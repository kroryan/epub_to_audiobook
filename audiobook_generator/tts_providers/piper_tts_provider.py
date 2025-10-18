import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from subprocess import run

import requests
from pydub import AudioSegment
from pydub.utils import which
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.audio_quality import AudioQualityProcessor
from audiobook_generator.utils.docker_helper import get_container, get_docker_client, is_env_var_equal, \
    remove_container, wait_until_initialised
from audiobook_generator.utils.utils import set_audio_tags

logger = logging.getLogger(__name__)

class PiperTTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        # Initialize audio quality processor
        self.audio_processor = AudioQualityProcessor(config, "piper_")
        
        # Default to mp3 unless we detect missing ffmpeg/ffprobe, then fall back to wav
        config.output_format = config.output_format or "mp3"
        try:
            ffmpeg_path = which("ffmpeg")
            ffprobe_path = which("ffprobe")
            # If either is missing, pydub may fail even for WAV introspection; use WAV to avoid conversion
            if (ffmpeg_path is None or ffprobe_path is None) and str(config.output_format).lower() != "wav":
                logging.getLogger(__name__).warning(
                    "FFmpeg/ffprobe not found on PATH; forcing Piper output_format to 'wav'. "
                    "Install FFmpeg (add ffmpeg.exe and ffprobe.exe to PATH) to enable mp3/other formats."
                )
                config.output_format = "wav"
        except Exception:
            # On any unexpected error detecting ffmpeg, choose safe default
            config.output_format = "wav"
        self.price = 0.000
        self.docker_container_name = "piper"
        self.docker_port = 10200
        self.docker_values_checked = False
        self.base_voice_model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        # simple in-memory cache of download failures to avoid retrying every chapter
        # keys are model_name strings, values are exception messages
        self._failed_model_downloads = {}
        super().__init__(config)

    def __str__(self) -> str:
        return f"PiperTTSProvider(config={self.config})"

    def validate_config(self):
        pass

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        if self.config.piper_path:
            logger.info("Local Piper installation selected")
            self._text_to_speech_local(text, output_file, audio_tags)
        else:
            logger.info("Docker Piper selected")
            self._text_to_speech_docker(text, output_file, audio_tags)

    def _text_to_speech_docker(self, text: str, output_file: str, audio_tags: AudioTags):

        def start_docker_container():
            logger.info("Starting docker container")
            container = get_docker_client().containers.run(
                image=self.config.piper_docker_image,
                name=self.docker_container_name,
                detach=True,
                ports={str(self.docker_port): self.docker_port},
                environment={
                    "PUID": 1000,
                    "PGID": 1000,
                    "TZ": "Etc/UTC",
                    "PIPER_VOICE": f"{self.config.model_name}",
                    "PIPER_SPEAKER": int(self.config.piper_speaker),
                    "PIPER_NOISE_SCALE": float(self.config.piper_noise_scale),
                    "PIPER_NOISE_W_SCALE": float(self.config.piper_noise_w_scale),
                    "PIPER_LENGTH_SCALE": float(self.config.piper_length_scale),
                    "PIPER_SENTENCE_SILENCE": float(self.config.piper_sentence_silence),
                }
            )
            wait_until_initialised(container, "done.")
            return container

        def get_docker_container():
            container = get_container("piper")
            if not container:
                logger.info("Piper docker container not found")
                container = start_docker_container()
            return container

        def check_docker_values_match():
            if self.docker_values_checked:
                return
            logger.info("Checking docker values match")
            container = get_docker_container()
            values = {
                "PIPER_VOICE": f"{self.config.model_name}",
                "PIPER_SPEAKER": int(self.config.piper_speaker),
                "PIPER_NOISE_SCALE": float(self.config.piper_noise_scale),
                "PIPER_NOISE_W_SCALE": float(self.config.piper_noise_w_scale),
                "PIPER_LENGTH_SCALE": float(self.config.piper_length_scale),
                "PIPER_SENTENCE_SILENCE": float(self.config.piper_sentence_silence)
            }
            for key, val in values.items():
                if not is_env_var_equal(container, key, str(val)):
                    logger.info(f"Environment variable {key} is not equal to {val}, re-deploying docker")
                    remove_container(container)
                    start_docker_container()
                    break
            self.docker_values_checked = True

        async def synthesize_speech(input_text: str):
            client = AsyncTcpClient('localhost', 10200)
            synthesize = Synthesize(text=input_text)
            request_event = synthesize.event()

            audio_data = bytearray()
            sample_rate = 22050  # Default sample rate
            sample_width = 2  # Default to 16-bit audio
            channels = 1  # Default to mono

            async with client:
                await client.write_event(request_event)

                while True:
                    response_event = await client.read_event()
                    if response_event is None:
                        break

                    if response_event.type == "audio-start":
                        sample_rate = response_event.data.get("rate", sample_rate)
                        sample_width = response_event.data.get("width", sample_width)
                        if sample_width > 4:
                            sample_width = sample_width // 8
                        channels = response_event.data.get("channels", channels)
                    elif response_event.type == "audio-chunk" and response_event.payload:
                        audio_data.extend(response_event.payload)
                    elif response_event.type == "audio-stop":
                        return AudioSegment(
                            data=bytes(audio_data),
                            sample_width=sample_width,
                            frame_rate=sample_rate,
                            channels=channels,
                        )
                    else:
                        logger.error(f"Unknown event type: {response_event.type}")
            return None, sample_rate, sample_width, channels

        # Start Text to Speech with Docker Piper
        check_docker_values_match()
        audio_segment = asyncio.run(synthesize_speech(text))
        
        # Handle audio format conversion for Docker version with high quality
        exported_file = output_file
        try:
            # Use high quality export
            self.audio_processor.export_with_high_quality(audio_segment, output_file)
        except Exception as export_error:
            # Fallback to standard export
            logger.warning(
                f"Failed to export with high quality ({export_error}); falling back to standard export"
            )
            try:
                audio_segment.export(output_file, format=self.config.output_format)
            except Exception as ffmpeg_error:
                # Most common: ffmpeg/ffprobe missing
                logger.warning(
                    f"Failed to export in format {self.config.output_format} ({ffmpeg_error}); falling back to WAV"
                )
                exported_file = str(output_file).rsplit('.', 1)[0] + '.wav'
                audio_segment.export(exported_file, format="wav")
                logger.info(f"Conversion completed, output file: {exported_file} (WAV format)")

        if audio_tags:
            set_audio_tags(exported_file, audio_tags)


    def _text_to_speech_local(self, text: str, output_file: str, audio_tags: AudioTags):

        def check_piper_exists():
            if not Path(self.config.piper_path).exists():
                raise FileNotFoundError(f"Piper executable not found at {self.config.piper_path}")

        def check_voice_model_present():
            piper_root_path = Path(self.config.piper_path).parent.resolve()
            vmp = piper_root_path / "espeak-ng-data" / "voices" / f"{self.config.model_name}.onnx"
            if vmp.exists():
                return str(vmp)
            # Try bundled resource path (for packaged EXE)
            try:
                from audiobook_generator.utils.resource_path import resource_path
                alt = resource_path(f"piper_tts/espeak-ng-data/voices/{self.config.model_name}.onnx")
                if Path(alt).exists():
                    return str(alt)
            except Exception:
                pass
            return False

        def download_voice_model():
            model_segments = self.config.model_name.split("-")
            language_short = self.config.model_name.split("_")[0]
            language_long = model_segments[0]
            voice = model_segments[1]
            quality = model_segments[2]
            piper_root_path = Path(self.config.piper_path).parent.resolve()
            voice_model_root_path = piper_root_path / "espeak-ng-data" / "voices"
            # If we've previously failed to download this model, skip retrying
            if self.config.model_name in self._failed_model_downloads:
                raise FileNotFoundError(f"Previous download attempt failed for {self.config.model_name}: {self._failed_model_downloads[self.config.model_name]}")

            # Try two candidate URL patterns. Hugging Face repo structures vary; some models are stored
            # under language/locale/voice/quality/... and others might have slightly different layouts.
            candidate_urls = [
                f"{self.base_voice_model_url}/{language_short}/{language_long}/{voice}/{quality}/{self.config.model_name}.onnx",
                # fallback: try without the quality folder (some uploads don't include it)
                f"{self.base_voice_model_url}/{language_short}/{language_long}/{voice}/{self.config.model_name}.onnx",
            ]

            # Special-case known external repo for es_ES-miro-high uploaded by csukuangfj
            try:
                if language_long == 'es_ES' and voice == 'miro' and quality == 'high':
                    # this repo contains the ONNX model at: csukuangfj/vits-piper-es_ES-miro-high (branch: main)
                    candidate_urls.append(
                        f"https://huggingface.co/csukuangfj/vits-piper-{language_long}-{voice}-{quality}/resolve/main/{self.config.model_name}.onnx"
                    )
            except Exception:
                # defensive: if parsing failed, continue with existing candidates
                pass

            file_name = f"{self.config.model_name}.onnx"
            config_file_name = f"{self.config.model_name}.onnx.json"
            file_path = voice_model_root_path / file_name
            config_file_path = voice_model_root_path / config_file_name

            # Ensure destination directory exists
            voice_model_root_path.mkdir(parents=True, exist_ok=True)

            last_error = None
            for url in candidate_urls:
                # Add explicit download query param expected by HF resolve endpoint
                download_url = url + "?download=true" if "?" not in url else url
                config_url = download_url.replace('.onnx', '.onnx.json')
                if file_path.exists() and config_file_path.exists():
                    logger.info(f"{file_name} and config already exist, skipping download")
                    return str(file_path)

                logger.info(f"Attempting to download voice model from {download_url} to {file_path}")
                try:
                    with requests.get(download_url, stream=True, timeout=30) as response:
                        response.raise_for_status()
                        with open(file_path, "wb") as file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    file.write(chunk)
                    logger.info(f"Finished downloading {download_url}")
                    
                    # Download config JSON
                    try:
                        with requests.get(config_url, stream=True, timeout=30) as response:
                            response.raise_for_status()
                            with open(config_file_path, "wb") as file:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        file.write(chunk)
                        logger.info(f"Finished downloading {config_url}")
                    except Exception as config_e:
                        logger.warning(f"Failed to download config {config_url}: {config_e}")
                        # Continue if config download fails, as some models might not have it
                    
                    return str(file_path)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed to download from {download_url}: {e}")

            # If we reached here, all candidates failed. Cache the failure to avoid hammering HF per chapter.
            err_msg = str(last_error) if last_error else "unknown error"
            self._failed_model_downloads[self.config.model_name] = err_msg
            raise FileNotFoundError(f"Could not download voice model {self.config.model_name}: {err_msg}")

        # Start Text to Speech with local Piper
        check_piper_exists()
        voice_model_path = check_voice_model_present()
        if not voice_model_path:
            logger.info(f"Voice model {self.config.model_name} not found, downloading...")
            voice_model_path = download_voice_model()
            if not voice_model_path:
                raise FileNotFoundError(f"Voice model {self.config.model_name} not found after download")

        tmpdir_obj = None
        try:
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdirname = tmpdir_obj.name
            logger.debug("created temporary directory %r", tmpdirname)

            tmpfilename = Path(tmpdirname) / "piper.wav"

            cmd = [
                self.config.piper_path,
                "--model",
                voice_model_path,
                "--speaker",
                str(self.config.piper_speaker),
                "--noise_scale",
                str(self.config.piper_noise_scale),
                "--noise_w",
                str(self.config.piper_noise_w_scale),
                "--sentence_silence",
                str(self.config.piper_sentence_silence),
                "--length_scale",
                str(self.config.piper_length_scale),
                "-f",
                str(tmpfilename)
            ]
            # Si el usuario selecciona GPU, agregar --cuda
            if getattr(self.config, 'piper_device', None) == "cuda":
                cmd.append("--cuda")

            logger.info(
                f"Running Piper TTS command: {' '.join(str(arg) for arg in cmd)}"
            )
            
            # Run the command and capture output
            result = run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            
            # Check if the command failed
            if result.returncode != 0:
                error_msg = f"Piper command failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f". Error: {result.stderr}"
                if result.stdout:
                    error_msg += f". Output: {result.stdout}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Ensure the file exists and is complete
            if not tmpfilename.exists():
                raise FileNotFoundError(f"Piper failed to create output file: {tmpfilename}")

            # set audio tags, need to be done before conversion or opus won't work, not sure why
            if audio_tags:
                set_audio_tags(tmpfilename, audio_tags)
            
            # Handle audio format conversion
            exported_file = output_file
            try:
                if self.config.output_format.lower() == 'wav':
                    # If output format is WAV, just copy the file
                    logger.info("Piper TTS command completed, copying WAV file to output")
                    shutil.copy2(tmpfilename, output_file)
                else:
                    # Try to convert using AudioSegment (requires FFmpeg for non-WAV formats)
                    logger.info(
                        f"Piper TTS command completed, converting {tmpfilename} to {self.config.output_format} format"
                    )
                    audio_segment = AudioSegment.from_wav(tmpfilename)
                    audio_segment.export(output_file, format=self.config.output_format)
                    # Explicitly close the audio segment to release file handles
                    del audio_segment
            except Exception as conv_error:
                logger.warning(
                    f"Failed to export in format {self.config.output_format} ({conv_error}); falling back to WAV"
                )
                exported_file = str(output_file).rsplit('.', 1)[0] + '.wav'
                shutil.copy2(tmpfilename, exported_file)
                logger.info(f"Conversion completed, output file: {exported_file} (WAV format)")

            # Apply audio tags to the final output file
            if audio_tags:
                try:
                    set_audio_tags(exported_file, audio_tags)
                except Exception as tag_err:
                    logger.warning(f"Failed to set audio tags on {exported_file}: {tag_err}")

            logger.info(f"Conversion completed, output file: {exported_file}")

        except Exception as e:
            logger.error(f"Error during Piper TTS conversion: {e}")
            raise
        finally:
            # Clean up temporary directory with error handling
            if tmpdir_obj:
                try:
                    tmpdir_obj.cleanup()
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not clean up temporary directory {tmpdirname}: {e}")
                    # On Windows, sometimes we need to wait a bit and try again
                    import time
                    time.sleep(0.1)
                    try:
                        tmpdir_obj.cleanup()
                    except (OSError, PermissionError):
                        logger.warning(f"Failed to clean up temporary directory {tmpdirname} after retry. This may be cleaned up later by the system.")

    def estimate_cost(self, total_chars):
        return 0  # Piper is free

    def get_break_string(self):
        return "."  # Four spaces as the default break string

    def get_output_file_extension(self):
        return self.config.output_format


def get_piper_supported_languages():
    return list(voice_data.keys())

def get_piper_supported_voices(language: str):
    if language not in voice_data:
        raise ValueError(f"Language '{language}' is not supported.")
    return list(voice_data[language].keys())

def get_piper_supported_qualities(language: str, voice_name: str):
    if language not in voice_data:
        raise ValueError(f"Language '{language}' is not supported.")
    if voice_name not in voice_data[language]:
        raise ValueError(f"Voice '{voice_name}' is not supported for language '{language}'.")
    return list(voice_data[language][voice_name].keys())

def get_piper_supported_speakers(language: str, voice_name: str, quality: str):
    if language not in voice_data:
        raise ValueError(f"Language '{language}' is not supported.")
    if voice_name not in voice_data[language]:
        raise ValueError(f"Voice '{voice_name}' is not supported for language '{language}'.")
    if quality not in voice_data[language][voice_name]:
        raise ValueError(f"Quality '{quality}' is not supported for voice '{voice_name}' in language '{language}'.")
    if voice_data[language][voice_name][quality] is None:
        return ["0"]
    return list(range(voice_data[language][voice_name][quality] + 1))


voice_data = {
    "ar_JO": {
        "kareem": {"low": None, "medium": None}
    },
    "ca_ES": {
        "upc_ona": {"x_low": None, "medium": None},
        "upc_pau": {"x_low": None}
    },
    "cs_CZ": {
        "jirka": {"low": None, "medium": None}
    },
    "cy_GB": {
        "gwryw_gogleddol": {"medium": None}
    },
    "da_DK": {
        "talesyntese": {"medium": None}
    },
    "de_DE": {
        "eva_k": {"x_low": None},
        "karlsson": {"low": None},
        "kerstin": {"low": None},
        "mls": {"medium": None},
        "pavoque": {"low": None},
        "ramona": {"low": None},
        "thorsten": {"low": None, "medium": None, "high": None},
        "thorsten_emotional": {"medium": None}
    },
    "el_GR": {
        "rapunzelina": {"low": None}
    },
    "en_GB": {
        "alan": {"low": None, "medium": None},
        "alba": {"medium": None},
        "aru": {"medium": 11},
        "cori": {"medium": None, "high": None},
        "jenny_dioco": {"medium": None},
        "northern_english_male": {"medium": None},
        "semaine": {"medium": 3},
        "southern_english_female": {"low": None},
        "vctk": {"medium": 108}
    },
    "en_US": {
        "amy": {"low": None, "medium": None},
        "arctic": {"medium": 17},
        "bryce": {"medium": None},
        "danny": {"low": None},
        "hfc_female": {"medium": None},
        "hfc_male": {"medium": None},
        "joe": {"medium": None},
        "john": {"medium": None},
        "kathleen": {"low": None},
        "kristin": {"medium": None},
        "kusal": {"medium": None},
        "l2arctic": {"medium": 23},
        "lessac": {"low": None, "medium": None, "high": None},
        "libritts": {"high": 903},
        "libritts_r": {"medium": 903},
        "ljspeech": {"medium": None, "high": None},
        "norman": {"medium": None},
        "ryan": {"low": None, "medium": None, "high": None}
    },
    "es_ES": {
        "carlfm": {"x_low": None},
        "davefx": {"medium": None},
        "mls_10246": {"low": None},
        "mls_9972": {"low": None},
        "sharvard": {"medium": 1},
        "miro": {"high": None}
    },
    "es_MX": {
        "ald": {"medium": None},
        "claude": {"high": None}
    },
    "fa_IR": {
        "amir": {"medium": None},
        "gyro": {"medium": None}
    },
    "fi_FI": {
        "harri": {"low": None, "medium": None}
    },
    "fr_FR": {
        "gilles": {"low": None},
        "mls": {"medium": 124},
        "mls_1840": {"low": None},
        "siwis": {"low": None, "medium": None},
        "tom": {"medium": None},
        "upmc": {"medium": 1}
    },
    "hu_HU": {
        "anna": {"medium": None},
        "berta": {"medium": None},
        "imre": {"medium": None}
    },
    "is_IS": {
        "bui": {"medium": None},
        "salka": {"medium": None},
        "steinn": {"medium": None},
        "ugla": {"medium": None}
    },
    "it_IT": {
        "paola": {"medium": None},
        "riccardo": {"x_low": None}
    },
    "ka_GE": {
        "natia": {"medium": None}
    },
    "kk_KZ": {
        "iseke": {"x_low": None},
        "issai": {"high": 5},
        "raya": {"x_low": None}
    },
    "lb_LU": {
        "marylux": {"medium": None}
    },
    "ne_NP": {
        "google": {"x_low": 17, "medium": 17}
    },
    "nl_BE": {
        "nathalie": {"x_low": None, "medium": None},
        "rdh": {"x_low": None, "medium": None}
    },
    "nl_NL": {
        "mls": {"medium": 51},
        "mls_5809": {"low": None},
        "mls_7432": {"low": None}
    },
    "no_NO": {
        "talesyntese": {"medium": None}
    },
    "pl_PL": {
        "darkman": {"medium": None},
        "gosia": {"medium": None},
        "mc_speech": {"medium": None},
        "mls_6892": {"low": None}
    },
    "pt_BR": {
        "edresson": {"low": None},
        "faber": {"medium": None}
    },
    "pt_PT": {
        "tugаo": {"medium": None}
    },
    "ro_RO": {
        "mihai": {"medium": None}
    },
    "ru_RU": {
        "denis": {"medium": None},
        "dmitri": {"medium": None},
        "irina": {"medium": None},
        "ruslan": {"medium": None}
    },
    "sk_SK": {
        "lili": {"medium": None}
    },
    "sl_SI": {
        "artur": {"medium": None}
    },
    "sr_RS": {
        "serbski_institut": {"medium": 1}
    },
    "sv_SE": {
        "nst": {"medium": None}
    },
    "sw_CD": {
        "lanfrica": {"medium": None}
    },
    "tr_TR": {
        "dfki": {"medium": None},
        "fahrettin": {"medium": None},
        "fettah": {"medium": None}
    },
    "uk_UA": {
        "lada": {"x_low": None},
        "ukrainian_tts": {"medium": 2}
    },
    "vi_VN": {
        "25hours_single": {"low": None},
        "vais1000": {"medium": None},
        "vivos": {"x_low": 64}
    },
    "zh_CN": {
        "huayan": {"x_low": None, "medium": None}
    }
}
