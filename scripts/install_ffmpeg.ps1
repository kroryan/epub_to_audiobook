# Downloads and installs FFmpeg and FFprobe into third_party/ffmpeg/bin for local use
param(
    [string]$DestinationRoot = "third_party/ffmpeg"
)

$ErrorActionPreference = "Stop"

# Resolve paths
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$DestDir = Join-Path $ProjectRoot $DestinationRoot
$BinDir = Join-Path $DestDir "bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$ffmpegPath = Join-Path $BinDir "ffmpeg.exe"
$ffprobePath = Join-Path $BinDir "ffprobe.exe"
if (Test-Path $ffmpegPath -PathType Leaf -and Test-Path $ffprobePath -PathType Leaf) {
    Write-Host "FFmpeg already present at $BinDir. Skipping download."
    return
}

$zipUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$tmpZip = Join-Path $env:TEMP "ffmpeg.zip"

Write-Host "Downloading FFmpeg from $zipUrl ..."
Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip

# Extract
$extractDir = Join-Path $env:TEMP "ffmpeg_extract_$(Get-Random)"
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
Expand-Archive -Path $tmpZip -DestinationPath $extractDir -Force

# Find ffmpeg.exe and ffprobe.exe
$ffmpegExe = Get-ChildItem -Path $extractDir -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$ffprobeExe = Get-ChildItem -Path $extractDir -Recurse -Filter ffprobe.exe | Select-Object -First 1

if (-not $ffmpegExe -or -not $ffprobeExe) {
    Write-Error "Could not locate ffmpeg.exe/ffprobe.exe inside archive."
    exit 1
}

Copy-Item -Force $ffmpegExe.FullName (Join-Path $BinDir "ffmpeg.exe")
Copy-Item -Force $ffprobeExe.FullName (Join-Path $BinDir "ffprobe.exe")

# Cleanup
Remove-Item -Force $tmpZip
Remove-Item -Recurse -Force $extractDir

Write-Host "Installed FFmpeg to $BinDir"
