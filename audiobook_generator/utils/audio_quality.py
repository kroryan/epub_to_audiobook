"""
Audio quality utilities for TTS providers
Shared audio processing functions for high quality output
"""

import logging
from pathlib import Path
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class AudioQualityProcessor:
    """
    Shared audio quality processing for all TTS providers
    """
    
    def __init__(self, config, provider_prefix=""):
        """
        Initialize with configuration and provider prefix
        
        Args:
            config: Configuration object with audio quality settings
            provider_prefix: Prefix for config attributes (e.g., 'coqui_', 'piper_', 'kokoro_')
        """
        self.config = config
        self.prefix = provider_prefix
        
    def _get_config_value(self, setting_name, default_value):
        """Get configuration value with provider prefix"""
        full_name = f"{self.prefix}{setting_name}"
        return getattr(self.config, full_name, default_value)
    
    def normalize_audio_level(self, audio_segment):
        """Normaliza el nivel de audio para evitar diferencias de volumen"""
        if not self._get_config_value('normalize_volume', True):
            return audio_segment
            
        target_dBFS = -20.0  # Nivel target en dBFS
        current_dBFS = audio_segment.dBFS
        
        if current_dBFS < -50.0:  # Audio muy silencioso
            return audio_segment
        
        change_in_dBFS = target_dBFS - current_dBFS
        return audio_segment.apply_gain(change_in_dBFS)

    def apply_soft_limiter(self, audio_segment):
        """Aplica un limiter suave para evitar distorsión"""
        if not self._get_config_value('enable_limiter', True):
            return audio_segment
            
        # Comprimir picos suavemente
        if audio_segment.max_dBFS > -3.0:
            return audio_segment.compress_dynamic_range(
                threshold=-12.0,
                ratio=4.0,
                attack=5.0,
                release=50.0
            )
        return audio_segment

    def apply_audio_quality_settings(self, audio_segment):
        """Apply quality settings to audio segment"""
        
        # Convert to mono/stereo
        target_channels = self._get_config_value('audio_channels', 1)
        if target_channels == 1 and audio_segment.channels > 1:
            audio_segment = audio_segment.set_channels(1)
        elif target_channels == 2 and audio_segment.channels == 1:
            # Convert mono to stereo by duplicating channel
            audio_segment = audio_segment.set_channels(2)
        
        # Set sample rate
        target_rate = int(self._get_config_value('sample_rate', 22050))
        if audio_segment.frame_rate != target_rate:
            audio_segment = audio_segment.set_frame_rate(target_rate)
        
        # Apply volume normalization if enabled
        audio_segment = self.normalize_audio_level(audio_segment)
        
        # Apply limiter if enabled
        audio_segment = self.apply_soft_limiter(audio_segment)
        
        return audio_segment

    def export_with_high_quality(self, audio_segment, output_path):
        """Export audio with high quality settings"""
        
        # Apply quality settings first
        audio_segment = self.apply_audio_quality_settings(audio_segment)
        
        # Get format from output path
        format_type = Path(output_path).suffix.lower().lstrip('.')
        
        if format_type == "mp3":
            # High quality MP3 export
            bitrate = self._get_config_value('audio_bitrate', '192k')
            mp3_quality = self._get_config_value('mp3_quality', 2)
            
            # Use high quality parameters
            audio_segment.export(
                output_path, 
                format="mp3",
                bitrate=bitrate,
                parameters=[
                    "-q:a", str(mp3_quality),      # Quality (0=best)
                    "-compression_level", "0",      # No compression
                    "-joint_stereo", "0",          # No joint stereo
                    "-reservoir", "1",             # Enable bit reservoir
                    "-abr", "1" if "k" in bitrate else "0"  # Enable ABR
                ]
            )
        elif format_type == "wav":
            # High quality WAV export
            bit_depth = self._get_config_value('wav_bit_depth', 16)
            sample_rate = self._get_config_value('sample_rate', 22050)
            
            if bit_depth == 16:
                codec = "pcm_s16le"
            elif bit_depth == 24:
                codec = "pcm_s24le" 
            elif bit_depth == 32:
                codec = "pcm_s32le"
            else:
                codec = "pcm_s16le"  # Default to 16-bit for compatibility
                
            audio_segment.export(
                output_path,
                format="wav",
                parameters=[
                    "-acodec", codec, 
                    "-ar", str(sample_rate),
                    "-ac", str(audio_segment.channels)
                ]
            )
        else:
            # For other formats, use default high quality
            bitrate = self._get_config_value('audio_bitrate', '192k')
            audio_segment.export(output_path, format=format_type, bitrate=bitrate)
        
        # Log quality information
        sample_rate = self._get_config_value('sample_rate', 22050)
        bit_depth = self._get_config_value('wav_bit_depth', 16)
        bitrate = self._get_config_value('audio_bitrate', '192k')
        
        logger.info(f"🎵 Exported {self.prefix.upper()}audio with HIGH QUALITY: {format_type.upper()}, "
                   f"{sample_rate}Hz, {bit_depth}-bit, {bitrate}")
        
        return True

    def get_quality_preset_configs(self):
        """Get predefined quality preset configurations"""
        return {
            "mobile": {
                "sample_rate": 16000,
                "audio_bitrate": "128k", 
                "audio_channels": 1,
                "wav_bit_depth": 16,
                "mp3_quality": 4,
                "enable_limiter": True,
                "normalize_volume": True
            },
            "desktop": {
                "sample_rate": 22050,
                "audio_bitrate": "192k",
                "audio_channels": 1, 
                "wav_bit_depth": 16,
                "mp3_quality": 2,
                "enable_limiter": True,
                "normalize_volume": True
            },
            "high": {
                "sample_rate": 44100,
                "audio_bitrate": "256k",
                "audio_channels": 1,
                "wav_bit_depth": 24,
                "mp3_quality": 1,
                "enable_limiter": True,
                "normalize_volume": True
            },
            "max": {
                "sample_rate": 44100,
                "audio_bitrate": "320k",
                "audio_channels": 2,
                "wav_bit_depth": 24,
                "mp3_quality": 0,
                "enable_limiter": True,
                "normalize_volume": True
            }
        }

def apply_preset_to_config(config, preset_name, provider_prefix):
    """
    Apply a quality preset to configuration
    
    Args:
        config: Configuration object to modify
        preset_name: Name of preset ('mobile', 'desktop', 'high', 'max')
        provider_prefix: Provider prefix ('coqui_', 'piper_', 'kokoro_')
    """
    processor = AudioQualityProcessor(config, provider_prefix)
    presets = processor.get_quality_preset_configs()
    
    if preset_name not in presets:
        logger.warning(f"Unknown preset '{preset_name}', using 'desktop'")
        preset_name = "desktop"
    
    preset = presets[preset_name]
    
    # Apply preset values to config
    for setting, value in preset.items():
        full_name = f"{provider_prefix}{setting}"
        setattr(config, full_name, value)
    
    logger.info(f"Applied {preset_name} quality preset to {provider_prefix}")
    
    return preset