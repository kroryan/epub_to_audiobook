# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('piper_tts\\piper.exe', 'piper_tts'), ('piper_tts\\espeak-ng-data', 'piper_tts\\espeak-ng-data'), ('third_party\\ffmpeg', 'third_party\\ffmpeg'), ('examples', 'examples'), ('audiobook_generator\\ui', 'aud_gen_ui'), ('C:\\Users\\adryl\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\gradio_client\\types.json', 'gradio_client')]
datas += collect_data_files('gradio')
datas += collect_data_files('gradio_client')


a = Analysis(
    ['tray_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['gradio', 'gradio_client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'triton', 'xformers', 'pytorch_lightning', 'expecttest', 'tensorflow', 'tensorflow_intel', 'tensorflow_probability', 'tf_keras', 'jax', 'jaxlib', 'deepspeed', 'accelerate', 'transformers', 'optimum', 'bitsandbytes', 'auto_gptq', 'flash_attn', 'onnx', 'onnxruntime', 'scipy', 'sklearn', 'numba', 'llvmlite', 'matplotlib', 'pandas', 'pyarrow', 'numexpr', 'sympy', 'cv2', 'librosa', 'sounddevice', 'pyaudio', 'opencv_python', 'spacy', 'thinc', 'nltk', 'jieba', 'datasets', 'xgboost', 'lightgbm', 'gevent', 'zope', 'boto3', 'botocore', 'google.cloud', 'grpc', 'opentelemetry', 'notebook', 'ipykernel', 'pytest', 'hypothesis', 'pygame'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EpubToAudiobook',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EpubToAudiobook',
)
