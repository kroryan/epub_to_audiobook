#!/usr/bin/env python3
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
    
    print("\n📊 Voces por categoría:")
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
    
    print(f"\n🎧 Probando {len(test_voices)} voces representativas...")
    
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
    
    print(f"\n🎤 Probando {len(voice_combinations)} combinaciones...")
    
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
    print(f"\n✨ Completado: {success_count}/{total_tests} muestras generadas")
    print(f"📁 Muestras guardadas en: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
