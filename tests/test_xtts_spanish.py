#!/usr/bin/env python3
"""
Test script para probar XTTS-v2 con español directamente
"""
import os
import sys
import tempfile
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_xtts_spanish():
    """Prueba XTTS-v2 con texto en español"""
    try:
        print("🎯 Probando XTTS-v2 con español...")
        
        # Importar TTS
        from TTS.api import TTS
        
        # Crear modelo XTTS-v2
        print("📥 Cargando modelo XTTS-v2...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        
        # Verificar que es multilingüe
        print(f"✅ Modelo multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Modelo multispeaker: {tts.is_multi_speaker}")
        
        # Mostrar idiomas soportados
        if tts.is_multi_lingual:
            print(f"🌍 Idiomas soportados: {tts.languages}")
            
            # Verificar que español está incluido
            if 'es' in tts.languages:
                print("✅ ¡Español confirmado en los idiomas soportados!")
            else:
                print("❌ Español no encontrado en idiomas soportados")
                return False
        
        # Mostrar voces disponibles
        if tts.is_multi_speaker:
            print(f"🎤 Voces disponibles: {len(tts.speakers)} voces")
            print(f"🎤 Primeras 5 voces: {tts.speakers[:5] if tts.speakers else 'Ninguna'}")
        
        # Texto de prueba en español
        texto_español = "Hola, este es un test de síntesis de voz en español usando XTTS-v2. ¿Funciona correctamente?"
        
        # Archivo de salida temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        print("🗣️ Generando audio en español...")
        
        # Parámetros para XTTS-v2 en español
        synthesis_params = {
            "text": texto_español,
            "file_path": output_file,
            "language": "es",  # ¡Importante: especificar idioma!
        }
        
        # Si hay voces disponibles, usar una
        if tts.is_multi_speaker and tts.speakers:
            # Usar una voz que suene bien para español
            spanish_voices = ["Ana Florence", "Sofia Hellen", "Gracie Wise"]
            selected_voice = None
            
            for voice in spanish_voices:
                if voice in tts.speakers:
                    selected_voice = voice
                    break
            
            if not selected_voice and tts.speakers:
                selected_voice = tts.speakers[0]  # Usar la primera voz disponible
            
            if selected_voice:
                synthesis_params["speaker"] = selected_voice
                print(f"🎤 Usando voz: {selected_voice}")
        
        # Generar el audio
        tts.tts_to_file(**synthesis_params)
        
        # Verificar que el archivo se creó
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Audio generado exitosamente: {output_file}")
            print(f"📁 Tamaño del archivo: {file_size} bytes")
            
            # Limpiar archivo temporal
            os.unlink(output_file)
            return True
        else:
            print("❌ No se pudo generar el archivo de audio")
            return False
            
    except Exception as e:
        print(f"❌ Error probando XTTS-v2: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_css10_spanish():
    """Prueba modelo CSS10 español como alternativa"""
    try:
        print("\n🎯 Probando modelo CSS10 español...")
        
        from TTS.api import TTS
        
        # Crear modelo CSS10 español
        print("📥 Cargando modelo CSS10 español...")
        tts = TTS("tts_models/es/css10/vits", gpu=False)
        
        print(f"✅ Modelo multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Modelo multispeaker: {tts.is_multi_speaker}")
        
        # Texto de prueba
        texto = "Esta es una prueba del modelo CSS10 en español."
        
        # Archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        print("🗣️ Generando audio con CSS10...")
        
        # Generar audio (CSS10 no necesita parámetros de idioma)
        tts.tts_to_file(text=texto, file_path=output_file)
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ CSS10 generado exitosamente: {file_size} bytes")
            os.unlink(output_file)
            return True
        else:
            print("❌ CSS10 falló")
            return False
            
    except Exception as e:
        print(f"❌ Error con CSS10: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 Test de modelos TTS en español\n")
    
    # Probar XTTS-v2
    xtts_ok = test_xtts_spanish()
    
    # Probar CSS10 como respaldo
    css10_ok = test_css10_spanish()
    
    print(f"\n📊 Resultados:")
    print(f"   XTTS-v2: {'✅ OK' if xtts_ok else '❌ FAIL'}")
    print(f"   CSS10:   {'✅ OK' if css10_ok else '❌ FAIL'}")
    
    if xtts_ok:
        print("\n🎉 ¡XTTS-v2 funciona correctamente en español!")
        print("💡 El problema está en la configuración de la aplicación, no en las dependencias.")
    elif css10_ok:
        print("\n⚠️ XTTS-v2 tiene problemas, pero CSS10 funciona.")
        print("💡 Usar CSS10 como alternativa hasta resolver XTTS-v2.")
    else:
        print("\n❌ Ambos modelos tienen problemas.")

if __name__ == "__main__":
    main()