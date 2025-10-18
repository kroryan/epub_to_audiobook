#!/usr/bin/env python3
"""
Script de prueba simple para la interfaz Coqui TTS
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from audiobook_generator.tts_providers.coqui_tts_provider import (
    get_coqui_supported_models, 
    get_coqui_supported_voices, 
    get_coqui_model_info,
    get_coqui_supported_languages_for_model,
    get_coqui_supported_languages
)

def test_spanish_functionality():
    """Probar funcionalidad específica para español."""
    print("🇪🇸 Probando funcionalidad de Coqui TTS para español...")
    
    # Probar modelos disponibles
    print("\n📋 Modelos disponibles:")
    models = get_coqui_supported_models()
    spanish_models = [m for m in models if "/es/" in m or "multilingual" in m]
    for i, model in enumerate(spanish_models[:10], 1):  # Mostrar los primeros 10
        print(f"  {i}. {model}")
    
    # Probar XTTS-v2 específicamente
    print("\n🎯 Probando XTTS-v2:")
    xtts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
    voices = get_coqui_supported_voices(xtts_model)
    print(f"  Voces disponibles: {len(voices)}")
    for i, voice in enumerate(voices[:5], 1):  # Primeras 5 voces
        print(f"    {i}. {voice}")
    
    # Probar modelo español específico
    print("\n🇪🇸 Probando modelo CSS10 español:")
    css10_model = "tts_models/es/css10/vits"
    css10_voices = get_coqui_supported_voices(css10_model)
    print(f"  Voces CSS10: {css10_voices}")
    
    # Probar idiomas soportados
    print("\n🌍 Idiomas soportados:")
    languages = get_coqui_supported_languages()
    print(f"  {languages[:8]}...")  # Primeros 8 idiomas
    
    print("\n✅ Prueba completada exitosamente!")

if __name__ == "__main__":
    test_spanish_functionality()