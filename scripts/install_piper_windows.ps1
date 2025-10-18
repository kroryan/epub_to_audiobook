# Script alternativo para instalar Piper TTS
# Usa descarga directa de binarios precompilados

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=== Instalador Piper TTS Alternativo ===" -ForegroundColor Green
Write-Host ""

$root = Split-Path -Parent $PSScriptRoot
$piperDir = Join-Path $root 'piper_tts'
$espeakDir = Join-Path $piperDir 'espeak-ng-data'
$voiceDir = Join-Path $espeakDir 'voices'

# URL correcto para Piper TTS
$piperUrl = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"

# Modelos de voz completos
$voiceModels = @(
    @{ 
        Name = 'es_ES-davefx-medium.onnx'
        Url = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx'
        Config = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json'
        Language = 'Espanol (Espana)'
        Quality = 'Media'
    },
    @{ 
        Name = 'es_ES-mls_10246-low.onnx'
        Url = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx'
        Config = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx.json'
        Language = 'Espanol (Espana)'
        Quality = 'Baja (rapida)'
    },
    @{ 
        Name = 'en_US-lessac-medium.onnx'
        Url = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx'
        Config = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json'
        Language = 'Ingles (Estados Unidos)'
        Quality = 'Media'
    },
    @{ 
        Name = 'en_US-amy-medium.onnx'
        Url = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx'
        Config = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json'
        Language = 'Ingles (Estados Unidos)'
        Quality = 'Media'
    },
    @{ 
        Name = 'es_ES-miro-high.onnx'
        Url = 'https://huggingface.co/csukuangfj/vits-piper-es_ES-miro-high/resolve/main/es_ES-miro-high.onnx'
        Config = 'https://huggingface.co/csukuangfj/vits-piper-es_ES-miro-high/resolve/main/es_ES-miro-high.onnx.json'
        Language = 'Espanol (Espana) - Miro'
        Quality = 'Alta'
    }
)

# Crear directorios
Write-Host "Creando directorios..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $piperDir | Out-Null
New-Item -ItemType Directory -Force -Path $espeakDir | Out-Null
New-Item -ItemType Directory -Force -Path $voiceDir | Out-Null

# Funcion para descargar
function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )
    
    try {
        Write-Host "  Probando: $Url"
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($Url, $Destination)
        $webClient.Dispose()
        return $true
    } catch {
        Write-Host "    FALLO: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Verificar si Piper ya existe
$piperExe = Join-Path $piperDir 'piper.exe'
if ((Test-Path $piperExe) -and -not $Force) {
    Write-Host "OK Piper TTS ya instalado" -ForegroundColor Green
} else {
    Write-Host "1. Intentando descargar Piper TTS..." -ForegroundColor Yellow
    
    $tempDir = Join-Path $env:TEMP "piper_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    
    $success = $false
    $archivePath = Join-Path $tempDir 'piper_windows_amd64.zip'
    
    if (Download-File -Url $piperUrl -Destination $archivePath) {
        Write-Host "  OK Descarga exitosa" -ForegroundColor Green
        
        try {
            Write-Host "  Extrayendo archivos ZIP..." -ForegroundColor Cyan
            
            # Usar Expand-Archive nativo de PowerShell
            Expand-Archive -Path $archivePath -DestinationPath $tempDir -Force
            
            # Buscar archivos extraidos
            $extractedFiles = Get-ChildItem -Path $tempDir -Recurse -File | Where-Object { $_.Name -eq 'piper.exe' }
            
            if ($extractedFiles.Count -gt 0) {
                $piperSource = $extractedFiles[0].DirectoryName
                Write-Host "  Copiando archivos de Piper..." -ForegroundColor Cyan
                
                # Copiar todos los archivos
                Copy-Item -Path "$piperSource\*" -Destination $piperDir -Recurse -Force
                
                Write-Host "  OK Piper TTS instalado correctamente" -ForegroundColor Green
                $success = $true
            } else {
                Write-Host "  ERROR: No se encontro piper.exe en el archivo" -ForegroundColor Red
            }
        } catch {
            Write-Host "  ERROR en extraccion: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  ERROR: No se pudo descargar el archivo" -ForegroundColor Red
    }
    
    if (-not $success) {
        Write-Host "ADVERTENCIA: No se pudo descargar Piper TTS automaticamente." -ForegroundColor Yellow
        Write-Host "Instrucciones manuales:" -ForegroundColor Yellow
        Write-Host "1. Ve a: https://github.com/rhasspy/piper/releases" -ForegroundColor Cyan
        Write-Host "2. Descarga el archivo para Windows" -ForegroundColor Cyan
        Write-Host "3. Extrae el contenido a: $piperDir" -ForegroundColor Cyan
    }
    
    # Limpiar directorio temporal
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""

# Descargar modelos (esto ya funciona bien)
Write-Host "2. Descargando modelos de voz..." -ForegroundColor Yellow

$successCount = 0
foreach ($model in $voiceModels) {
    $modelPath = Join-Path $voiceDir $model.Name
    $configPath = $modelPath + ".json"
    
    Write-Host ""
    Write-Host "Modelo: $($model.Name)" -ForegroundColor White
    Write-Host "Idioma: $($model.Language) | Calidad: $($model.Quality)"
    
    if ((Test-Path $modelPath) -and -not $Force) {
        Write-Host "OK Ya instalado" -ForegroundColor Green
        $successCount++
        continue
    }
    
    # Descargar modelo
    if (Download-File -Url $model.Url -Destination $modelPath) {
        $fileSize = (Get-Item $modelPath).Length / 1MB
        if ($fileSize -gt 1) {
            $sizeRounded = [math]::Round($fileSize, 1)
            Write-Host "OK Modelo descargado ($sizeRounded MB)" -ForegroundColor Green
            
            # Descargar configuracion
            if (Download-File -Url $model.Config -Destination $configPath) {
                Write-Host "OK Configuracion descargada" -ForegroundColor Green
            }
            $successCount++
        } else {
            Write-Warning "Archivo incompleto"
            Remove-Item $modelPath -Force -ErrorAction SilentlyContinue
        }
    }
}

# Resumen
Write-Host ""
Write-Host "=== RESUMEN ===" -ForegroundColor Green

if (Test-Path $piperExe) {
    Write-Host "OK Piper TTS: INSTALADO" -ForegroundColor Green
    
    try {
        $version = & $piperExe --version 2>$null
        Write-Host "  Version: $version"
    } catch {
        Write-Host "  Ejecutable disponible"
    }
} else {
    Write-Host "PENDIENTE Piper TTS: Instalacion manual requerida" -ForegroundColor Yellow
}

Write-Host "OK Modelos: $successCount/$($voiceModels.Count) instalados" -ForegroundColor Green

if (($successCount -gt 0) -and (Test-Path $piperExe)) {
    Write-Host ""
    Write-Host "EXITO Todo listo para usar!" -ForegroundColor Green
    Write-Host "Ejecuta: python main_ui.py" -ForegroundColor Cyan
} elseif ($successCount -gt 0) {
    Write-Host ""
    Write-Host "PARCIAL Modelos listos, falta Piper TTS" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "ERROR Instalacion fallida" -ForegroundColor Red
}

Write-Host ""