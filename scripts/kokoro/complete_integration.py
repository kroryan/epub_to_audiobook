#!/usr/bin/env python3
"""
Script para completar la integración avanzada de Kokoro TTS
Actualiza automáticamente los archivos necesarios
"""

import os
import sys
from pathlib import Path

def update_main_py():
    """Actualiza main.py para incluir Kokoro como opción independiente"""
    main_path = Path("main.py")
    
    if not main_path.exists():
        print("❌ main.py no encontrado")
        return False
        
    content = main_path.read_text(encoding='utf-8')
    
    # Actualizar la descripción de help para incluir Kokoro
    if "--tts" in content and "kokoro" not in content:
        content = content.replace(
            'help="Choose TTS provider (default: azure). azure: Azure Cognitive Services, openai: OpenAI TTS API. When using azure, environment variables MS_TTS_KEY and MS_TTS_REGION must be set. When using openai, environment variable OPENAI_API_KEY must be set."',
            'help="Choose TTS provider (default: azure). azure: Azure Cognitive Services, openai: OpenAI TTS API, kokoro: Local Kokoro TTS server. When using azure, environment variables MS_TTS_KEY and MS_TTS_REGION must be set. When using openai, environment variable OPENAI_API_KEY must be set. When using kokoro, ensure local server is running on http://localhost:8880."'
        )
        
        # Agregar argumentos específicos de Kokoro
        kokoro_args = '''
    kokoro_tts_group = parser.add_argument_group(title="kokoro specific")
    kokoro_tts_group.add_argument(
        "--kokoro_base_url",
        default="http://localhost:8880",
        help="Base URL for Kokoro TTS server",
    )
    kokoro_tts_group.add_argument(
        "--kokoro_volume_multiplier",
        default=1.0,
        type=float,
        help="Volume multiplier for audio output (0.1 to 2.0)",
    )
    kokoro_tts_group.add_argument(
        "--kokoro_voice_combination",
        help="Combine voices using syntax like 'voice1+voice2(0.5)' or 'voice1-voice2(0.3)'",
    )
    kokoro_tts_group.add_argument(
        "--kokoro_stream",
        action="store_true",
        default=True,
        help="Use streaming mode for faster generation",
    )
    kokoro_tts_group.add_argument(
        "--kokoro_return_timestamps",
        action="store_true",
        help="Include word-level timestamps in output",
    )
    kokoro_tts_group.add_argument(
        "--kokoro_normalize_text",
        action="store_true",
        default=True,
        help="Enable advanced text normalization (URLs, emails, phones, etc.)",
    )
'''
        
        # Buscar el lugar adecuado para insertar (después de coqui_tts_group)
        if "coqui_tts_group.add_argument(" in content:
            # Encontrar el final del grupo coqui
            coqui_end = content.rfind("coqui_tts_group.add_argument(")
            # Encontrar el final de esa línea y sus argumentos
            next_section_start = content.find("\n\n", coqui_end)
            if next_section_start != -1:
                content = content[:next_section_start] + kokoro_args + content[next_section_start:]
        
        main_path.write_text(content, encoding='utf-8')
        print("✅ main.py actualizado con argumentos de Kokoro")
        return True
    else:
        print("✅ main.py ya tiene soporte para Kokoro")
        return True


def update_requirements():
    """Actualiza requirements.txt para incluir las dependencias necesarias"""
    req_path = Path("requirements.txt")
    
    if not req_path.exists():
        print("❌ requirements.txt no encontrado")
        return False
    
    content = req_path.read_text()
    
    # Dependencias adicionales para Kokoro
    additional_deps = [
        "torch>=2.0.0",
        "torchaudio>=2.0.0", 
        "numpy>=1.21.0",
        "requests>=2.25.0"
    ]
    
    needs_update = False
    for dep in additional_deps:
        dep_name = dep.split('>=')[0]
        if dep_name not in content:
            content += f"\n{dep}"
            needs_update = True
    
    if needs_update:
        req_path.write_text(content)
        print("✅ requirements.txt actualizado")
    else:
        print("✅ requirements.txt ya tiene las dependencias necesarias")
    
    return True


def create_example_config():
    """Crea un archivo de configuración de ejemplo para Kokoro"""
    example_path = Path("examples/kokoro_config_example.py")
    example_path.parent.mkdir(exist_ok=True)
    
    config_example = '''#!/usr/bin/env python3
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
        print(f"\\n📋 {category}:")
        for cmd in commands:
            print(f"   {cmd}")
    
    print("\\n💡 CARACTERÍSTICAS SOPORTADAS:")
    print("   ✅ Mezcla de voces con pesos")
    print("   ✅ Normalización avanzada de texto")
    print("   ✅ Múltiples idiomas y acentos")
    print("   ✅ Control de volumen y velocidad")
    print("   ✅ Calidad de audio personalizable")
    print("   ✅ Streaming en tiempo real")
    print("   ✅ Completamente gratuito")
'''
    
    example_path.write_text(config_example, encoding='utf-8')
    print(f"✅ Creado ejemplo de configuración: {example_path}")
    return True


def create_voice_samples_script():
    """Crea script para descargar y probar voces"""
    script_path = Path("scripts/kokoro/test_all_voices.py")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    
    script_content = '''#!/usr/bin/env python3
"""
Script para probar todas las voces disponibles en Kokoro
Genera muestras de audio para cada voz y idioma
"""

import requests
import json
import os
from pathlib import Path
import time

def get_available_voices(base_url="http://localhost:8880"):
    """Obtener lista de voces disponibles"""
    try:
        response = requests.get(f"{base_url}/v1/audio/voices", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('voices', [])
        return []
    except Exception as e:
        print(f"Error obteniendo voces: {e}")
        return []

def test_voice_combination(voice_spec, text, base_url="http://localhost:8880", lang_code=""):
    """Probar una combinación de voces específica"""
    try:
        url = f"{base_url}/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "voice": voice_spec,
            "input": text,
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False,
            "lang_code": lang_code
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return True, response.content
        else:
            return False, f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, str(e)

def main():
    """Función principal para probar voces"""
    base_url = "http://localhost:8880"
    output_dir = Path("voice_samples")
    output_dir.mkdir(exist_ok=True)
    
    # Obtener voces disponibles
    print("🎤 Obteniendo lista de voces...")
    voices = get_available_voices(base_url)
    
    if not voices:
        print("❌ No se pudieron obtener voces. ¿Está ejecutándose Kokoro?")
        return
    
    print(f"✅ Encontradas {len(voices)} voces")
    
    # Textos de prueba por idioma
    test_texts = {
        "": "Hello, this is a test of the selected voice.",
        "a": "Hello, this is a test of the American English voice.", 
        "b": "Hello, this is a test of the British English voice.",
        "e": "Hola, esta es una prueba de la voz en español.",
        "f": "Bonjour, ceci est un test de la voix française.",
        "i": "Ciao, questo è un test della voce italiana.",
        "p": "Olá, este é um teste da voz portuguesa.",
        "j": "こんにちは、これは選択された音声のテストです。",
        "z": "你好，这是所选语音的测试。"
    }
    
    # Probar combinaciones interesantes
    voice_combinations = [
        "af_bella+af_sky(0.3)",
        "af_heart+ef_dora(0.4)", 
        "bf_emma+af_bella(0.5)",
        "ef_dora+em_alex(0.5)",
        "af_bella-am_adam(0.2)"
    ]
    
    # Probar voces individuales por categoría
    categories = {}
    for voice in voices:
        prefix = voice[:2] if len(voice) > 1 else voice[0]
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(voice)
    
    print("\\n📊 Voces por categoría:")
    for prefix, voice_list in sorted(categories.items()):
        lang_name = {
            'af': 'American Female', 'am': 'American Male',
            'bf': 'British Female', 'bm': 'British Male', 
            'ef': 'Spanish Female', 'em': 'Spanish Male',
            'pf': 'Portuguese Female', 'pm': 'Portuguese Male'
        }.get(prefix, f'Other ({prefix})')
        print(f"   {prefix}: {lang_name} ({len(voice_list)} voces)")
    
    # Probar algunas voces representativas
    test_voices = []
    for prefix, voice_list in categories.items():
        if voice_list:
            test_voices.append(voice_list[0])  # Primera voz de cada categoría
    
    print(f"\\n🎧 Probando {len(test_voices)} voces representativas...")
    
    success_count = 0
    for i, voice in enumerate(test_voices, 1):
        print(f"   [{i}/{len(test_voices)}] {voice}...")
        
        # Determinar idioma por prefijo
        lang_code = voice[0].lower()
        text = test_texts.get(lang_code, test_texts[""])
        
        success, result = test_voice_combination(voice, text, base_url, lang_code)
        
        if success:
            # Guardar muestra
            sample_file = output_dir / f"{voice}_sample.mp3"
            with open(sample_file, 'wb') as f:
                f.write(result)
            print(f"      ✅ Guardado: {sample_file}")
            success_count += 1
        else:
            print(f"      ❌ Error: {result}")
        
        time.sleep(0.5)  # Pequeña pausa entre requests
    
    print(f"\\n🎤 Probando {len(voice_combinations)} combinaciones...")
    
    for i, combination in enumerate(voice_combinations, 1):
        print(f"   [{i}/{len(voice_combinations)}] {combination}...")
        
        # Usar texto en inglés para combinaciones
        success, result = test_voice_combination(combination, test_texts["a"], base_url, "a")
        
        if success:
            safe_name = combination.replace("+", "_plus_").replace("-", "_minus_").replace("(", "_").replace(")", "")
            sample_file = output_dir / f"combo_{safe_name}_sample.mp3"
            with open(sample_file, 'wb') as f:
                f.write(result)
            print(f"      ✅ Guardado: {sample_file}")
            success_count += 1
        else:
            print(f"      ❌ Error: {result}")
            
        time.sleep(0.5)
    
    total_tests = len(test_voices) + len(voice_combinations)
    print(f"\\n✨ Completado: {success_count}/{total_tests} muestras generadas")
    print(f"📁 Muestras guardadas en: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
'''
    
    script_path.write_text(script_content, encoding='utf-8')
    print(f"✅ Creado script de prueba de voces: {script_path}")
    return True


def main():
    """Función principal del script de actualización"""
    print("🚀 ACTUALIZANDO INTEGRACIÓN AVANZADA DE KOKORO TTS")
    print("=" * 60)
    
    success_count = 0
    total_tasks = 4
    
    # 1. Actualizar main.py
    if update_main_py():
        success_count += 1
    
    # 2. Actualizar requirements.txt
    if update_requirements():
        success_count += 1
    
    # 3. Crear ejemplo de configuración
    if create_example_config():
        success_count += 1
    
    # 4. Crear script de prueba de voces
    if create_voice_samples_script():
        success_count += 1
    
    print(f"\\n🎯 RESUMEN DE ACTUALIZACIÓN")
    print("=" * 30)
    print(f"✅ Tareas completadas: {success_count}/{total_tasks}")
    
    if success_count == total_tasks:
        print("\\n🎉 ¡INTEGRACIÓN COMPLETADA!")
        print("\\n📋 PRÓXIMOS PASOS:")
        print("1. Ejecutar: pip install -r requirements.txt")
        print("2. Iniciar servidor Kokoro: cd Kokoro-FastAPI && python -m api.src.main")
        print("3. Probar con: python main.py --tts kokoro --help")
        print("4. Usar interfaz web: python main_ui.py")
        print("\\n💡 NUEVAS CARACTERÍSTICAS DISPONIBLES:")
        print("   🎤 Mezcla avanzada de voces")
        print("   📝 Normalización inteligente de texto")
        print("   🌍 Soporte multi-idioma completo")
        print("   🎛️ Control granular de parámetros")
        print("   ⚡ Streaming en tiempo real")
        print("   🎯 Calidad de audio personalizable")
    else:
        print("\\n⚠️  Algunas tareas fallaron. Revisa los errores arriba.")
    
    return success_count == total_tasks


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)