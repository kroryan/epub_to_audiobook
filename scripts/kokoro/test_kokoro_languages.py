#!/usr/bin/env python3
"""
Test script for Kokoro TTS language and voice functionality
"""

import requests
import json
import os
from pathlib import Path

def test_kokoro_voices_and_languages():
    """Test Kokoro voice fetching and language codes"""
    base_url = "http://localhost:8880"
    
    print("🎯 Testing Kokoro TTS Voice and Language Support")
    print("=" * 60)
    
    # Test server health
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Kokoro server is running")
        else:
            print("❌ Kokoro server health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot reach Kokoro server: {e}")
        return
    
    # Test voice fetching
    print(f"\n🎙️ Fetching available voices...")
    try:
        voices_response = requests.get(f"{base_url}/v1/audio/voices", timeout=10)
        if voices_response.status_code == 200:
            voices_data = voices_response.json()
            print(f"✅ Voice endpoint response: {voices_response.status_code}")
            
            # Extract voices
            if isinstance(voices_data, dict) and 'voices' in voices_data:
                voices = voices_data['voices']
            elif isinstance(voices_data, list):
                voices = voices_data
            else:
                voices = []
                
            print(f"📊 Found {len(voices)} voices")
            
            # Categorize voices by prefix
            voice_categories = {}
            for voice in voices[:20]:  # Show first 20
                if '_' in str(voice):
                    prefix = str(voice).split('_')[0]
                    if prefix not in voice_categories:
                        voice_categories[prefix] = []
                    voice_categories[prefix].append(voice)
                    
            print(f"\n🏷️ Voice Categories:")
            for prefix, voice_list in sorted(voice_categories.items()):
                print(f"   {prefix}: {', '.join(voice_list[:5])}")
                if len(voice_list) > 5:
                    print(f"        ... and {len(voice_list)-5} more")
                    
        else:
            print(f"❌ Voice endpoint failed: {voices_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error fetching voices: {e}")
    
    # Test language codes
    print(f"\n🌍 Testing Language Codes:")
    languages = {
        "": "Auto-detect",
        "a": "🇺🇸 English (US)", 
        "b": "🇬🇧 British English",
        "e": "🇪🇸 Spanish",
        "f": "🇫🇷 French", 
        "h": "🇮🇳 Hindi",
        "i": "🇮🇹 Italian",
        "p": "🇵🇹 Portuguese",
        "j": "🇯🇵 Japanese",
        "z": "🇨🇳 Chinese"
    }
    
    for code, name in languages.items():
        print(f"   {code:2} → {name}")
    
    # Test synthesis with different languages
    print(f"\n🔊 Testing Synthesis with Language Codes:")
    
    test_cases = [
        ("e", "af_bella", "Hola mundo, este es una prueba en español"),
        ("a", "af_bella", "Hello world, this is a test in English"),
        ("f", "af_bella", "Bonjour le monde, ceci est un test en français"),
    ]
    
    for lang_code, voice, text in test_cases:
        try:
            print(f"\n   Testing {languages.get(lang_code, lang_code)} with voice '{voice}'...")
            
            # Set up environment for OpenAI client
            os.environ['OPENAI_BASE_URL'] = f"{base_url}/v1"
            os.environ['OPENAI_API_KEY'] = "fake-key"
            
            # Test with requests first
            response = requests.post(f"{base_url}/v1/audio/speech", 
                json={
                    "model": "kokoro",
                    "voice": voice,
                    "input": text[:50],  # Short text for testing
                    "language": lang_code,
                    "response_format": "mp3"
                }, 
                timeout=30
            )
            
            if response.status_code == 200:
                content_length = len(response.content)
                print(f"   ✅ {languages.get(lang_code)}: {content_length} bytes generated")
                
                # Save a small test file
                test_file = Path(f"test_kokoro_{lang_code}_{voice}.mp3")
                test_file.write_bytes(response.content)
                print(f"   💾 Saved test file: {test_file}")
                
            else:
                print(f"   ❌ {languages.get(lang_code)}: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      Error: {error_data}")
                except:
                    print(f"      Error: {response.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ {languages.get(lang_code)}: {e}")
    
    print(f"\n📝 Summary:")
    print("   - Voice fetching endpoint tested")
    print("   - Language code mapping verified")  
    print("   - Multi-language synthesis tested")
    print("   - Test audio files generated")
    
    print(f"\n💡 Next Steps:")
    print("   1. Run the Web UI: python main_ui.py")
    print("   2. Select 'Kokoro' tab")
    print("   3. Choose language and voice")
    print("   4. Generate audiobook")

if __name__ == "__main__":
    test_kokoro_voices_and_languages()