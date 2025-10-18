#!/usr/bin/env python3
"""
Script de configuración para usar Kokoro TTS como endpoint OpenAI compatible en puerto 8880.

Este script configura el entorno para usar Kokoro TTS localmente a través del puerto 8880,
compatible con la API de OpenAI para síntesis de texto a voz.

Uso:
    1. Asegúrate de que Kokoro TTS esté ejecutándose en http://localhost:8880
    2. Ejecuta este script para configurar las variables de entorno
    3. Usa el conversor con --tts openai

Ejemplo:
    python setup_kokoro_8880.py
    python main.py libro.epub output/ --tts openai --voice_name "dora" --model_name "tts-1"
"""

import os
import sys
import subprocess
import requests
import time
import json

def check_kokoro_running(port=8880, max_retries=3):
    """Verificar si Kokoro TTS está ejecutándose en el puerto especificado."""
    base_url = f"http://localhost:{port}"
    
    for attempt in range(max_retries):
        try:
            # Intentar acceder al endpoint de salud
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Kokoro TTS está ejecutándose en {base_url}")
                return True
        except requests.exceptions.RequestException as e:
            print(f"Error conectando: {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ Intento {attempt + 1}/{max_retries}: Kokoro TTS no está disponible, reintentando...")
            time.sleep(2)
    
    return False

def get_available_voices(port=8880):
    """Obtener lista de voces disponibles en Kokoro TTS."""
    try:
        base_url = f"http://localhost:{port}"
        response = requests.get(f"{base_url}/v1/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"📢 Modelos disponibles en Kokoro TTS:")
            for model in models.get('data', []):
                print(f"   - {model.get('id', 'unknown')}")
            return models
    except Exception as e:
        print(f"⚠️  No se pudieron obtener las voces disponibles: {e}")
    return None

def search_spanish_voices(port=8880):
    """Buscar voces en español específicamente."""
    spanish_voices = []
    known_spanish_voices = ['dora', 'alex', 'santa', 'es_dora', 'es_alex', 'es_santa']
    
    print(f"🔍 Buscando voces en español...")
    for voice in known_spanish_voices:
        if test_voice_exists(voice, port):
            spanish_voices.append(voice)
            print(f"   ✅ Encontrada: {voice}")
        else:
            print(f"   ❌ No encontrada: {voice}")
    
    return spanish_voices

def test_voice_exists(voice_name, port=8880):
    """Probar si una voz específica existe."""
    try:
        base_url = f"http://localhost:{port}/v1"
        
        # Crear cliente OpenAI temporal
        import openai
        client = openai.OpenAI(base_url=base_url, api_key="fake")
        
        # Intentar generar audio muy corto
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice_name,
            input="test",
            response_format="mp3"
        )
        
        return len(response.content) > 0
        
    except Exception as e:
        return False

def setup_environment_variables(port=8880):
    """Configurar variables de entorno para usar Kokoro TTS."""
    base_url = f"http://localhost:{port}/v1"
    
    # Configurar variables de entorno
    os.environ['OPENAI_BASE_URL'] = base_url
    os.environ['OPENAI_API_KEY'] = 'fake_key_for_kokoro'
    
    print(f"🔧 Variables de entorno configuradas:")
    print(f"   OPENAI_BASE_URL = {base_url}")
    print(f"   OPENAI_API_KEY = fake_key_for_kokoro")
    
    return base_url

def test_kokoro_tts(port=8880, voice="af_bella", test_text="Hola, esto es una prueba de Kokoro TTS."):
    """Hacer una prueba básica de Kokoro TTS."""
    try:
        import tempfile
        from openai import OpenAI
        
        base_url = f"http://localhost:{port}/v1"
        client = OpenAI(base_url=base_url, api_key="fake_key_for_kokoro")
        
        print(f"🧪 Probando síntesis con voz '{voice}'...")
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=test_text,
            response_format="mp3"
        )
        
        # Guardar archivo temporal para verificar
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_filename = temp_file.name
        
        print(f"✅ Prueba exitosa! Audio generado: {temp_filename}")
        print(f"   Tamaño del archivo: {len(response.content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def print_usage_examples():
    """Mostrar ejemplos de uso."""
    print(f"\n📖 Ejemplos de uso con Kokoro TTS:")
    print(f"")
    print(f"1. Conversión básica con voz española:")
    print(f"   python main.py libro.epub output/ --tts openai --voice_name dora --model_name tts-1")
    print(f"")
    print(f"2. Con otras voces españolas:")
    print(f"   python main.py libro.epub output/ --tts openai --voice_name alex --model_name tts-1")
    print(f"   python main.py libro.epub output/ --tts openai --voice_name santa --model_name tts-1")
    print(f"")
    print(f"3. Con configuraciones específicas:")
    print(f"   python main.py libro.epub output/ --tts openai --voice_name dora --model_name tts-1 --speed 1.2")
    print(f"")
    print(f"4. Solo algunos capítulos:")
    print(f"   python main.py libro.epub output/ --tts openai --voice_name dora --model_name tts-1 --chapter_start 1 --chapter_end 3")
    print(f"")
    print(f"💡 Voces españolas de Kokoro:")
    print(f"   - dora: Voz femenina española natural")
    print(f"   - alex: Voz masculina española") 
    print(f"   - santa: Voz femenina española alternativa")
    print(f"")
    print(f"🔗 Más voces disponibles en: https://huggingface.co/spaces/hexgrad/Kokoro-TTS")
    print(f"🌐 Interface web: http://localhost:8880/web/")

def main():
    print("🚀 Configurando Kokoro TTS como endpoint OpenAI compatible (Puerto 8880)")
    print("=" * 70)
    
    port = 8880
    
    # Verificar si Kokoro está ejecutándose
    if not check_kokoro_running(port):
        print(f"\n❌ Error: Kokoro TTS no está ejecutándose en el puerto {port}")
        print(f"\n💡 Para iniciar Kokoro TTS:")
        print(f"   - Con Docker: docker run -p {port}:8880 ghcr.io/remsky/kokoro-fastapi-cpu")
        print(f"   - Con GPU: docker run --gpus all -p {port}:8880 ghcr.io/remsky/kokoro-fastapi-gpu")
        print(f"   - Con Docker Compose: docker compose -f docker-compose.kokoro-example.yml up")
        sys.exit(1)
    
    # Configurar variables de entorno
    base_url = setup_environment_variables(port)
    
    # Obtener voces disponibles
    get_available_voices(port)
    
    # Buscar voces en español
    spanish_voices = search_spanish_voices(port)
    if spanish_voices:
        print(f"\n🇪🇸 Voces en español encontradas: {', '.join(spanish_voices)}")
    else:
        print(f"\n⚠️  No se encontraron voces específicamente en español, pero puedes usar las voces estándar.")
    
    # Realizar prueba básica
    print(f"\n🧪 Realizando prueba de conectividad...")
    test_voice = spanish_voices[0] if spanish_voices else "af_bella"
    if test_kokoro_tts(port, voice=test_voice):
        print(f"✅ ¡Kokoro TTS está configurado y funcionando correctamente!")
    else:
        print(f"⚠️  La prueba falló, pero puedes intentar usar el sistema de todas formas.")
    
    # Mostrar ejemplos de uso
    print_usage_examples()
    
    print(f"\n🎉 ¡Configuración completada!")
    print(f"   Ahora puedes usar --tts openai para acceder a Kokoro TTS en el puerto {port}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Configuración cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)