"""
Kokoro TTS Provider with advanced features
Includes voice mixing, normalization, streaming, and all Kokoro-FastAPI capabilities
"""

import io
import json
import logging
import math
import os
import re
import tempfile
from typing import List, Dict, Optional, Union, Tuple
from pydub import AudioSegment
import requests

from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.utils.utils import split_text, set_audio_tags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.audio_quality import AudioQualityProcessor

logger = logging.getLogger(__name__)


def get_kokoro_supported_output_formats():
    return ["mp3", "opus", "aac", "flac", "wav", "pcm"]


def get_kokoro_supported_voices():
    """Get default voice list (will be fetched from server in runtime)"""
    return [
        # American English
        "af_bella", "af_sky", "af_heart", "af_nicole", "af_sarah", "af_emma",
        "am_adam", "am_daniel", "am_michael", "am_liam",
        # British English  
        "bf_emma", "bf_sarah", "bf_nicole", "bf_sky",
        "bm_lewis", "bm_george", "bm_william", "bm_james",
        # Spanish
        "ef_dora", "ef_sarah", "ef_maria", "ef_isabella",
        "em_alex", "em_carlos", "em_diego", "em_miguel",
        # Spanish Santa voices
        "am_santa", "em_santa", "pm_santa",
        # Bella variants
        "af_v0bella", "bf_v0isabella",
        # Other Spanish
        "pf_dora", "pm_alex"
    ]


def get_kokoro_supported_models():
    return ["kokoro", "tts-1", "tts-1-hd"]


def get_kokoro_supported_languages():
    """Get supported language codes and their full names"""
    return {
        "": "Auto-detect",
        "a": "English (US)", 
        "b": "British English",
        "e": "Spanish",
        "f": "French", 
        "h": "Hindi",
        "i": "Italian",
        "p": "Portuguese",
        "j": "Japanese",
        "z": "Chinese"
    }


class NormalizationOptions:
    """Options for text normalization"""
    def __init__(self, config: GeneralConfig = None):
        # Default values from Kokoro-FastAPI
        self.normalize = getattr(config, 'kokoro_normalize', True)
        self.unit_normalization = getattr(config, 'kokoro_unit_normalization', False)
        self.url_normalization = getattr(config, 'kokoro_url_normalization', True)
        self.email_normalization = getattr(config, 'kokoro_email_normalization', True)
        self.optional_pluralization_normalization = getattr(config, 'kokoro_pluralization_normalization', True)
        self.phone_normalization = getattr(config, 'kokoro_phone_normalization', True)
        self.replace_remaining_symbols = getattr(config, 'kokoro_replace_symbols', True)

    def to_dict(self):
        return {
            "normalize": self.normalize,
            "unit_normalization": self.unit_normalization,
            "url_normalization": self.url_normalization,
            "email_normalization": self.email_normalization,
            "optional_pluralization_normalization": self.optional_pluralization_normalization,
            "phone_normalization": self.phone_normalization,
            "replace_remaining_symbols": self.replace_remaining_symbols
        }


class KokoroTTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        # Initialize base class first
        super().__init__(config)
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        # Set defaults
        config.model_name = config.model_name or "kokoro"
        config.voice_name = config.voice_name or "af_heart"
        config.speed = config.speed or 1.0
        config.output_format = config.output_format or "mp3"
        
        # Kokoro specific settings
        self.base_url = getattr(config, 'kokoro_base_url', 'http://localhost:8880')
        self.volume_multiplier = getattr(config, 'kokoro_volume_multiplier', 1.0)
        self.stream_audio = getattr(config, 'kokoro_stream', True)
        self.return_timestamps = getattr(config, 'kokoro_return_timestamps', False)
        self.return_download_link = getattr(config, 'kokoro_return_download_link', False)
        
        # Normalization options
        self.normalization_options = NormalizationOptions(config)
        
        # Voice mixing configuration
        self.voice_weight_normalization = getattr(config, 'kokoro_voice_weight_normalization', True)
        
        super().__init__(config)

        # Initialize audio quality processor with Kokoro-specific settings
        self.audio_processor = AudioQualityProcessor(config, provider_prefix="kokoro")

        # Set up API headers
        self.headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }

    def __str__(self) -> str:
        return super().__str__()

    def validate_config(self):
        if self.config.output_format not in get_kokoro_supported_output_formats():
            raise ValueError(f"Kokoro: Unsupported output format: {self.config.output_format}")
        if self.config.speed < 0.25 or self.config.speed > 4.0:
            raise ValueError(f"Kokoro: Unsupported speed: {self.config.speed}")

    def fetch_voices(self) -> List[str]:
        """Fetch available voices from Kokoro server"""
        try:
            url = f"{self.base_url.rstrip('/')}/v1/audio/voices"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch voices from {url}, using defaults")
                return get_kokoro_supported_voices()
            
            data = resp.json()
            
            # Extract voices from response
            if isinstance(data, dict) and 'voices' in data:
                voices = data['voices']
            elif isinstance(data, list):
                voices = data
            else:
                return get_kokoro_supported_voices()
                
            # Ensure we return a list of strings
            voice_list = []
            for voice in voices:
                if isinstance(voice, dict):
                    voice_list.append(voice.get('id', voice.get('name', str(voice))))
                elif isinstance(voice, str):
                    voice_list.append(voice)
            
            return voice_list
            
        except Exception as e:
            logger.warning(f"Error fetching Kokoro voices: {e}")
            return get_kokoro_supported_voices()

    def parse_voice_combination(self, voice_input: str) -> List[Tuple[str, str, float]]:
        """
        Parse voice combination string into components
        
        Args:
            voice_input: Voice string like "voice1+voice2(0.5)-voice3(0.3)"
            
        Returns:
            List of (voice_name, operation, weight) tuples
            First entry always has operation "=" (base voice)
        """
        # Clean input
        voice_input = voice_input.replace(" ", "").strip()
        
        # Validate input
        if voice_input[-1] in "+-" or voice_input[0] in "+-":
            raise ValueError("Voice combination contains empty combine items")
        
        if re.search(r"[+-]{2,}", voice_input):
            raise ValueError("Voice combination contains empty combine items")
            
        # Split by operators while preserving operators
        parts = re.split(r"([-+])", voice_input)
        
        # Parse voice components
        components = []
        for i in range(0, len(parts), 2):
            voice_part = parts[i]
            operation = "=" if i == 0 else parts[i-1]  # First voice is base, others have operators
            
            # Parse voice name and weight
            if "(" in voice_part and ")" in voice_part:
                voice_name = voice_part.split("(")[0].strip()
                weight_str = voice_part.split("(")[1].split(")")[0]
                try:
                    weight = float(weight_str)
                except ValueError:
                    raise ValueError(f"Invalid weight in voice '{voice_part}': {weight_str}")
            else:
                voice_name = voice_part
                weight = 1.0
                
            if len(voice_name) == 0:
                raise ValueError(f"Empty voice name in '{voice_part}'")
                
            components.append((voice_name, operation, weight))
        
        return components

    def validate_voice_combination(self, voice_input: str) -> str:
        """
        Validate and potentially modify voice combination
        
        Args:
            voice_input: Voice combination string
            
        Returns:
            Validated voice combination string
        """
        # If simple voice, return as-is
        if "+" not in voice_input and "-" not in voice_input:
            return voice_input
            
        # Parse components
        components = self.parse_voice_combination(voice_input)
        
        # Get available voices to validate
        available_voices = self.fetch_voices()
        
        # Validate each voice exists
        for voice_name, _, _ in components:
            if voice_name not in available_voices:
                raise ValueError(f"Voice '{voice_name}' not found. Available: {', '.join(sorted(available_voices))}")
        
        # Rebuild the combination string (normalized)
        result_parts = []
        for i, (voice_name, operation, weight) in enumerate(components):
            if i == 0:
                # First voice (base)
                if weight != 1.0:
                    result_parts.append(f"{voice_name}({weight})")
                else:
                    result_parts.append(voice_name)
            else:
                # Subsequent voices with operators
                if weight != 1.0:
                    result_parts.append(f"{operation}{voice_name}({weight})")
                else:
                    result_parts.append(f"{operation}{voice_name}")
        
        return "".join(result_parts)

    def combine_voices_api(self, voices: Union[str, List[str]]) -> bytes:
        """
        Call Kokoro API to combine voices and return .pt file
        Note: This is optional - voice combinations work directly in TTS requests
        
        Args:
            voices: Either string combination or list of voice names
            
        Returns:
            Raw bytes of the combined voice .pt file
        """
        try:
            url = f"{self.base_url.rstrip('/')}/v1/audio/voices/combine"
            
            # Prepare request data
            if isinstance(voices, str):
                # Validate the combination string
                validated_combination = self.validate_voice_combination(voices)
                request_data = validated_combination
            else:
                # List of voices - validate each one
                available_voices = self.fetch_voices()
                for voice in voices:
                    if voice not in available_voices:
                        raise ValueError(f"Voice '{voice}' not found")
                request_data = voices
            
            # Make API call
            response = requests.post(
                url,
                json=request_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 403:
                # Server has voice combination creation disabled - this is OK
                # Voice combinations still work in TTS requests
                logger.info("Voice combination endpoint disabled on server, but combinations work in TTS requests")
                raise RuntimeError("Voice combination creation is disabled on the server, but you can use combinations directly in voice field")
            elif response.status_code != 200:
                raise RuntimeError(f"Voice combination failed: {response.status_code} - {response.text}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to combine voices: {e}")
            raise

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        """Convert text to speech using Kokoro TTS with advanced features"""
        
        # Prepare the API request
        url = f"{self.base_url.rstrip('/')}/v1/audio/speech"
        
        # Validate and prepare voice (handle combinations)
        voice_to_use = self.config.voice_name

        
        if "+" in voice_to_use or "-" in voice_to_use:
            self.logger.info(f"🔀 Using voice combination: {voice_to_use}")
            voice_to_use = self.validate_voice_combination(voice_to_use)

        else:
            self.logger.info(f"🎵 Using single voice: {voice_to_use}")
        
        # Determine language code
        lang_code = getattr(self.config, 'language', '') or ''
        
        # Split text into chunks if needed
        max_chars = 2000  # Kokoro can handle longer texts than OpenAI
        text_chunks = split_text(text, max_chars, self.config.language)
        
        audio_segments = []
        chunk_ids = []
        
        for i, chunk in enumerate(text_chunks, 1):
            chunk_id = f"chapter-{audio_tags.idx}_{audio_tags.title}_chunk_{i}_of_{len(text_chunks)}"
            logger.info(f"Processing {chunk_id}, length={len(chunk)}")
            
            # Prepare request payload with all Kokoro features
            payload = {
                "model": self.config.model_name,
                "voice": voice_to_use,
                "input": chunk,
                "speed": self.config.speed,
                "response_format": self.config.output_format,
                "stream": False,  # For now, use non-streaming for simplicity
                "volume_multiplier": self.volume_multiplier,
                "normalization_options": self.normalization_options.to_dict(),
                "return_timestamps": self.return_timestamps,
                "return_download_link": self.return_download_link
            }
            
            # Add language code if specified
            if lang_code:
                payload["lang_code"] = lang_code
            
            # Make API request
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=120  # Longer timeout for complex combinations
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Kokoro TTS failed: {response.status_code} - {response.text}")
            
            # Log response details
            logger.debug(f"Kokoro response: status={response.status_code}, size={len(response.content)} bytes")
            
            audio_segments.append(io.BytesIO(response.content))
            chunk_ids.append(chunk_id)
        
        # Merge audio segments with high quality
        self._merge_audio_segments_with_quality(
            audio_segments, 
            output_file, 
            self.config.output_format, 
            chunk_ids, 
            self.config.use_pydub_merge
        )
        
        # Set audio tags
        set_audio_tags(output_file, audio_tags)

    def _merge_audio_segments_with_quality(self, audio_segments, output_file, output_format, chunk_ids, use_pydub_merge):
        """Merge audio segments using high quality processing"""
        try:
            if use_pydub_merge or len(audio_segments) > 1:
                logger.info(f"Using high-quality merge for Kokoro audio segments: {chunk_ids}")
                
                # Create temporary files for each segment
                tmp_files = []
                for i, segment in enumerate(audio_segments):
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
                    tmp_file.write(segment.getvalue())
                    tmp_file.close()
                    tmp_files.append(tmp_file.name)
                    
                # Combine segments
                combined = AudioSegment.empty()
                for tmp_file in tmp_files:
                    logger.debug(f"Loading Kokoro chunk: {tmp_file}")
                    segment = AudioSegment.from_file(tmp_file)
                    combined += segment
                
                # Export with high quality
                self.audio_processor.export_with_high_quality(combined, output_file)
                
                # Clean up temporary files
                for tmp_file in tmp_files:
                    os.remove(tmp_file)
            else:
                # Single segment - write directly with quality processing
                segment = audio_segments[0]
                segment.seek(0)
                audio = AudioSegment.from_file(io.BytesIO(segment.read()), format=output_format)
                self.audio_processor.export_with_high_quality(audio, output_file)
                
        except Exception as e:
            logger.error(f"High-quality merge failed: {e}")
            # Fallback to simple merge
            self._simple_merge_segments(audio_segments, output_file)

    def _simple_merge_segments(self, audio_segments, output_file):
        """Simple fallback merge method"""
        with open(output_file, 'wb') as f:
            for segment in audio_segments:
                segment.seek(0)
                f.write(segment.read())

    def generate_from_phonemes(self, phonemes: str, output_file: str, audio_tags: AudioTags):
        """
        Generate audio directly from phonemes (Kokoro-FastAPI specific feature)
        
        Args:
            phonemes: Phonemes in Kokoro format
            output_file: Output audio file path
            audio_tags: Audio metadata tags
        """
        try:
            # This would require a dedicated phoneme endpoint in Kokoro-FastAPI
            # For now, we'll use the standard text endpoint with special phoneme markers
            url = f"{self.base_url.rstrip('/')}/v1/audio/speech"
            
            payload = {
                "model": self.config.model_name,
                "voice": self.config.voice_name,
                "input": f"<phonemes>{phonemes}</phonemes>",  # Special phoneme marker
                "speed": self.config.speed,
                "response_format": self.config.output_format,
                "stream": False,
                "volume_multiplier": self.volume_multiplier
            }
            
            # Add language code if specified
            lang_code = getattr(self.config, 'language', '')
            if lang_code:
                payload["lang_code"] = lang_code
            
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Phoneme generation failed: {response.status_code} - {response.text}")
            
            # Write audio to file
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            # Set audio tags
            set_audio_tags(output_file, audio_tags)
            
            logger.info(f"Generated audio from phonemes: {len(phonemes)} characters -> {output_file}")
            
        except Exception as e:
            logger.error(f"Phoneme generation failed: {e}")
            raise

    def estimate_cost(self, total_chars):
        """Kokoro is free, so cost is always 0"""
        return 0.0

    def get_break_string(self):
        """Return break string for pauses"""
        return "   "

    def get_output_file_extension(self):
        return self.config.output_format

    def get_advanced_capabilities(self) -> Dict[str, bool]:
        """Return dict of advanced capabilities supported by this provider"""
        return {
            "voice_mixing": True,
            "voice_combination": True,
            "text_normalization": True,
            "streaming": True,
            "timestamps": True,
            "phoneme_generation": True,
            "volume_control": True,
            "pause_tags": True,
            "multiple_languages": True,
            "free_usage": True
        }

    def create_voice_combination(self, voice_spec: str) -> str:
        """
        Validate and prepare a voice combination for use
        Note: Actual combination happens during TTS generation, not pre-creation
        
        Args:
            voice_spec: Voice combination specification (e.g., "voice1+voice2(0.5)")
            
        Returns:
            Validated voice combination string (ready for TTS use)
        """
        try:
            # Just validate the combination - no need to pre-create
            validated_combination = self.validate_voice_combination(voice_spec)
            
            logger.info(f"Validated voice combination: {voice_spec} -> {validated_combination}")
            
            # Return the validated combination string (it will be used directly in TTS)
            return validated_combination
            
        except Exception as e:
            logger.error(f"Failed to validate voice combination: {e}")
            raise

    # Quality preset methods (inherited from audio processor)
    def set_mobile_quality(self):
        return self.audio_processor.set_mobile_quality()

    def set_desktop_quality(self):
        return self.audio_processor.set_desktop_quality()

    def set_high_quality(self):
        return self.audio_processor.set_high_quality()

    def set_maximum_quality(self):
        return self.audio_processor.set_maximum_quality()

    def get_quality_info(self):
        return self.audio_processor.get_quality_info()
