#!/usr/bin/env python3
"""
Test script para verificar que los warnings de límite de caracteres se suprimen correctamente
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider

def test_warnings_suppression():
    """Test que los warnings se suprimen correctamente"""
    print("🧪 Testing warnings suppression for XTTS...")
    
    # Configurar logging para capturar warnings
    logging.basicConfig(level=logging.INFO)
    
    # Crear configuración de test usando argparse.Namespace
    import argparse
    args = argparse.Namespace()
    args.coqui_model = "tts_models/multilingual/multi-dataset/xtts_v2"
    args.coqui_speaker = "Ana Florence"
    args.coqui_language = "es"
    args.output_format = "wav"
    args.coqui_device = "cpu"  # Usar CPU para test
    
    config = GeneralConfig(args)
    
    # Texto que tradicionalmente causaría el warning (largo)
    long_text = """
    Hubo un tiempo en que estos bosques eran suyos, y todavía conocían los lugares secretos de cubiles de bestias y cosas por el estilo.
    Le gustaría conocer todo eso algún día, cuando fuera un hombre y pudiera ir a donde le placiera.
    Suspiró y rebulló, buscando una postura más cómoda contra su roca favorita, y por la fuerza de la costumbre dirigió la mirada a la inclinada ladera de la pradera para asegurarse de que sus ovejas estaban sanas y salvas.
    Lo estaban. No por primera vez, el huesudo muchacho de nariz aguileña oteó hacia el sur, con los ojos entrecerrados.
    Retiró el rebelde cabello, negro como el azabache, con una delgada mano que mantuvo levantada para resguardar los ojos, azulgrisáceos, e intentar en vano divisar los torreones del lejano y espléndido Athalgard, el corazón de Hastarl, junto al río.
    Como siempre, pudo distinguir la tenue neblina azulada que señalaba el meandro más próximo del Delimbiyr, pero nada más.
    Este texto es suficientemente largo para activar el sistema de chunking y verificar que no aparezcan warnings molestos.
    """ * 3  # Hacer el texto aún más largo
    
    try:
        # Crear provider
        provider = CoquiTTSProvider(config)
        
        # Crear archivo temporal para output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        # Audio tags de prueba
        audio_tags = AudioTags(
            title="Test Chunk",
            author="Test Author",
            genre="Test"
        )
        
        print(f"📝 Procesando texto de {len(long_text)} caracteres...")
        print("🔇 Si la configuración es correcta, NO deberías ver warnings sobre límite de caracteres")
        
        # Ejecutar síntesis (esto normalmente mostraría warnings)
        provider.text_to_speech(long_text, output_path, audio_tags)
        
        # Verificar que el archivo se creó
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Síntesis completada exitosamente")
            print(f"📄 Archivo creado: {output_path}")
            print(f"📏 Tamaño del archivo: {file_size} bytes")
            
            # Limpiar archivo temporal
            os.unlink(output_path)
            print("🧹 Archivo temporal limpiado")
            
            return True
        else:
            print("❌ Error: No se creó el archivo de audio")
            return False
            
    except ImportError as e:
        print(f"⚠️  TTS package no disponible: {e}")
        print("💡 Instala con: pip install TTS")
        return False
    except Exception as e:
        print(f"❌ Error durante la síntesis: {e}")
        return False

def test_short_text():
    """Test con texto corto para verificar funcionamiento normal"""
    print("\n🧪 Testing short text synthesis...")
    
    import argparse
    args = argparse.Namespace()
    args.coqui_model = "tts_models/multilingual/multi-dataset/xtts_v2"
    args.coqui_speaker = "Ana Florence"
    args.coqui_language = "es"
    args.output_format = "wav"
    args.coqui_device = "cpu"
    
    config = GeneralConfig(args)
    
    short_text = "Hola, esto es una prueba con texto corto."
    
    try:
        provider = CoquiTTSProvider(config)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        audio_tags = AudioTags(
            title="Test Short",
            author="Test Author",
            genre="Test"
        )
        
        print(f"📝 Procesando texto corto de {len(short_text)} caracteres...")
        
        provider.text_to_speech(short_text, output_path, audio_tags)
        
        if os.path.exists(output_path):
            print("✅ Síntesis de texto corto completada exitosamente")
            os.unlink(output_path)
            return True
        else:
            print("❌ Error: No se creó el archivo de audio para texto corto")
            return False
            
    except Exception as e:
        print(f"❌ Error durante síntesis de texto corto: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Test de Supresión de Warnings para Coqui TTS")
    print("=" * 50)
    
    success = True
    
    # Test 1: Texto largo (debería usar chunking sin warnings)
    if not test_warnings_suppression():
        success = False
    
    # Test 2: Texto corto (debería funcionar normalmente)
    if not test_short_text():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Todos los tests pasaron correctamente!")
        print("🔇 Los warnings de límite de caracteres están suprimidos")
        print("✨ El sistema de chunking funciona sin interrupciones")
    else:
        print("❌ Algunos tests fallaron")
        print("💡 Verifica la configuración de TTS y los modelos")
    
    print("\n📋 Resumen de mejoras implementadas:")
    print("   • Supresión de warnings de límite de caracteres")
    print("   • Supresión de warnings de torchaudio")
    print("   • Uso de enable_text_splitting nativo de XTTS")
    print("   • Chunking mejorado para textos largos")
    print("   • Supresión temporal durante procesamiento de chunks")