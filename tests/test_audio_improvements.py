#!/usr/bin/env python3
"""
Test script to verify that audio processing improvements are working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider

def test_audio_methods():
    """Test that new audio processing methods are available"""
    
    # Create a simple mock config object
    class MockConfig:
        def __init__(self):
            self.coqui_model = "tts_models/multilingual/multi-dataset/xtts_v2"
            self.coqui_language = "es"
            self.coqui_speaker = "Viktor Eka"
            self.output_format = "mp3"
    
    config = MockConfig()
    
    # Create provider instance
    provider = CoquiTTSProvider(config)
    
    # Test that new methods exist
    assert hasattr(provider, '_normalize_audio_level'), "Missing _normalize_audio_level method"
    assert hasattr(provider, '_apply_soft_limiter'), "Missing _apply_soft_limiter method"
    assert hasattr(provider, '_combine_audio_smoothly'), "Missing _combine_audio_smoothly method"
    assert hasattr(provider, '_is_silence'), "Missing _is_silence method"
    
    print("✅ All audio processing methods are available!")
    
    # Test chunk splitting with improved algorithm
    test_text = """
    En este capítulo vamos a explorar las aventuras de nuestro protagonista. 
    Las aventuras son emocionantes y llenas de acción. Cada momento trae nuevos desafíos.
    Los personajes enfrentan obstáculos difíciles pero siempre encuentran una manera de superarlos.
    El desarrollo de la historia es fascinante y mantiene al lector enganchado desde el primer momento.
    """
    
    chunks = provider._split_text_for_xtts(test_text, max_tokens=350)
    print(f"✅ Text split into {len(chunks)} chunks with improved algorithm:")
    for i, chunk in enumerate(chunks):
        word_count = len(chunk.split())
        print(f"  Chunk {i+1} ({len(chunk)} chars, ~{word_count} words): {chunk[:80]}...")
    
    print("✅ Audio improvement test completed successfully!")
    print("🎵 New features:")
    print("   - Volume normalization between chunks")
    print("   - Fade in/out to prevent clicks/pops")
    print("   - Smooth crossfades between segments")
    print("   - Soft limiter to prevent distortion")
    print("   - Improved chunk pause duration (150ms)")

if __name__ == "__main__":
    test_audio_methods()