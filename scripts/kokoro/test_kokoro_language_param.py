#!/usr/bin/env python3
"""
Test script to verify Kokoro language parameter support
"""

import requests
import os
from openai import OpenAI

def test_kokoro_language_parameter():
    """Test if Kokoro accepts the language parameter"""
    
    print("🧪 Testing Kokoro Language Parameter Support")
    print("=" * 50)
    
    # Test 1: Direct requests to Kokoro
    print("\n1. 🌐 Testing with direct HTTP requests:")
    
    test_cases = [
        {"with_language": True, "language": "e", "text": "Hola mundo en español"},
        {"with_language": False, "language": None, "text": "Hello world in English"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n   Test {i}: {'With' if case['with_language'] else 'Without'} language parameter")
        
        payload = {
            "model": "kokoro",
            "voice": "af_bella",
            "input": case["text"],
            "response_format": "mp3"
        }
        
        if case["with_language"]:
            payload["language"] = case["language"]
        
        try:
            response = requests.post(
                "http://localhost:8880/v1/audio/speech", 
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"   ✅ Success: {len(response.content)} bytes")
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      Error: {error_data}")
                except:
                    print(f"      Error: {response.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test 2: OpenAI SDK with Kokoro
    print(f"\n2. 🔧 Testing with OpenAI SDK:")
    
    # Set up environment
    os.environ['OPENAI_BASE_URL'] = 'http://localhost:8880/v1'
    os.environ['OPENAI_API_KEY'] = 'fake-key'
    
    client = OpenAI(
        base_url="http://localhost:8880/v1",
        api_key="fake-key"
    )
    
    sdk_test_cases = [
        {"with_language": True, "language": "e", "text": "Prueba con SDK"},
        {"with_language": False, "language": None, "text": "Test with SDK"},
    ]
    
    for i, case in enumerate(sdk_test_cases, 1):
        print(f"\n   SDK Test {i}: {'With' if case['with_language'] else 'Without'} language parameter")
        
        try:
            kwargs = {
                "model": "kokoro",
                "voice": "af_bella",
                "input": case["text"],
                "response_format": "mp3"
            }
            
            if case["with_language"]:
                kwargs["language"] = case["language"]
            
            response = client.audio.speech.create(**kwargs)
            
            if hasattr(response, 'content') and response.content:
                print(f"   ✅ Success: {len(response.content)} bytes")
            else:
                print(f"   ❓ Response received but no content attribute")
                
        except TypeError as e:
            if "language" in str(e):
                print(f"   ❌ Language parameter not supported by SDK: {e}")
            else:
                print(f"   ❌ SDK TypeError: {e}")
        except Exception as e:
            print(f"   ❌ SDK Exception: {e}")
    
    # Test 3: Check OpenAI SDK version
    print(f"\n3. 📦 Checking OpenAI SDK version:")
    try:
        import openai
        print(f"   OpenAI SDK version: {openai.__version__}")
        
        # Check if speech.create supports language parameter
        import inspect
        create_signature = inspect.signature(client.audio.speech.create)
        params = list(create_signature.parameters.keys())
        
        print(f"   Supported parameters: {params}")
        
        if 'language' in params:
            print("   ✅ Language parameter is supported by SDK")
        else:
            print("   ❌ Language parameter is NOT supported by SDK")
            
    except Exception as e:
        print(f"   ❌ Error checking SDK: {e}")
    
    # Test 4: Check Kokoro API documentation
    print(f"\n4. 📚 Testing Kokoro endpoint capabilities:")
    
    try:
        # Try to get API schema or documentation
        endpoints_to_try = [
            "http://localhost:8880/openapi.json",
            "http://localhost:8880/docs",
            "http://localhost:8880/v1/models"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint}: {response.status_code}")
                    if 'json' in response.headers.get('content-type', ''):
                        data = response.json()
                        if 'language' in str(data).lower():
                            print("      → Contains 'language' references")
                else:
                    print(f"   ❌ {endpoint}: {response.status_code}")
            except:
                print(f"   ❌ {endpoint}: Failed to connect")
                
    except Exception as e:
        print(f"   ❌ Error checking endpoints: {e}")
    
    print(f"\n📋 Recommendations:")
    print("   • If direct HTTP requests with 'language' work but SDK fails:")
    print("     → Use requests instead of OpenAI SDK for Kokoro")
    print("   • If both fail:")
    print("     → Kokoro may not support language parameter")
    print("   • If SDK version is old:")
    print("     → Consider upgrading: pip install openai --upgrade")

if __name__ == "__main__":
    test_kokoro_language_parameter()