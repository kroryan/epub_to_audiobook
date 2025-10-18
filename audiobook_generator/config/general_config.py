class GeneralConfig:
    def __init__(self, args):
        # General arguments
        self.input_file = getattr(args, 'input_file', None)
        self.output_folder = getattr(args, 'output_folder', None)
        self.preview = getattr(args, 'preview', None)
        self.output_text = getattr(args, 'output_text', None)
        self.log = getattr(args, 'log', None)
        self.log_file = None
        self.no_prompt = getattr(args, 'no_prompt', None)
        self.worker_count = getattr(args, 'worker_count', None)
        self.use_pydub_merge = getattr(args, 'use_pydub_merge', None)

        # Book parser specific arguments
        self.title_mode = getattr(args, 'title_mode', None)
        self.newline_mode = getattr(args, 'newline_mode', None)
        self.chapter_start = getattr(args, 'chapter_start', None)
        self.chapter_end = getattr(args, 'chapter_end', None)
        self.remove_endnotes = getattr(args, 'remove_endnotes', None)
        self.remove_reference_numbers = getattr(args, 'remove_reference_numbers', None)
        self.search_and_replace_file = getattr(args, 'search_and_replace_file', None)

        # TTS provider: common arguments
        self.tts = getattr(args, 'tts', None)
        self.language = getattr(args, 'language', None)
        self.voice_name = getattr(args, 'voice_name', None)
        self.output_format = getattr(args, 'output_format', None)
        self.model_name = getattr(args, 'model_name', None)

        # OpenAI specific arguments
        self.instructions = getattr(args, 'instructions', None)
        self.speed = getattr(args, 'speed', None)

        # TTS provider: Azure & Edge TTS specific arguments
        self.break_duration = getattr(args, 'break_duration', None)

        # TTS provider: Edge specific arguments
        self.voice_rate = getattr(args, 'voice_rate', None)
        self.voice_volume = getattr(args, 'voice_volume', None)
        self.voice_pitch = getattr(args, 'voice_pitch', None)
        self.proxy = getattr(args, 'proxy', None)

        # TTS provider: Piper specific arguments
        self.piper_path = getattr(args, 'piper_path', None)
        self.piper_docker_image = getattr(args, 'piper_docker_image', None)
        self.piper_speaker = getattr(args, 'piper_speaker', None)
        self.piper_noise_scale = getattr(args, 'piper_noise_scale', None)
        self.piper_noise_w_scale = getattr(args, 'piper_noise_w_scale', None)
        self.piper_length_scale = getattr(args, 'piper_length_scale', None)
        self.piper_sentence_silence = getattr(args, 'piper_sentence_silence', None)
        self.piper_device = getattr(args, 'piper_device', None)
        # TTS provider: Coqui TTS specific arguments
        self.coqui_path = getattr(args, 'coqui_path', None)
        self.coqui_model = getattr(args, 'coqui_model', None)
        self.coqui_speaker = getattr(args, 'coqui_speaker', None)
        self.coqui_speaker_wav = getattr(args, 'coqui_speaker_wav', None)  # For voice cloning
        self.coqui_language = getattr(args, 'coqui_language', None)  # For multilingual models
        self.coqui_length_scale = getattr(args, 'coqui_length_scale', None)
        self.coqui_noise_scale = getattr(args, 'coqui_noise_scale', None)
        self.coqui_noise_w_scale = getattr(args, 'coqui_noise_w_scale', None)
        self.coqui_device = getattr(args, 'coqui_device', None)
        
        # === CONFIGURACIÓN DE CALIDAD DE AUDIO COQUI ===
        self.coqui_sample_rate = getattr(args, 'coqui_sample_rate', 44100)        # 22050, 44100, 48000 Hz
        self.coqui_audio_bitrate = getattr(args, 'coqui_audio_bitrate', "320k")   # 128k, 192k, 256k, 320k
        self.coqui_audio_channels = getattr(args, 'coqui_audio_channels', 1)      # 1 (mono), 2 (estéreo)
        self.coqui_wav_bit_depth = getattr(args, 'coqui_wav_bit_depth', 24)      # 16, 24, 32 bits
        self.coqui_mp3_quality = getattr(args, 'coqui_mp3_quality', 0)           # 0 (mejor) a 9 (peor)
        self.coqui_enable_limiter = getattr(args, 'coqui_enable_limiter', True)  # Limiter para mejor calidad
        self.coqui_normalize_volume = getattr(args, 'coqui_normalize_volume', True) # Normalización de volumen
        
        # === CONFIGURACIÓN DE CALIDAD DE AUDIO PIPER ===
        self.piper_sample_rate = getattr(args, 'piper_sample_rate', 22050)        # 16000, 22050, 44100 Hz
        self.piper_audio_bitrate = getattr(args, 'piper_audio_bitrate', "192k")   # 128k, 192k, 256k, 320k
        self.piper_audio_channels = getattr(args, 'piper_audio_channels', 1)      # 1 (mono), 2 (estéreo)
        self.piper_wav_bit_depth = getattr(args, 'piper_wav_bit_depth', 16)      # 16, 24 bits
        self.piper_mp3_quality = getattr(args, 'piper_mp3_quality', 2)           # 0 (mejor) a 9 (peor)
        self.piper_enable_limiter = getattr(args, 'piper_enable_limiter', True)  # Limiter para mejor calidad
        self.piper_normalize_volume = getattr(args, 'piper_normalize_volume', True) # Normalización de volumen
        
        # === CONFIGURACIÓN DE CALIDAD DE AUDIO KOKORO ===
        self.kokoro_sample_rate = getattr(args, 'kokoro_sample_rate', 22050)      # 16000, 22050, 44100 Hz
        self.kokoro_audio_bitrate = getattr(args, 'kokoro_audio_bitrate', "192k") # 128k, 192k, 256k, 320k
        self.kokoro_audio_channels = getattr(args, 'kokoro_audio_channels', 1)    # 1 (mono), 2 (estéreo)
        self.kokoro_wav_bit_depth = getattr(args, 'kokoro_wav_bit_depth', 16)    # 16, 24 bits
        self.kokoro_mp3_quality = getattr(args, 'kokoro_mp3_quality', 2)         # 0 (mejor) a 9 (peor)
        self.kokoro_enable_limiter = getattr(args, 'kokoro_enable_limiter', True) # Limiter para mejor calidad
        self.kokoro_normalize_volume = getattr(args, 'kokoro_normalize_volume', True) # Normalización de volumen

    def __str__(self):
        return ",\n".join(f"{key}={value}" for key, value in self.__dict__.items())
