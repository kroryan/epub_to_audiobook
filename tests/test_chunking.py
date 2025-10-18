#!/usr/bin/env python3
"""
Test script to verify that chunking methods are available in CoquiTTSProvider
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider
from audiobook_generator.config.general_config import GeneralConfig

def test_chunking_methods():
    """Test that chunking methods are available in the class"""
    
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
    
    # Test that methods exist
    assert hasattr(provider, '_synthesize_xtts_chunks'), "Missing _synthesize_xtts_chunks method"
    assert hasattr(provider, '_split_text_for_xtts'), "Missing _split_text_for_xtts method"
    assert hasattr(provider, '_split_long_sentence'), "Missing _split_long_sentence method"
    
    print("✅ All chunking methods are available!")
    
    # Test text splitting
    test_text = "Esta es una prueba muy larga que debería ser dividida en chunks más pequeños para XTTS. El sistema debe respetar los límites de caracteres y mantener la coherencia de las oraciones. Esto es importante para la calidad del audio generado."
    
    chunks = provider._split_text_for_xtts(test_text, 100)
    print(f"✅ Text split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1} ({len(chunk)} chars): {chunk[:50]}...")
    
    print("✅ Chunking test completed successfully!")

if __name__ == "__main__":
    test_chunking_methods()