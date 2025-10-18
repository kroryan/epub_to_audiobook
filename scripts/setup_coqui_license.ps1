# Script para aceptar licencia Coqui TTS automáticamente
# Ejecutar este script si aparecen prompts de licencia

Write-Host "🤝 CONFIGURANDO LICENCIA COQUI TTS AUTOMÁTICA" -ForegroundColor Green
Write-Host "=" * 55

Write-Host "`n📋 Información de Licencia:" -ForegroundColor Cyan
Write-Host "Coqui TTS tiene dos tipos de licencia:"
Write-Host "1. 🏢 Comercial: Requiere compra de licencia"
Write-Host "2. 🎓 No Comercial (CPML): Gratuita para uso personal/educativo"
Write-Host ""
Write-Host "Este script configura la licencia NO COMERCIAL automáticamente." -ForegroundColor Yellow
Write-Host ""

# Configurar variables de entorno para aceptar licencia
Write-Host "🔧 Configurando variables de entorno..." -ForegroundColor Yellow

$env:COQUI_TOS = "AGREED"
$env:TTS_AGREE_LICENSE = "yes"
$env:COQUI_AGREE_LICENSE = "1"

# Configurar para persistir en el sistema (opcional)
$response = Read-Host "¿Configurar licencia permanentemente en este PC? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    try {
        [Environment]::SetEnvironmentVariable("COQUI_TOS", "AGREED", "User")
        [Environment]::SetEnvironmentVariable("TTS_AGREE_LICENSE", "yes", "User")
        [Environment]::SetEnvironmentVariable("COQUI_AGREE_LICENSE", "1", "User")
        Write-Host "✅ Variables configuradas permanentemente" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Error configurando variables permanentes: $_" -ForegroundColor Yellow
    }
}

# Crear archivos de licencia en cache TTS
Write-Host "`n📁 Creando archivos de licencia en cache..." -ForegroundColor Yellow

$ttsCache = "$env:USERPROFILE\.cache\tts"
if (-not (Test-Path $ttsCache)) {
    New-Item -ItemType Directory -Path $ttsCache -Force | Out-Null
}

# Crear archivo de aceptación de licencia
$licenseFile = Join-Path $ttsCache ".tos_agreed"
New-Item -ItemType File -Path $licenseFile -Force | Out-Null
Write-Host "✅ Archivo de licencia creado: $licenseFile" -ForegroundColor Green

# Buscar directorios de modelos existentes
$modelDirs = Get-ChildItem -Path $ttsCache -Directory -Filter "*xtts*" -ErrorAction SilentlyContinue
foreach ($dir in $modelDirs) {
    $modelLicenseFile = Join-Path $dir.FullName ".tos_agreed"
    New-Item -ItemType File -Path $modelLicenseFile -Force | Out-Null
    Write-Host "✅ Licencia configurada para modelo: $($dir.Name)" -ForegroundColor Green
}

# Verificar configuración
Write-Host "`n🧪 Verificando configuración..." -ForegroundColor Yellow

Write-Host "Variables de entorno:"
Write-Host "  COQUI_TOS: $env:COQUI_TOS"
Write-Host "  TTS_AGREE_LICENSE: $env:TTS_AGREE_LICENSE"
Write-Host "  COQUI_AGREE_LICENSE: $env:COQUI_AGREE_LICENSE"

Write-Host "`nArchivos de licencia:"
if (Test-Path $licenseFile) {
    Write-Host "  ✅ $licenseFile" -ForegroundColor Green
} else {
    Write-Host "  ❌ $licenseFile" -ForegroundColor Red
}

# Test de TTS sin prompts
Write-Host "`n🔬 Probando TTS sin prompts interactivos..." -ForegroundColor Yellow

try {
    $testResult = python -c "
import os
os.environ['COQUI_TOS'] = 'AGREED'
os.environ['TTS_AGREE_LICENSE'] = 'yes'
os.environ['COQUI_AGREE_LICENSE'] = '1'

try:
    from TTS.api import TTS
    print('✅ TTS importado sin prompts')
    
    # Test rápido de modelos disponibles
    models = TTS().list_models()
    if 'tts_models/multilingual/multi-dataset/xtts_v2' in models:
        print('✅ Modelo XTTS-v2 disponible')
    else:
        print('⚠️ Modelo XTTS-v2 no encontrado en lista')
        
except Exception as e:
    if 'EOF when reading a line' in str(e):
        print('❌ Aún aparecen prompts interactivos')
        print('💡 Puede requerir reinicio de terminal/aplicación')
    else:
        print(f'⚠️ Error: {e}')
        print('💡 Esto puede ser normal si no hay conexión o es la primera vez')
"

    Write-Host $testResult
} catch {
    Write-Host "⚠️ Error en test: $_" -ForegroundColor Yellow
    Write-Host "💡 Esto puede ser normal en algunos entornos" -ForegroundColor Gray
}

Write-Host "`n✅ CONFIGURACIÓN DE LICENCIA COMPLETADA" -ForegroundColor Green
Write-Host ""
Write-Host "📋 TÉRMINOS DE LICENCIA NO COMERCIAL COQUI:" -ForegroundColor Cyan
Write-Host "- ✅ Uso personal y educativo permitido"
Write-Host "- ✅ Investigación académica permitida"
Write-Host "- ❌ Uso comercial NO permitido sin licencia"
Write-Host "- 📄 Licencia completa: https://coqui.ai/cpml"
Write-Host ""
Write-Host "🚀 PRÓXIMOS PASOS:" -ForegroundColor Blue
Write-Host "1. Reinicia la aplicación para aplicar cambios"
Write-Host "2. Los prompts de licencia ya no deberían aparecer"
Write-Host "3. Si persisten, contacta soporte técnico"
Write-Host ""

Read-Host "Presiona Enter para continuar..."