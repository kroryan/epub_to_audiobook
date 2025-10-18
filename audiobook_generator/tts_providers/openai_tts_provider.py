import io
import logging
import math
import tempfile
import os
from pydub import AudioSegment

from openai import OpenAI

from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.utils.utils import split_text, set_audio_tags, merge_audio_segments
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.audio_quality import AudioQualityProcessor


logger = logging.getLogger(__name__)


def get_openai_supported_output_formats():
    return ["mp3", "aac", "flac", "opus", "wav"]

def get_openai_supported_voices():
    return ["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]

def get_openai_supported_models():
    return ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]

def get_openai_instructions_example():
    return """Voice Affect: Calm, composed, and reassuring. Competent and in control, instilling trust.
Tone: Sincere, empathetic, with genuine concern for the customer and understanding of the situation.
Pacing: Slower during the apology to allow for clarity and processing. Faster when offering solutions to signal action and resolution.
Emotions: Calm reassurance, empathy, and gratitude.
Pronunciation: Clear, precise: Ensures clarity, especially with key details. Focus on key words like 'refund' and 'patience.' 
Pauses: Before and after the apology to give space for processing the apology."""

def get_price(model):
    # https://platform.openai.com/docs/pricing#transcription-and-speech-generation
    if model == "tts-1": # $15 per 1 mil chars
        return 0.015
    elif model == "tts-1-hd": # $30 per 1 mil chars
        return 0.03
    elif model == "gpt-4o-mini-tts": # $12 per 1 mil tokens (not chars, as 1 token is ~4 chars)
        return 0.003 # TODO: this could be very wrong for Chinese. Not sure how openai calculates the audio token count.
    else:
        logger.warning(f"OpenAI: Unsupported model name: {model}, unable to retrieve the price")
        return 0.0


class OpenAITTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        config.model_name = config.model_name or "gpt-4o-mini-tts" # default to this model as it's the cheapest
        config.voice_name = config.voice_name or "alloy"
        config.speed = config.speed or 1.0
        config.instructions = config.instructions or None
        config.output_format = config.output_format or "mp3"

        self.price = get_price(config.model_name)
        super().__init__(config)

        # Inicializar el procesador de calidad de audio
        # Para Kokoro, usamos las configuraciones con prefijo 'kokoro_'
        # Para OpenAI estándar, usamos configuraciones generales
        if os.getenv("OPENAI_BASE_URL"):
            # Configuración específica de Kokoro
            self.audio_processor = AudioQualityProcessor(
                config, 
                provider_prefix="kokoro"
            )
        else:
            # Configuración general de OpenAI
            self.audio_processor = AudioQualityProcessor(
                config, 
                provider_prefix=None  # Usar configuraciones generales
            )

        # User should set OPENAI_API_KEY environment variable for authentication.
        # If OPENAI_BASE_URL is set, prefer that so the OpenAI client can target
        # OpenAI-compatible servers (e.g. local Kokoro). Fall back to default client.
        base_url = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")
        
        if base_url:
            try:
                # For local servers like Kokoro, use fake key if none provided
                if not api_key:
                    api_key = "fake-key"
                self.client = OpenAI(base_url=base_url, api_key=api_key, max_retries=4)
                logger.info(f"OpenAI client configured to use base_url={base_url}")
            except TypeError:
                # Some older OpenAI SDK versions may not accept base_url kwarg.
                logger.info("OpenAI SDK does not accept base_url parameter; using default client")
                self.client = OpenAI(max_retries=4)
        else:
            self.client = OpenAI(max_retries=4)

    def __str__(self) -> str:
        return super().__str__()

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        # Reason: The max num of input tokens is 2000 for gpt-4o-mini-tts https://platform.openai.com/docs/models/gpt-4o-mini-tts. One token is ~4 chars in English but ~1 word/char in Chinese.
        # So we reduce the max num of chars from 4000 to 1800 to avoid the input tokens limit.
        # TODO: detect the language and set the max num of chars accordingly.
        max_chars = 1800

        text_chunks = split_text(text, max_chars, self.config.language)

        audio_segments = []
        chunk_ids = []

        for i, chunk in enumerate(text_chunks, 1):
            chunk_id = f"chapter-{audio_tags.idx}_{audio_tags.title}_chunk_{i}_of_{len(text_chunks)}"
            logger.info(
                f"Processing {chunk_id}, length={len(chunk)}"
            )
            logger.debug(
                f"Processing {chunk_id}, length={len(chunk)}, text=[{chunk}]"
            )

            # NO retry for OpenAI TTS because SDK has built-in retry logic
            base_url = os.getenv("OPENAI_BASE_URL")
            
            # If using Kokoro (custom base_url) and language is specified, use requests directly
            # because OpenAI SDK doesn't support language parameter
            if base_url and hasattr(self.config, 'language') and self.config.language:
                # Use direct HTTP request for Kokoro with language support
                payload = {
                    "model": self.config.model_name,
                    "voice": self.config.voice_name,
                    "speed": self.config.speed,
                    "input": chunk,
                    "response_format": self.config.output_format,
                    "language": self.config.language
                }
                
                import requests
                api_key = os.getenv("OPENAI_API_KEY", "fake-key")
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                http_response = requests.post(
                    f"{base_url}/audio/speech",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                if http_response.status_code != 200:
                    raise Exception(f"Kokoro API error: {http_response.status_code} - {http_response.text}")
                
                # Create a mock response object similar to OpenAI's response
                class MockResponse:
                    def __init__(self, content):
                        self.content = content
                        self.response = type('obj', (object,), {'status_code': 200})()
                
                response = MockResponse(http_response.content)
                
            else:
                # Use OpenAI SDK for regular OpenAI or Kokoro without language
                request_params = {
                    "model": self.config.model_name,
                    "voice": self.config.voice_name,
                    "speed": self.config.speed,
                    "input": chunk,
                    "response_format": self.config.output_format,
                }
                
                # Add instructions if available (OpenAI specific)
                if self.config.instructions:
                    request_params["instructions"] = self.config.instructions
                
                response = self.client.audio.speech.create(**request_params)

            # Log response details
            logger.debug(f"Remote server response: status_code={response.response.status_code}, "
                         f"size={len(response.content)} bytes, "
                         f"content={response.content[:128]}...")

            audio_segments.append(io.BytesIO(response.content))
            chunk_ids.append(chunk_id)

        # Use utility function to merge audio segments with high quality processing
        self._merge_audio_segments_with_quality(audio_segments, output_file, self.config.output_format, chunk_ids, self.config.use_pydub_merge)

        set_audio_tags(output_file, audio_tags)

    def _merge_audio_segments_with_quality(self, audio_segments, output_file, output_format, chunk_ids, use_pydub_merge):
        """
        Merge audio segments using high quality processing.
        """
        try:
            if use_pydub_merge:
                logger.info(f"Using pydub with high quality to merge audio segments: {chunk_ids}")
                
                # Crear archivos temporales para cada segmento
                tmp_files = []
                for i, segment in enumerate(audio_segments):
                    import tempfile
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
                    tmp_file.write(segment.getvalue())
                    tmp_file.close()
                    tmp_files.append(tmp_file.name)
                    
                # Combinar segmentos
                combined = AudioSegment.empty()
                for tmp_file in tmp_files:
                    logger.debug(f"Loading chunk from temporary file: {tmp_file}")
                    segment = AudioSegment.from_file(tmp_file)
                    combined += segment
                
                # Exportar con calidad alta
                self.audio_processor.export_with_high_quality(combined, output_file)
                
                # Limpiar archivos temporales
                for tmp_file in tmp_files:
                    os.remove(tmp_file)
                    
            else:
                logger.info(f"Using direct write with high quality to merge audio segments: {chunk_ids}")
                
                # Combinar directamente y aplicar calidad
                combined = AudioSegment.empty()
                for segment in audio_segments:
                    segment.seek(0)
                    audio_chunk = AudioSegment.from_file(io.BytesIO(segment.read()), format=output_format)
                    combined += audio_chunk
                
                # Exportar con calidad alta
                self.audio_processor.export_with_high_quality(combined, output_file)
                
        except Exception as quality_error:
            logger.warning(f"Failed to merge with high quality ({quality_error}); falling back to standard merge")
            # Fallback a merge estándar
            merge_audio_segments(audio_segments, output_file, output_format, chunk_ids, use_pydub_merge)

    def set_mobile_quality(self):
        """Configurar calidad optimizada para dispositivos móviles."""
        return self.audio_processor.set_mobile_quality()

    def set_desktop_quality(self):
        """Configurar calidad optimizada para escritorio."""
        return self.audio_processor.set_desktop_quality()

    def set_high_quality(self):
        """Configurar calidad alta para audiófilos."""
        return self.audio_processor.set_high_quality()

    def set_maximum_quality(self):
        """Configurar calidad máxima."""
        return self.audio_processor.set_maximum_quality()

    def get_quality_info(self):
        """Obtener información sobre la configuración actual de calidad."""
        return self.audio_processor.get_quality_info()

    def get_break_string(self):
        return "   "

    def get_output_file_extension(self):
        return self.config.output_format

    def validate_config(self):
        if self.config.output_format not in get_openai_supported_output_formats():
            raise ValueError(f"OpenAI: Unsupported output format: {self.config.output_format}")
        if self.config.speed < 0.25 or self.config.speed > 4.0:
            raise ValueError(f"OpenAI: Unsupported speed: {self.config.speed}")
        if self.config.instructions and len(self.config.instructions) > 0 and self.config.model_name != "gpt-4o-mini-tts":
            raise ValueError(f"OpenAI: Instructions are only supported for 'gpt-4o-mini-tts' model")

    def estimate_cost(self, total_chars):
        return math.ceil(total_chars / 1000) * self.price
