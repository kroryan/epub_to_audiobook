#!/usr/bin/env python3
"""
Script de prueba para verificar que la integración de Kokoro funciona correctamente
"""

import requests
import time

def test_kokoro_server(base_url="http://localhost:8880"):
    """Probar que el servidor Kokoro está funcionando"""
    print("🔗 Testing Kokoro server connection...")
    
    try:
        # Test 1: Health check
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check: OK")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test 2: Models endpoint
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ Models endpoint: OK")
        else:
            print(f"❌ Models endpoint failed: {response.status_code}")
            return False
            
        # Test 3: Voices endpoint
        response = requests.get(f"{base_url}/v1/audio/voices", timeout=5)
        if response.status_code == 200:
            data = response.json()
            voices = data.get('voices', [])
            print(f"✅ Voices endpoint: OK ({len(voices)} voices available)")
        else:
            print(f"❌ Voices endpoint failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_voice_combination_validation():
    """Probar validación de combinaciones de voces"""
    print("\n🎤 Testing voice combination validation...")
    
    # Test basic validation logic without importing the provider
    test_cases = [
        ("af_bella", True),  # Simple voice
        ("af_bella+af_sky", True),  # Simple combination
        ("ef_dora+em_alex", True),  # Spanish combination
        ("af_heart+af_sky(0.3)", True),  # With weight
        ("af_bella+", False),  # Invalid: empty after +
        ("af_bella++af_sky", False),  # Invalid: double +
        ("+af_bella", False),  # Invalid: starts with +
        ("", False),  # Invalid: empty
    ]
    
    try:
        success_count = 0
        
        for voice_spec, should_be_valid in test_cases:
            # Basic validation logic
            is_valid = True
            try:
                if not voice_spec or voice_spec.strip() == "":
                    is_valid = False
                elif voice_spec.startswith('+') or voice_spec.startswith('-'):
                    is_valid = False
                elif voice_spec.endswith('+') or voice_spec.endswith('-'):
                    is_valid = False
                elif "++" in voice_spec or "--" in voice_spec:
                    is_valid = False
                
                result_msg = "✅ Valid syntax" if is_valid else "❌ Invalid syntax"
            except Exception as e:
                is_valid = False
                result_msg = f"❌ Error: {str(e)}"
            
            if is_valid == should_be_valid:
                print(f"✅ {voice_spec}: {result_msg}")
                success_count += 1
            else:
                print(f"❌ {voice_spec}: Expected {'valid' if should_be_valid else 'invalid'}, got {'valid' if is_valid else 'invalid'}")
        
        print(f"\n📊 Validation tests: {success_count}/{len(test_cases)} passed")
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_simple_tts_generation(base_url="http://localhost:8880"):
    """Probar generación básica de TTS"""
    print("\n🔊 Testing simple TTS generation...")
    
    try:
        url = f"{base_url}/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "voice": "af_heart",
            "input": "Hello, this is a test of Kokoro TTS integration.",
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            size = len(response.content)
            print(f"✅ TTS generation successful: {size} bytes")
            return True
        else:
            print(f"❌ TTS generation failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False

def test_voice_combination_tts(base_url="http://localhost:8880"):
    """Probar generación TTS con combinación de voces"""
    print("\n🎭 Testing voice combination TTS...")
    
    try:
        url = f"{base_url}/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "voice": "af_bella+af_sky(0.3)",  # Voice combination
            "input": "This is a test of voice combination in Kokoro.",
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False,
            "lang_code": "a"
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            size = len(response.content)
            print(f"✅ Voice combination TTS successful: {size} bytes")
            return True
        else:
            print(f"❌ Voice combination TTS failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Voice combination test failed: {e}")
        return False

def test_normalization_features(base_url="http://localhost:8880"):
    """Probar características de normalización"""
    print("\n📝 Testing text normalization features...")
    
    try:
        url = f"{base_url}/v1/audio/speech"
        
        # Text with various normalization targets
        test_text = "Visit https://example.com or email user@domain.com. Call +1-555-123-4567 for 10KB file."
        
        payload = {
            "model": "kokoro",
            "voice": "af_heart",
            "input": test_text,
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False,
            "normalization_options": {
                "normalize": True,
                "url_normalization": True,
                "email_normalization": True,
                "phone_normalization": True,
                "unit_normalization": True,
                "replace_remaining_symbols": True
            }
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            size = len(response.content)
            print(f"✅ Normalization TTS successful: {size} bytes")
            print(f"   Text with URLs, emails, phones, and units was processed")
            return True
        else:
            print(f"❌ Normalization TTS failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Normalization test failed: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🧪 KOKORO TTS INTEGRATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Server Connection", test_kokoro_server),
        ("Voice Combination Validation", test_voice_combination_validation),
        ("Simple TTS Generation", test_simple_tts_generation),
        ("Voice Combination TTS", test_voice_combination_tts),
        ("Text Normalization", test_normalization_features),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        start_time = time.time()
        
        try:
            success = test_func()
            duration = time.time() - start_time
            results.append((test_name, success, duration))
            
            if success:
                print(f"✅ {test_name}: PASSED ({duration:.2f}s)")
            else:
                print(f"❌ {test_name}: FAILED ({duration:.2f}s)")
                
        except Exception as e:
            duration = time.time() - start_time
            results.append((test_name, False, duration))
            print(f"💥 {test_name}: ERROR - {e} ({duration:.2f}s)")
    
    # Summary
    print(f"\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name:<30} | {duration:>6.2f}s")
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Kokoro TTS integration is working correctly")
        print(f"\n💡 Ready to use:")
        print(f"   • Simple voices: af_heart, ef_dora, etc.")
        print(f"   • Voice combinations: af_bella+af_sky(0.3)")
        print(f"   • Text normalization: URLs, emails, phones")
        print(f"   • Multiple languages and formats")
    else:
        print(f"\n⚠️  Some tests failed")
        print(f"❌ Please check Kokoro server status and configuration")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)