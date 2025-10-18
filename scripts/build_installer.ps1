# Build an installer-based distribution using PyInstaller onedir + Inno Setup (optional)
# 1) Install deps
# 2) Download (idempotent) FFmpeg and voice models
# 3) Build onedir app (faster startup, avoids onefile temp extraction issues)
# 4) Package with Inno Setup if ISCC is available; otherwise produce a ZIP

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

Write-Host "Installing Python dependencies..."
pip install -r requirements.txt
pip install pyinstaller

Write-Host "Cleaning previous build artifacts..."
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path .\dist\EpubToAudiobook) { Remove-Item .\dist\EpubToAudiobook -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path .\EpubToAudiobook.spec) { Remove-Item .\EpubToAudiobook.spec -Force -ErrorAction SilentlyContinue }

Write-Host "Checking FFmpeg..."
$ffmpegBin = Join-Path $ProjectRoot 'third_party\ffmpeg\bin'
$ffmpegExe = Join-Path $ffmpegBin 'ffmpeg.exe'
$ffprobeExe = Join-Path $ffmpegBin 'ffprobe.exe'
if ((Test-Path $ffmpegExe -PathType Leaf) -and (Test-Path $ffprobeExe -PathType Leaf)) {
  Write-Host "FFmpeg already present at $ffmpegBin."
} else {
  Write-Host "FFmpeg missing; invoking installer..."
  powershell -ExecutionPolicy Bypass -File .\scripts\install_ffmpeg.ps1
}

Write-Host "Checking Piper voice models..."
$voiceDir = Join-Path $ProjectRoot 'piper_tts\espeak-ng-data\voices'
$voices = @(
  'es_ES-davefx-medium.onnx',
  'es_ES-mls_10246-low.onnx',
  'en_US-lessac-medium.onnx',
  'en_US-amy-medium.onnx'
)
$missing = @()
foreach ($v in $voices) {
  if (-not (Test-Path (Join-Path $voiceDir $v) -PathType Leaf)) { $missing += $v }
}
if ($missing.Count -eq 0) {
  Write-Host "All Piper models present in $voiceDir."
} else {
  Write-Host ("Missing models: {0}" -f ($missing -join ', '))
  Write-Host "Downloading Piper voice models..."
  powershell -ExecutionPolicy Bypass -File .\scripts\download_piper_models.ps1
}

$Name = "EpubToAudiobook"
$Entry = "tray_app.py"
$DistDir = "dist"
$BuildDir = "build"

# Build onedir to avoid large single-file extraction and cython/cpyd decompression issues
# Find gradio_client path for types.json
$GradioClientPath = python -c "import gradio_client; import os; print(os.path.dirname(gradio_client.__file__))"
$GradioTypesJson = Join-Path $GradioClientPath "types.json"

$datas = @(
    "piper_tts\piper.exe;piper_tts",
    "piper_tts\espeak-ng-data;piper_tts\espeak-ng-data",
    "third_party\ffmpeg;third_party\ffmpeg",
    "examples;examples",
    "audiobook_generator\ui;aud_gen_ui"
)

# Add Gradio data files if they exist
if (Test-Path $GradioTypesJson -PathType Leaf) {
    $datas += "$GradioTypesJson;gradio_client"
    Write-Host "Adding Gradio types.json from $GradioTypesJson"
}
$dataArgs = @()
foreach ($d in $datas) { $dataArgs += @('--add-data', $d) }

Write-Host "Building onedir app..."
$excludes = @(
  # Big ML/GPU stacks
  'torch','torchvision','torchaudio','triton','xformers','pytorch_lightning','expecttest',
  'tensorflow','tensorflow_intel','tensorflow_probability','tf_keras','jax','jaxlib',
  'deepspeed','accelerate','transformers','optimum','bitsandbytes','auto_gptq','flash_attn',
  'onnx','onnxruntime',
  # Sci/Num stack not needed
  'scipy','sklearn','numba','llvmlite','matplotlib','pandas','pyarrow','numexpr','sympy',
  # Audio/Vision extras not used
  'cv2','librosa','sounddevice','pyaudio','opencv_python',
  # NLP/data libs pulled transitively by transformers
  'spacy','thinc','nltk','jieba','datasets',
  # Other heavy/optional
  'xgboost','lightgbm','gevent','zope','boto3','botocore','google.cloud','grpc','opentelemetry',
  'notebook','ipykernel','pytest','hypothesis','pygame'
)
$excludeArgs = @()
foreach ($e in $excludes) { $excludeArgs += @('--exclude-module', $e) }

pyinstaller `
  --name $Name `
  --noconsole `
  --onedir `
  --clean `
  --noconfirm `
  --distpath $DistDir `
  --workpath $BuildDir `
  --collect-data gradio `
  --collect-data gradio_client `
  --collect-data setuptools `
  --collect-data jaraco `
  --collect-data jaraco.text `
  --collect-data pkg_resources `
  --hidden-import gradio `
  --hidden-import gradio_client `
  --hidden-import setuptools `
  --hidden-import jaraco.text `
  --hidden-import pkg_resources `
  @excludeArgs `
  @dataArgs `
  $Entry

$AppDir = Join-Path $DistDir $Name
if (-not (Test-Path $AppDir)) { throw "Build output not found: $AppDir" }

# Try Inno Setup if installed
$Iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue)
if ($Iscc) {
  Write-Host "Packaging with Inno Setup..."
  $IssPath = Join-Path $PSScriptRoot "installer.iss"
  if (-not (Test-Path $IssPath)) {
    Write-Host "No installer.iss found; creating a minimal script..."
    $iss = @"
#define MyAppName "EpubToAudiobook"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Local"
#define MyAppExeName "EpubToAudiobook.exe"

[Setup]
AppId={{8F7B3948-9C55-4A4E-AF9D-2E7B5E7B7F01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=EpubToAudiobook-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source:"..\\dist\\EpubToAudiobook\\*"; DestDir:"{app}"; Flags: recursesubdirs

[Icons]
Name:"{group}\\EpubToAudiobook"; Filename:"{app}\\EpubToAudiobook.exe"
Name:"{commondesktop}\\EpubToAudiobook"; Filename:"{app}\\EpubToAudiobook.exe"; Tasks: desktopicon

[Tasks]
Name:"desktopicon"; Description:"Create a &desktop icon"; GroupDescription:"Additional icons:"; Flags: unchecked
"@
    Set-Content -Path $IssPath -Value $iss -Encoding UTF8
  }
  & iscc.exe $IssPath
} else {
  Write-Host "Inno Setup not found; creating a ZIP package instead..."
  $ZipPath = Join-Path $DistDir "EpubToAudiobook-portable.zip"
  if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue }

  # Create staging copy to avoid locking issues when zipping from build output
  $Staging = Join-Path $DistDir "EpubToAudiobook_pack"
  if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue }
  Write-Host "Preparing staging folder for ZIP..."
  Copy-Item -Path $AppDir -Destination $Staging -Recurse -Force

  # Use .NET ZipFile for reliability; retry to handle transient locks from AV/indexers
  Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
  $attempts = 0
  $maxAttempts = 3
  while ($attempts -lt $maxAttempts) {
    try {
      [System.IO.Compression.ZipFile]::CreateFromDirectory($Staging, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
      break
    } catch {
      $attempts++
      if ($attempts -ge $maxAttempts) {
        Write-Warning "Failed to create ZIP after $attempts attempts: $($_.Exception.Message)"
        throw
      } else {
        Write-Host "ZIP attempt $attempts failed: $($_.Exception.Message). Retrying in 2s..."
        Start-Sleep -Seconds 2
      }
    }
  }

  # Cleanup staging
  if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue }

  Write-Host "Portable ZIP created at $ZipPath"
}

Pop-Location
Write-Host "Installer build complete."