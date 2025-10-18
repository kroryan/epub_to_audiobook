#!/usr/bin/env python3
"""
Test the updated chunking system for XTTS token limits
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider

def test_token_based_chunking():
    """Test that the new token-based chunking works correctly"""
    
    # Create a mock config
    class MockConfig:
        def __init__(self):
            self.coqui_model = "tts_models/multilingual/multi-dataset/xtts_v2"
            self.coqui_language = "es"
            self.coqui_speaker = "Viktor Eka"
            self.output_format = "mp3"
    
    config = MockConfig()
    provider = CoquiTTSProvider(config)
    
    # Test text that would cause the 400 token error
    long_text = """
    En la Torre Flotante, Elminster se encontró con una gran aventura. El terror ciego se apoderó de él
    cuando vio las criaturas mágicas que habitaban en los pasillos oscuros. Cada paso que daba resonaba
    en el silencio mortal que envolvía el lugar. Las paredes estaban cubiertas de runas antiguas que 
    brillaban con una luz azulada, creando sombras danzantes que parecían cobrar vida propia. El aire
    estaba cargado de magia elemental, tan denso que casi se podía cortar con una espada. Los hechizos
    de protección que había lanzado antes de entrar comenzaban a debilitarse, y podía sentir cómo las
    fuerzas oscuras intentaban penetrar sus defensas mágicas. A medida que avanzaba hacia el centro
    de la torre, los sonidos se volvían más extraños y amenazadores. Susurros en idiomas olvidados
    llenaban el aire, y ocasionalmente podía escuchar el eco de pasos que no eran los suyos.
    La aventura que había comenzado como una simple misión de reconocimiento se había convertido
    en una lucha por la supervivencia en un lugar donde la realidad misma parecía estar distorsionada
    por la antigua magia que impregnaba cada piedra de la construcción flotante.
    """ * 3  # Hacer el texto aún más largo
    
    print(f"🧪 Testing text of {len(long_text)} characters...")
    
    # Test chunking
    chunks = provider._split_text_for_xtts(long_text, max_tokens=350)
    
    print(f"✅ Successfully split into {len(chunks)} chunks")
    
    # Verify all chunks are within limits
    max_chunk_size = 0
    for i, chunk in enumerate(chunks):
        chunk_size = len(chunk)
        word_count = len(chunk.split())
        estimated_tokens = word_count * 1.3  # Rough estimation
        
        print(f"  Chunk {i+1}: {chunk_size} chars, ~{word_count} words, ~{estimated_tokens:.0f} tokens")
        
        if chunk_size > max_chunk_size:
            max_chunk_size = chunk_size
        
        # Check if chunk is within safe limits (should be ~1050 chars max)
        if chunk_size > 1200:
            print(f"⚠️  Warning: Chunk {i+1} might be too large ({chunk_size} chars)")
        
        # Preview chunk content
        preview = chunk[:100].replace('\n', ' ').strip()
        print(f"    Preview: {preview}...")
    
    print(f"\n📊 Max chunk size: {max_chunk_size} characters")
    
    # Test text reconstruction
    reconstructed = "\n\n".join(chunks)
    original_words = len(long_text.split())
    reconstructed_words = len(reconstructed.split())
    
    print(f"📝 Original text: {original_words} words")
    print(f"📝 Reconstructed: {reconstructed_words} words")
    
    if abs(original_words - reconstructed_words) <= 5:  # Allow small differences due to spacing
        print("✅ Text integrity maintained!")
    else:
        print("❌ Text integrity compromised!")
    
    return chunks

if __name__ == "__main__":
    test_token_based_chunking()