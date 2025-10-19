#!/usr/bin/env python3
"""
Test voice mixing functionality directly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from audiobook_generator.tts_providers.kokoro_tts_provider import KokoroTTSProvider
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags

def test_voice_mixing():
    """Test voice mixing with KokoroTTSProvider"""
    
    print("🧪 Testing voice mixing functionality...")
    
    # Create config
    config = GeneralConfig(None)
    config.kokoro_base_url = "http://localhost:8880"
    config.output_format = "mp3"
    config.language = "e"  # Spanish
    config.model_name = "kokoro"
    config.speed = 1.0
    
    # Test with single voice
    print("\n1️⃣ Testing single voice...")
    config.voice_name = "af_bella"
    provider = KokoroTTSProvider(config)
    
    # Test with voice combination  
    print("\n2️⃣ Testing voice combination...")
    config.voice_name = "af_bella+af_sky(0.3)"
    provider = KokoroTTSProvider(config)
    
    # Create test output
    test_text = "Hola, esto es una prueba del mixer de voces."
    output_file = "test_voice_mix.mp3"
    
    try:
        # Create audio tags
        audio_tags = AudioTags(
            title="Voice Mix Test",
            author="Test Author", 
            book_title="Voice Mix Test",
            idx=1
        )
        
        print(f"📝 Generating audio with voice: {config.voice_name}")
        provider.text_to_speech(test_text, output_file, audio_tags)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ Audio generated successfully: {output_file} ({size} bytes)")
            
            # Clean up
            os.remove(output_file)
            return True
        else:
            print("❌ Audio file not generated")
            return False
            
    except Exception as e:
        print(f"❌ Error generating audio: {e}")
        return False

if __name__ == "__main__":
    success = test_voice_mixing()
    if success:
        print("\n🎉 Voice mixing test PASSED!")
    else:
        print("\n💥 Voice mixing test FAILED!")
    
    exit(0 if success else 1)