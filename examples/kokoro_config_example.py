#!/usr/bin/env python3
"""
Ejemplo de configuración avanzada para Kokoro TTS
Demuestra todas las funcionalidades disponibles
"""

# Configuración básica
KOKORO_BASE_URL = "http://localhost:8880"
KOKORO_MODEL = "kokoro"

# Configuración de voz simple
BASIC_VOICE = "af_heart"

# Configuración de mezcla de voces
VOICE_COMBINATIONS = {
    "balanced_female": "af_bella+af_sky(0.3)",
    "dramatic_mix": "af_heart+ef_dora(0.4)",
    "subtle_british": "af_bella+bf_emma(0.2)",
    "spanish_blend": "ef_dora+em_alex(0.5)",
    "contrast_voices": "af_bella-am_adam(0.3)"  # Restar voz masculina
}

# Configuración de normalización de texto
TEXT_NORMALIZATION = {
    "normalize": True,
    "unit_normalization": True,        # 10KB → 10 kilobytes
    "url_normalization": True,         # URLs pronunciables
    "email_normalization": True,       # Emails pronunciables
    "pluralization_normalization": True,  # (s) → s
    "phone_normalization": True,       # Teléfonos pronunciables
    "replace_symbols": True           # Símbolos → palabras
}

# Configuración avanzada
ADVANCED_SETTINGS = {
    "volume_multiplier": 1.2,         # Volumen 20% más alto
    "stream": True,                   # Streaming habilitado
    "return_timestamps": False,       # Sin timestamps por defecto
    "return_download_link": False,    # Sin enlaces de descarga
    "voice_weight_normalization": True  # Normalizar pesos automáticamente
}

# Configuración de calidad de audio
QUALITY_PRESETS = {
    "mobile": {
        "sample_rate": 22050,
        "bitrate": "128k",
        "channels": 1,
        "format": "mp3"
    },
    "desktop": {
        "sample_rate": 44100,
        "bitrate": "192k", 
        "channels": 2,
        "format": "mp3"
    },
    "high_quality": {
        "sample_rate": 48000,
        "bitrate": "320k",
        "channels": 2,
        "format": "flac"
    }
}

# Ejemplo de uso con la línea de comandos
def generate_command_examples():
    """Genera ejemplos de comandos para usar con Kokoro"""
    
    examples = {
        "Básico": [
            "python main.py input.epub output/ --tts kokoro --voice_name af_heart"
        ],
        
        "Con mezcla de voces": [
            "python main.py input.epub output/ --tts kokoro --voice_name 'af_bella+af_sky(0.3)'",
            "python main.py input.epub output/ --tts kokoro --voice_name 'ef_dora+em_alex(0.5)'"
        ],
        
        "Con configuración avanzada": [
            "python main.py input.epub output/ --tts kokoro --voice_name af_heart --kokoro_volume_multiplier 1.2 --kokoro_normalize_text",
            "python main.py input.epub output/ --tts kokoro --voice_name 'af_bella-am_adam(0.2)' --kokoro_stream --language e"
        ],
        
        "Calidad específica": [
            "python main.py input.epub output/ --tts kokoro --voice_name af_heart --output_format flac --speed 0.9"
        ]
    }
    
    return examples

if __name__ == "__main__":
    examples = generate_command_examples()
    
    print("🎤 EJEMPLOS DE USO KOKORO TTS")
    print("=" * 50)
    
    for category, commands in examples.items():
        print(f"\n📋 {category}:")
        for cmd in commands:
            print(f"   {cmd}")
    
    print("\n💡 CARACTERÍSTICAS SOPORTADAS:")
    print("   ✅ Mezcla de voces con pesos")
    print("   ✅ Normalización avanzada de texto")
    print("   ✅ Múltiples idiomas y acentos")
    print("   ✅ Control de volumen y velocidad")
    print("   ✅ Calidad de audio personalizable")
    print("   ✅ Streaming en tiempo real")
    print("   ✅ Completamente gratuito")
