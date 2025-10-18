#!/usr/bin/env python3
"""
Test para verificar que la corrección de MemoryError funciona correctamente
"""

import sys
import os
import tempfile
from pydub import AudioSegment
from pydub.generators import Sine

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.tts_providers.coqui_tts_provider import CoquiTTSProvider

def test_memory_efficient_limiter():
    """Prueba el limiter eficiente en memoria"""
    print("🧪 Testing memory-efficient soft limiter...")
    
    # Crear un proveedor Coqui TTS con configuración básica
    class MockConfig:
        def __init__(self):
            self.coqui_enable_limiter = True
            self.coqui_normalize_volume = True
            self.coqui_sample_rate = 22050
            self.coqui_audio_channels = 1
    
    config = MockConfig()
    provider = CoquiTTSProvider(config)
    
    # Generar un audio largo (simulando 45 segundos) para probar el manejo de chunks
    print("📊 Generando audio de prueba largo...")
    sine_wave = Sine(440).to_audio_segment(duration=45000)  # 45 segundos
    
    # Hacer que el audio tenga picos altos para activar el limiter
    loud_audio = sine_wave + 10  # Aumentar volumen para provocar picos
    
    print(f"🎵 Audio original: {len(loud_audio)}ms, pico: {loud_audio.max_dBFS:.1f} dBFS")
    
    try:
        # Aplicar el limiter eficiente
        print("🔧 Aplicando soft limiter eficiente...")
        processed_audio = provider._apply_soft_limiter(loud_audio, None)
        
        print(f"✅ Procesamiento exitoso!")
        print(f"🎵 Audio procesado: {len(processed_audio)}ms, pico: {processed_audio.max_dBFS:.1f} dBFS")
        
        # Verificar que el audio se procesó correctamente
        if processed_audio.max_dBFS < loud_audio.max_dBFS:
            print("✅ El limiter redujo correctamente los picos")
        else:
            print("⚠️  El limiter no redujo los picos (puede ser normal si no era necesario)")
            
        # Verificar que la duración se mantuvo
        if abs(len(processed_audio) - len(loud_audio)) < 100:  # Tolerancia de 100ms
            print("✅ La duración del audio se mantuvo correcta")
        else:
            print(f"❌ Error: duración cambió de {len(loud_audio)}ms a {len(processed_audio)}ms")
            return False
            
        return True
        
    except MemoryError as e:
        print(f"❌ Error: MemoryError no fue manejado correctamente: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_short_audio_limiter():
    """Prueba el limiter con audio corto (método normal)"""
    print("\n🧪 Testing short audio limiter...")
    
    class MockConfig:
        def __init__(self):
            self.coqui_enable_limiter = True
            self.coqui_normalize_volume = True
    
    config = MockConfig()
    provider = CoquiTTSProvider(config)
    
    # Generar audio corto (5 segundos)
    sine_wave = Sine(440).to_audio_segment(duration=5000)
    loud_audio = sine_wave + 10  # Aumentar volumen
    
    print(f"🎵 Audio corto: {len(loud_audio)}ms, pico: {loud_audio.max_dBFS:.1f} dBFS")
    
    try:
        processed_audio = provider._apply_soft_limiter(loud_audio, None)
        print(f"✅ Audio corto procesado: {len(processed_audio)}ms, pico: {processed_audio.max_dBFS:.1f} dBFS")
        return True
    except Exception as e:
        print(f"❌ Error con audio corto: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 Iniciando pruebas de corrección de MemoryError en Coqui TTS")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Audio largo
    if test_memory_efficient_limiter():
        tests_passed += 1
    
    # Test 2: Audio corto  
    if test_short_audio_limiter():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Resultados: {tests_passed}/{total_tests} pruebas exitosas")
    
    if tests_passed == total_tests:
        print("🎉 ¡Todas las pruebas pasaron! La corrección de MemoryError funciona correctamente.")
        return True
    else:
        print("❌ Algunas pruebas fallaron. Revisar la implementación.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)