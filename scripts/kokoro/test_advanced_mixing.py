#!/usr/bin/env python3
"""
Test advanced voice mixing with multiple voices
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from audiobook_generator.tts_providers.kokoro_tts_provider import KokoroTTSProvider
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags

def test_multiple_voice_combinations():
    """Test multiple voice combinations"""
    
    print("🧪 Testing multiple voice combinations...")
    
    # Test configurations
    test_combinations = [
        "af_bella",  # Single voice (baseline)
        "af_bella+af_sky(0.5)",  # Two voices
        "af_bella+af_sky(0.5)+bf_emma(0.3)",  # Three voices
        "em_santa(0.7)+ef_dorarem_alex(0.6)+em_alex(0.4)+ef_nicoletta(0.3)",  # Four Spanish voices
        "am_adam(0.8)+bm_lewis(0.6)+am_daniel(0.4)"  # Three male voices
    ]
    
    test_text = "Esta es una prueba de mezcla avanzada de voces con múltiples combinaciones."
    
    for i, combination in enumerate(test_combinations, 1):
        print(f"\n{i}️⃣ Testing combination: {combination}")
        
        # Create config
        config = GeneralConfig(None)
        config.kokoro_base_url = "http://localhost:8880"
        config.output_format = "mp3"
        config.language = "e"  # Spanish
        config.model_name = "kokoro"
        config.speed = 1.0
        config.voice_name = combination
        
        try:
            provider = KokoroTTSProvider(config)
            
            # Create audio tags
            audio_tags = AudioTags(
                title=f"Voice Test {i}",
                author="Advanced Mixer Test", 
                book_title=f"Combination Test {i}",
                idx=i
            )
            
            output_file = f"test_combination_{i}.mp3"
            
            print(f"📝 Generating audio with combination: {combination}")
            provider.text_to_speech(test_text, output_file, audio_tags)
            
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"✅ Audio generated: {output_file} ({size} bytes)")
                
                # Keep the file for comparison (don't delete)
            else:
                print(f"❌ Audio file not generated")
                return False
                
        except Exception as e:
            print(f"❌ Error with combination '{combination}': {e}")
            return False
    
    print(f"\n🎉 All voice combination tests completed!")
    print(f"📁 Check the generated files to hear the differences:")
    for i in range(1, len(test_combinations) + 1):
        filename = f"test_combination_{i}.mp3"
        if os.path.exists(filename):
            print(f"   - {filename}")
    
    return True

if __name__ == "__main__":
    success = test_multiple_voice_combinations()
    if success:
        print("\n🎊 ADVANCED VOICE MIXING TEST PASSED!")
        print("🔊 Reproduce los archivos generados para escuchar las diferencias entre combinaciones")
    else:
        print("\n💥 Advanced voice mixing test FAILED!")
    
    exit(0 if success else 1)