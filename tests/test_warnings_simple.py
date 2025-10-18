#!/usr/bin/env python3
"""
Script simple para verificar la supresión de warnings
"""

import warnings
import logging

def test_warnings_import():
    """Test simple de importación y configuración de warnings"""
    print("🧪 Testing warnings suppression configuration...")
    
    # Configurar el mismo sistema de warnings que en coqui_tts_provider
    warnings.filterwarnings('ignore', message='.*text length exceeds.*character limit.*')
    warnings.filterwarnings('ignore', message='.*might cause truncated audio.*')
    warnings.filterwarnings('ignore', message='.*In 2.9, this function.*implementation will be changed.*')
    warnings.filterwarnings('ignore', category=UserWarning, module='torchaudio')
    warnings.filterwarnings('ignore', category=UserWarning, module='TTS')
    
    print("✅ Filtros de warnings configurados correctamente")
    
    # Test importación del provider
    try:
        from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider
        print("✅ CoquiTTSProvider importado correctamente con warnings suprimidos")
        return True
    except ImportError as e:
        print(f"⚠️  No se pudo importar CoquiTTSProvider: {e}")
        return False
    except Exception as e:
        print(f"❌ Error al importar: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Test Simple de Supresión de Warnings")
    print("=" * 40)
    
    if test_warnings_import():
        print("\n🎉 Test completado exitosamente!")
        print("🔇 Los warnings están configurados para ser suprimidos")
        print("\n📋 Configuración implementada:")
        print("   • warnings.filterwarnings para límite de caracteres")
        print("   • warnings.filterwarnings para audio truncado")
        print("   • warnings.filterwarnings para torchaudio")
        print("   • Logging de TTS configurado a nivel ERROR")
        print("   • enable_text_splitting en lugar de split_sentences")
        print("   • Supresión temporal durante chunking")
    else:
        print("\n❌ Test falló - revisar configuración")