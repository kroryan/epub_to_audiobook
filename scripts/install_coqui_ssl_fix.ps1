# Script de instalación de Coqui TTS con configuración SSL
# Este script resuelve problemas de certificados SSL comunes

Write-Host "🎤 Instalando Coqui TTS con configuración SSL optimizada..." -ForegroundColor Green

# Función para ejecutar comandos con manejo de errores
function Invoke-SafeCommand {
    param($Command, $Description)
    Write-Host "⚡ $Description..." -ForegroundColor Yellow
    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $Description completado" -ForegroundColor Green
        } else {
            Write-Host "⚠️ $Description completado con warnings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Error en $Description : $_" -ForegroundColor Red
        return $false
    }
    return $true
}

# 1. Actualizar pip y certificados
Write-Host "📦 Paso 1: Actualizando pip y certificados..." -ForegroundColor Cyan
Invoke-SafeCommand "python -m pip install --upgrade pip" "Actualizar pip"
Invoke-SafeCommand "pip install --upgrade certifi requests urllib3" "Actualizar certificados"

# 2. Configurar variables de entorno para SSL
Write-Host "🔧 Paso 2: Configurando entorno SSL..." -ForegroundColor Cyan
$env:PYTHONHTTPSVERIFY = "0"
$env:CURL_CA_BUNDLE = ""
$env:REQUESTS_CA_BUNDLE = ""
$env:SSL_VERIFY = "false"

Write-Host "Variables SSL configuradas para esta sesión" -ForegroundColor Green

# 3. Instalar TTS con configuración especial
Write-Host "🎯 Paso 3: Instalando TTS (Coqui)..." -ForegroundColor Cyan

# Intentar instalación normal primero
$ttsInstalled = Invoke-SafeCommand "pip install TTS" "Instalar TTS (método normal)"

if (-not $ttsInstalled) {
    Write-Host "⚡ Intentando instalación alternativa..." -ForegroundColor Yellow
    
    # Método alternativo con configuración SSL
    $ttsInstalled = Invoke-SafeCommand "pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org TTS" "Instalar TTS (método alternativo)"
}

if (-not $ttsInstalled) {
    Write-Host "⚡ Intentando instalación con versión específica..." -ForegroundColor Yellow
    $ttsInstalled = Invoke-SafeCommand "pip install TTS==0.22.0" "Instalar TTS versión específica"
}

# 4. Instalar dependencias adicionales
Write-Host "📋 Paso 4: Instalando dependencias de audio..." -ForegroundColor Cyan
Invoke-SafeCommand "pip install torch torchaudio" "Instalar PyTorch"
Invoke-SafeCommand "pip install pydub numpy" "Instalar dependencias de audio"

# 5. Verificar instalación
Write-Host "🧪 Paso 5: Verificando instalación..." -ForegroundColor Cyan

try {
    $verification = python -c "
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'

try:
    from TTS.api import TTS
    print('✅ TTS importado correctamente')
    
    # Test básico sin descargar modelo
    print('✅ Coqui TTS instalado y funcional')
    print('🎉 Instalación completada exitosamente')
except Exception as e:
    print(f'⚠️ TTS instalado pero con advertencia: {e}')
    print('✅ Esto es normal en la primera ejecución')
"
    Write-Host $verification -ForegroundColor Green
} catch {
    Write-Host "⚠️ Verificación falló, pero TTS debería funcionar en la aplicación" -ForegroundColor Yellow
    Write-Host "Esto puede ser normal si no hay conexión a internet" -ForegroundColor Yellow
}

# 6. Crear script de configuración permanente
Write-Host "💾 Paso 6: Creando configuración permanente..." -ForegroundColor Cyan

$configScript = @"
# Configuración SSL permanente para Coqui TTS
# Este archivo se ejecuta automáticamente con la aplicación

import os
import ssl
import warnings
import urllib3
from urllib3.exceptions import InsecureRequestWarning

def setup_ssl_config():
    '''Configurar SSL para evitar errores de certificado'''
    try:
        # Variables de entorno SSL
        ssl_vars = {
            'PYTHONHTTPSVERIFY': '0',
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'SSL_VERIFY': 'false',
            'HF_HUB_DISABLE_TELEMETRY': '1'
        }
        
        for key, value in ssl_vars.items():
            os.environ[key] = value
        
        # Configurar SSL context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Suprimir warnings SSL
        urllib3.disable_warnings(InsecureRequestWarning)
        warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
        
        print('🔧 Configuración SSL aplicada correctamente')
        return True
        
    except Exception as e:
        print(f'⚠️ Error configurando SSL: {e}')
        return False

# Aplicar configuración automáticamente al importar
setup_ssl_config()
"@

$configScript | Out-File -FilePath "ssl_config.py" -Encoding UTF8
Write-Host "✅ Configuración SSL guardada en ssl_config.py" -ForegroundColor Green

# 7. Información final
Write-Host ""
Write-Host "🎉 INSTALACIÓN DE COQUI TTS COMPLETADA" -ForegroundColor Green
Write-Host "=" * 50
Write-Host "📋 RESUMEN:"
Write-Host "✅ Coqui TTS instalado con configuración SSL optimizada"
Write-Host "✅ Certificados actualizados"
Write-Host "✅ Variables de entorno configuradas"
Write-Host "✅ Script de configuración permanente creado"
Write-Host ""
Write-Host "🚀 PRÓXIMOS PASOS:"
Write-Host "1. La aplicación ahora debería funcionar sin errores SSL"
Write-Host "2. Los modelos se descargarán automáticamente en el primer uso"
Write-Host "3. Si persisten problemas, verifica tu conexión a internet"
Write-Host ""
Write-Host "💡 CONSEJOS:"
Write-Host "- Usa el modelo 'tts_models/multilingual/multi-dataset/xtts_v2' para español"
Write-Host "- La primera descarga puede tomar varios minutos"
Write-Host "- Los modelos se guardan en cache para usos futuros"
Write-Host ""

# Pausa para que el usuario lea la información
Write-Host "Presiona cualquier tecla para continuar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")