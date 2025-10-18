# Build a self-contained Windows .exe with PyInstaller
# 1) Install deps
# 2) Download embedded FFmpeg
# 3) Download Piper models
# 4) Bundle tray app into single EXE with all resources

$ErrorActionPreference = "Stop"

# Resolve project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

Write-Host "Installing Python dependencies..."
pip install -r requirements.txt
pip install pyinstaller

Write-Host "Cleaning previous build artifacts..."
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path .\dist\EpubToAudiobook.exe) { Remove-Item .\dist\EpubToAudiobook.exe -Force -ErrorAction SilentlyContinue }
if (Test-Path .\EpubToAudiobook.spec) { Remove-Item .\EpubToAudiobook.spec -Force -ErrorAction SilentlyContinue }

Write-Host "Checking FFmpeg..."
$ffmpegBin = Join-Path (Split-Path -Parent $PSScriptRoot) 'third_party\ffmpeg\bin'
$ffmpegExe = Join-Path $ffmpegBin 'ffmpeg.exe'
$ffprobeExe = Join-Path $ffmpegBin 'ffprobe.exe'
if (Test-Path $ffmpegExe -PathType Leaf -and Test-Path $ffprobeExe -PathType Leaf) {
    Write-Host "FFmpeg already present at $ffmpegBin."
} else {
    Write-Host "Downloading FFmpeg..."
    powershell -ExecutionPolicy Bypass -File .\scripts\install_ffmpeg.ps1
}

Write-Host "Checking Piper voice models..."
$voiceDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'piper_tts\espeak-ng-data\voices'
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

# Prepare PyInstaller options
$OneFile = $true
$Name = "EpubToAudiobook"
$Entry = "tray_app.py"
$DistDir = "dist"
$BuildDir = "build"

# Include non-Python resources
# - Piper executable and data
# - third_party/ffmpeg
# - logs dir
# - examples
# Use --add-data with src;dest format (Windows uses ; separator)

$datas = @(
    "piper_tts\piper.exe;piper_tts",
    "piper_tts\espeak-ng-data;piper_tts\espeak-ng-data",
    "third_party\ffmpeg;third_party\ffmpeg",
    "examples;examples",
    "audiobook_generator\ui;aud_gen_ui"
)

# Convert to arguments
$dataArgs = @()
foreach ($d in $datas) { $dataArgs += @('--add-data', $d) }

# Exclude heavy/unused modules to shrink build and avoid link errors
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

# Run PyInstaller
Write-Host "Building EXE..."
pyinstaller `
    --name $Name `
    --noconsole `
    --clean `
    --noconfirm `
    $(if ($OneFile) { "--onefile" }) `
    --distpath $DistDir `
    --workpath $BuildDir `
    --collect-data gradio `
    --collect-data gradio_client `
    --hidden-import gradio `
    --hidden-import gradio_client `
    @excludeArgs `
    @dataArgs `
    $Entry

Pop-Location

Write-Host "Build complete. See dist/$Name.exe"
