import logging
import shutil
import tempfile
import warnings
from pathlib import Path
from subprocess import run
import os

# Importar y aplicar configuración SSL automática
try:
    from audiobook_generator.utils.ssl_config import ssl_manager, auto_configure_ssl
    auto_configure_ssl()
    logger = logging.getLogger(__name__)
    logger.info("🔧 Sistema SSL automático activado para Coqui TTS")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Sistema SSL automático no disponible: {e}")
    
    # Fallback: configuración SSL básica
    try:
        import ssl
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib3.disable_warnings(InsecureRequestWarning)
        
        os.environ.update({
            'PYTHONHTTPSVERIFY': '0',
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'HF_HUB_DISABLE_TELEMETRY': '1'
        })
        
        logger.info("🔧 Configuración SSL básica aplicada")
    except Exception as fallback_error:
        logger.warning(f"No se pudo configurar SSL: {fallback_error}")

# Suprimir warnings específicos de XTTS sobre límite de caracteres
warnings.filterwarnings('ignore', message='.*text length exceeds.*character limit.*')
warnings.filterwarnings('ignore', message='.*might cause truncated audio.*')
# Suprimir warnings de torchaudio sobre cambios futuros
warnings.filterwarnings('ignore', message='.*In 2.9, this function.*implementation will be changed.*')
warnings.filterwarnings('ignore', category=UserWarning, module='torchaudio')

# Fix para PyTorch 2.6+ - weights_only=False por defecto
import torch
_original_torch_load = torch.load

def custom_torch_load(*args, **kwargs):
    """Custom torch.load que fuerza weights_only=False para compatibilidad con TTS"""
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

# Sobrescribir globalmente para TTS
torch.load = custom_torch_load

# También establecer variable de entorno como respaldo
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import requests
from pydub import AudioSegment

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.utils import set_audio_tags

logger = logging.getLogger(__name__)


class CoquiTTSProvider(BaseTTSProvider):
    """Local Coqui TTS provider with automatic model download and WAV output.

    This provider aims to match the Piper provider interface and behavior.
    It will download a model from a Coqui-compatible repository URL when missing.
    """

    def __init__(self, config: GeneralConfig):
        # La configuración SSL ya se aplicó automáticamente al importar
        
        # Configurar aceptación automática de licencia Coqui para evitar prompts interactivos
        self._setup_coqui_license()
        
        # Force Coqui outputs to MP3 by default to match Piper and other providers.
        # If the environment misses FFmpeg/ffprobe, raise a clear error instead of
        # silently falling back to WAV so the user can fix their environment.
        config.output_format = config.output_format or "mp3"
        from pydub.utils import which

        ffmpeg_path = which("ffmpeg")
        ffprobe_path = which("ffprobe")
        # If user wants a non-WAV format (we default to MP3), ensure ffmpeg/ffprobe exist
        if str(config.output_format).lower() != "wav":
            if ffmpeg_path is None or ffprobe_path is None:
                raise RuntimeError(
                    "FFmpeg and/or ffprobe not found on PATH. Coqui TTS requires FFmpeg to produce MP3 output. "
                    "Install FFmpeg and ensure 'ffmpeg' and 'ffprobe' are available on PATH, then retry."
                )

        self.price = 0.0
        # default model repo base (user can set full model name in config.coqui_model)
        self.base_model_url = "https://models.silero.ai/coqui"  # placeholder; Coqui models often hosted elsewhere
        super().__init__(config)

    def __str__(self) -> str:
        return f"CoquiTTSProvider(config={self.config})"

    def validate_config(self):
        pass
    
    def _setup_coqui_license(self):
        """Configurar aceptación automática de licencia Coqui para evitar prompts interactivos"""
        try:
            import os
            from pathlib import Path
            
            # Variables de entorno para aceptar licencia automáticamente
            os.environ['COQUI_TOS'] = 'AGREED'
            os.environ['TTS_AGREE_LICENSE'] = 'yes' 
            os.environ['COQUI_AGREE_LICENSE'] = '1'
            
            # Crear archivo de configuración TTS si no existe
            try:
                from TTS.utils.manage import ModelManager
                tts_cache_path = Path.home() / ".cache" / "tts"
                tts_cache_path.mkdir(parents=True, exist_ok=True)
                
                # Crear archivo de aceptación de licencia
                license_file = tts_cache_path / ".tos_agreed"
                license_file.touch(exist_ok=True)
                
                # También en el directorio de modelos si existe
                models_dir = tts_cache_path / "tts_models--multilingual--multi-dataset--xtts_v2"
                if models_dir.exists():
                    license_file_model = models_dir / ".tos_agreed" 
                    license_file_model.touch(exist_ok=True)
                
                logger.info("🤝 Configuración de licencia Coqui TTS establecida (uso no comercial)")
                
            except Exception as e:
                logger.debug(f"Error creando archivos de licencia: {e}")
            
            # Monkey patch para el manager de TTS si es necesario
            try:
                import TTS.utils.manage
                original_ask_tos = TTS.utils.manage.ModelManager.ask_tos
                
                def auto_accept_tos(self, output_path):
                    """Auto-acepta términos de servicio para uso no comercial"""
                    try:
                        # Crear archivo .tos_agreed automáticamente
                        tos_file = Path(output_path) / ".tos_agreed"
                        tos_file.touch(exist_ok=True)
                        logger.info("✅ Licencia Coqui aceptada automáticamente (uso no comercial)")
                        return True
                    except Exception as e:
                        logger.warning(f"Error auto-aceptando licencia: {e}")
                        return original_ask_tos(self, output_path)
                
                # Aplicar monkey patch
                TTS.utils.manage.ModelManager.ask_tos = auto_accept_tos
                logger.info("🔧 Monkey patch aplicado para aceptación automática de licencia")
                
            except Exception as e:
                logger.debug(f"Error aplicando monkey patch: {e}")
                
        except Exception as e:
            logger.warning(f"Error configurando licencia Coqui: {e}")
    
    def _safe_load_tts_model(self, model_name, device):
        """Carga modelo TTS con manejo robusto de errores SSL y certificados"""
        from TTS.api import TTS
        
        strategies = [
            # Estrategia 1: Carga normal (SSL ya configurado)
            lambda: TTS(model_name).to(device),
            
            # Estrategia 2: Forzar descarga offline si el modelo ya existe
            lambda: self._load_offline_first(model_name, device),
            
            # Estrategia 3: Con reconfiguración SSL forzada
            lambda: self._load_with_ssl_reconfig(model_name, device),
        ]
        
        last_error = None
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"Intentando estrategia de carga {i+1}/3...")
                result = strategy()
                logger.info(f"✅ Estrategia {i+1} exitosa")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Estrategia {i+1} falló: {e}")
                
                # Si es error SSL, reconfigurar y continuar
                if ssl_manager.is_ssl_error(e):
                    logger.info("🔧 Error SSL detectado, reconfigurando...")
                    ssl_manager.setup_ssl_environment()
                    continue
        
        # Si todas las estrategias fallan, lanzar el último error
        raise last_error
    
    def _load_with_ssl_reconfig(self, model_name, device):
        """Carga modelo con reconfiguración SSL forzada"""
        from TTS.api import TTS
        
        # Reconfigurar SSL usando el sistema centralizado
        ssl_manager.setup_ssl_environment()
        
        # Configurar variables adicionales temporalmente
        temp_env = {
            'PYTHONHTTPSVERIFY': '0',
            'SSL_VERIFY': 'false',
            'HF_HUB_OFFLINE': '0'
        }
        
        original_env = {}
        for key, value in temp_env.items():
            original_env[key] = os.environ.get(key, '')
            os.environ[key] = value
        
        try:
            tts = TTS(model_name).to(device)
            return tts
        finally:
            # Restaurar variables originales
            for key, original_value in original_env.items():
                if original_value:
                    os.environ[key] = original_value
                else:
                    os.environ.pop(key, None)
    
    def _load_offline_first(self, model_name, device):
        """Intenta cargar modelo desde cache local si existe"""
        from TTS.api import TTS
        import huggingface_hub
        
        try:
            # Verificar si el modelo está en cache local
            cache_dir = huggingface_hub.constants.HUGGINGFACE_HUB_CACHE
            
            # Si existe en cache, intentar carga offline
            if os.path.exists(cache_dir):
                # Configurar modo offline temporal
                original_offline = os.environ.get('HF_HUB_OFFLINE', '0')
                os.environ['HF_HUB_OFFLINE'] = '1'
                
                try:
                    tts = TTS(model_name).to(device)
                    logger.info("✅ Modelo cargado desde cache local (offline)")
                    return tts
                except Exception as offline_error:
                    logger.debug(f"Carga offline falló: {offline_error}")
                    # Restaurar modo online y continuar
                    os.environ['HF_HUB_OFFLINE'] = original_offline
                    raise offline_error
                finally:
                    os.environ['HF_HUB_OFFLINE'] = original_offline
            else:
                # No hay cache, usar carga normal con configuración SSL
                return TTS(model_name).to(device)
                
        except Exception as e:
            raise e
    


    def _detect_language_from_model(self) -> str:
        """Detect language from the Coqui model name."""
        if not self.config.coqui_model:
            return "es"  # Default to Spanish for our Spanish-focused app
        
        model_name = self.config.coqui_model.lower()
        
        # Handle XTTS multilingual model - always use Spanish for our use case
        if "xtts" in model_name or "multilingual" in model_name:
            logger.info(f"Detected multilingual model '{self.config.coqui_model}', using Spanish")
            return "es"
        
        # Extract language from model path like "tts_models/es/css10/vits"
        if "/es/" in model_name or model_name.startswith("es") or "spanish" in model_name or "css10" in model_name or "mai" in model_name:
            return "es"
        elif "/en/" in model_name or model_name.startswith("en"):
            return "en"
        elif "/fr/" in model_name or model_name.startswith("fr"):
            return "fr"
        elif "/de/" in model_name or model_name.startswith("de"):
            return "de"
        elif "/it/" in model_name or model_name.startswith("it"):
            return "it"
        elif "/pt/" in model_name or model_name.startswith("pt"):
            return "pt"
        elif "/ru/" in model_name or model_name.startswith("ru"):
            return "ru"
        elif "/ja/" in model_name or model_name.startswith("ja"):
            return "ja"
        elif "/zh-cn/" in model_name or model_name.startswith("zh"):
            return "zh-cn"
        elif "/ko/" in model_name or model_name.startswith("ko"):
            return "ko"
        
        # If we can't detect, default to Spanish for our Spanish-focused application
        logger.info(f"Could not detect language from model '{self.config.coqui_model}', defaulting to Spanish")
        return "es"

    def _normalize_text_if_needed(self, text: str) -> str:
        """Apply text normalization if the model is Spanish."""
        try:
            # Detect language from model
            language = self._detect_language_from_model()
            
            # Only normalize for Spanish models
            if language.startswith('es'):
                from audiobook_generator.utils.text_normalizer import normalize_text_for_tts, is_normalization_needed
                
                # Check if normalization is needed to avoid unnecessary processing
                if is_normalization_needed(text, language):
                    normalized = normalize_text_for_tts(text, language)
                    if normalized != text:
                        logger.info(f"Applied Spanish text normalization to chunk of {len(text)} characters")
                    return normalized
            
            return text
            
        except ImportError as e:
            logger.warning(f"Text normalizer not available: {e}")
            return text
        except Exception as e:
            logger.error(f"Error during text normalization: {e}")
            return text

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        # For now implement local-only path using the TTS python package if installed
        if not self.config.coqui_model:
            raise ValueError("Coqui model not configured (config.coqui_model)")
        
        # Apply text normalization for Spanish models
        normalized_text = self._normalize_text_if_needed(text)
        
        self._text_to_speech_local(normalized_text, output_file, audio_tags)

    def _download_model(self, model_name: str, dest_dir: Path) -> Path:
        """Download model files for a Coqui/TTS model with SSL error handling.

        This implementation expects a model archive available via a direct URL or a huggingface-like path.
        We'll support both a raw URL (if model_name starts with http) or a HF-style id.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar requests session con SSL handling
        session = self._create_secure_session()
        
        # If the user passed a full URL, try to download that as a file
        if model_name.lower().startswith("http"):
            out_path = dest_dir / Path(model_name).name
            if not out_path.exists():
                logger.info(f"Downloading Coqui model from {model_name} to {out_path}")
                try:
                    with session.get(model_name, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        with open(out_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                except Exception as e:
                    logger.error(f"Error downloading model from {model_name}: {e}")
                    if ssl_manager.is_ssl_error(e):
                        ssl_manager.provide_troubleshooting_info(e)
                    raise
            return out_path

        # If not a direct URL, assume a huggingface-style repo id and try to download the TTS model .pth or config
        # We'll try a best-effort approach: construct download URLs for model.pth and config.json
        model_base = model_name
        possible_files = [f"{model_base}.pth", f"{model_base}.tar.gz", "config.json", "model.pt"]
        successful_downloads = 0
        
        for fname in possible_files:
            url = f"https://huggingface.co/{model_base}/resolve/main/{fname}"
            out_path = dest_dir / fname
            if out_path.exists():
                logger.info(f"Model artifact {fname} already present, skipping download")
                successful_downloads += 1
                continue
                
            try:
                logger.info(f"Trying to download {url}")
                with session.get(url, stream=True, timeout=30) as r:
                    if r.status_code == 200:
                        with open(out_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        logger.info(f"Downloaded {fname} to {out_path}")
                        successful_downloads += 1
                    else:
                        logger.debug(f"File {fname} not found on server (status: {r.status_code})")
            except Exception as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['ssl', 'certificate', 'handshake']):
                    logger.warning(f"SSL error downloading {fname}: {e}")
                    # No lanzar error inmediatamente, intentar otros archivos
                else:
                    logger.debug(f"Could not download {url}: {e}")

        # Si no se descargó nada y había errores SSL, informar al usuario
        if successful_downloads == 0:
            logger.warning("No se pudieron descargar archivos del modelo. Esto puede indicar un problema de conectividad.")
            logger.info("TTS intentará descargar automáticamente cuando sea necesario.")

        # Return the directory for TTS loader to search; the TTS python package often accepts model name or path
        return dest_dir
    
    def _create_secure_session(self):
        """Crear session de requests con configuración SSL robusta"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Configurar SSL
        session.verify = False
        
        # Configurar retry strategy (compatible con urllib3 1.x y 2.x)
        try:
            # Para urllib3 2.0+
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        except TypeError:
            try:
                # Para urllib3 1.x
                retry_strategy = Retry(
                    total=3,
                    status_forcelist=[429, 500, 502, 503, 504],
                    method_whitelist=["HEAD", "GET", "OPTIONS"],
                    backoff_factor=1
                )
            except TypeError:
                # Fallback sin métodos específicos
                retry_strategy = Retry(
                    total=3,
                    status_forcelist=[429, 500, 502, 503, 504],
                    backoff_factor=1
                )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers para evitar bloqueos
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session

    def _text_to_speech_local(self, text: str, output_file: str, audio_tags: AudioTags):
        # Handle different model types
        model_id = self.config.coqui_model

        # Check if it's a local model (prefixed with "local:")
        if model_id.startswith("local:"):
            # Use local model path
            local_model_name = model_id[6:]  # Remove "local:" prefix
            coqui_root = Path(self.config.coqui_path) if self.config.coqui_path else Path(__file__).parent.parent.parent / "coqui_models"
            model_path = coqui_root / local_model_name
            if not model_path.exists():
                raise ValueError(f"Local Coqui model '{local_model_name}' not found in {coqui_root}. Please ensure the model is properly installed.")
            tts_model = str(model_path)
        else:
            # Use hub model directly
            tts_model = model_id

        # Try to use the TTS python package (Coqui/TTS). Import lazily so requirements are optional.
        try:
            from TTS.api import TTS
            import torch
            
            # Configurar logging de TTS para suprimir warnings de límite de caracteres
            tts_logger = logging.getLogger('TTS')
            tts_logger.setLevel(logging.ERROR)  # Solo mostrar errores críticos
            
            # Suprimir warnings adicionales que puedan aparecer durante inicialización
            warnings.filterwarnings('ignore', category=UserWarning, module='TTS')
            
        except Exception as e:
            logger.error("TTS package not available. Install with `pip install TTS` (Coqui TTS)")
            raise

        # Handle device configuration
        device = "cpu"
        if hasattr(self.config, 'coqui_device') and self.config.coqui_device:
            device = self.config.coqui_device
        
        if device == "cuda" and torch.cuda.is_available():
            import os
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            torch.cuda.set_device(0)
            logger.info(f"Using GPU: {torch.cuda.get_device_name(torch.cuda.current_device())}")
        elif device == "cuda":
            logger.warning("CUDA requested but not available, falling back to CPU")
            device = "cpu"
        
        logger.info(f"Using device: {device}")

        # Initialize TTS model with SSL error handling
        logger.info(f"Initializing Coqui TTS model: {tts_model}")
        try:
            # Intentar cargar modelo con múltiples estrategias
            tts = self._safe_load_tts_model(tts_model, device)
            logger.info(f"TTS model loaded successfully on {device}")
            
            # Log model capabilities (defensive checks)
            try:
                is_multi_speaker = getattr(tts, 'is_multi_speaker', False)
                speakers_list = getattr(tts, 'speakers', None)
                if is_multi_speaker:
                    speakers_count = len(speakers_list) if speakers_list else 0
                    logger.info(f"Multi-speaker model with {speakers_count} speakers")
            except Exception:
                logger.debug("Could not determine multi-speaker capabilities for TTS model")

            try:
                is_multi_lingual = getattr(tts, 'is_multi_lingual', False)
                languages_list = getattr(tts, 'languages', None)
                if is_multi_lingual:
                    languages_count = len(languages_list) if languages_list else 0
                    logger.info(f"Multi-lingual model with {languages_count} languages")
            except Exception:
                logger.debug("Could not determine multi-lingual capabilities for TTS model")
                
        except Exception as e:
            # Usar el sistema SSL centralizado para detectar y manejar errores
            if ssl_manager.is_ssl_error(e):
                logger.error("❌ Error de certificado SSL detectado. Aplicando soluciones...")
                try:
                    # Re-aplicar configuración SSL y reintentar
                    ssl_manager.setup_ssl_environment()
                    tts = self._safe_load_tts_model(tts_model, device)
                    logger.info("✅ Modelo cargado exitosamente después de corregir SSL")
                except Exception as ssl_retry_error:
                    logger.error(f"Error persistente después de corregir SSL: {ssl_retry_error}")
                    ssl_manager.provide_troubleshooting_info(e)
                    raise
            else:
                logger.error(f"Failed to initialize TTS model {tts_model}: {e}")
                if "local:" in model_id:
                    logger.error("For local models, ensure the model files are correctly placed in the coqui_models directory")
                else:
                    logger.error("For hub models, check the model name format (should be like 'tts_models/language/dataset/model')")
                raise

        tmpdir_obj = None
        try:
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdirname = tmpdir_obj.name
            tmpwav = Path(tmpdirname) / "coqui.wav"

            logger.info("Synthesizing with Coqui TTS")
            # Log GPU memory before synthesis
            if device == "cuda" and torch.cuda.is_available():
                logger.info(f"GPU memory allocated before synthesis: {torch.cuda.memory_allocated()/1024**2:.2f} MB")
            
            try:
                # Build kwargs for TTS synthesis
                tts_kwargs = {
                    "text": text,
                    "file_path": str(tmpwav)
                }
                
                # Handle speaker selection for multi-speaker models
                if hasattr(self.config, 'coqui_speaker') and self.config.coqui_speaker:
                    speaker = self.config.coqui_speaker
                    
                    # Handle voice cloning for XTTS models
                    if "xtts" in model_id.lower() and ("Clonación" in speaker or "Custom" in speaker):
                        # For XTTS voice cloning, user should provide speaker_wav file
                        if hasattr(self.config, 'coqui_speaker_wav') and self.config.coqui_speaker_wav:
                            tts_kwargs["speaker_wav"] = self.config.coqui_speaker_wav
                            logger.info(f"🎙️ Usando clonación de voz con archivo: {self.config.coqui_speaker_wav}")
                        else:
                            logger.warning("Clonación de voz solicitada pero no se proporcionó archivo speaker_wav, usando voz predeterminada")
                            # Fallback to a good Spanish voice
                            default_spanish_voices = ["Ana Florence", "Sofia Hellen", "Tanja Adelina"]
                            tts_kwargs["speaker"] = default_spanish_voices[0]  # Ana Florence for Spanish
                            logger.info(f"🎤 Usando voz por defecto para español: {default_spanish_voices[0]}")
                    else:
                        # Regular speaker selection - handle Spanish voice names
                        original_speaker = speaker
                        # Clean up Spanish descriptive names
                        if " (" in speaker:
                            speaker = speaker.split(" (")[0]
                        
                        # Check if model supports multiple speakers safely
                        is_multi_speaker = getattr(tts, 'is_multi_speaker', False)
                        if is_multi_speaker:
                            # For XTTS models, use predefined speaker names
                            xtts_speakers = [
                                "Claribel Dervla", "Daisy Studious", "Gracie Wise", "Tammie Ema",
                                "Alison Dietlinde", "Ana Florence", "Annmarie Nele", "Asya Anara",
                                "Brenda Stern", "Gitta Nikolina", "Henriette Usha", "Sofia Hellen",
                                "Tammy Grit", "Tanja Adelina", "Vjollca Johnnie", "Andrew Chipper",
                                "Badr Odhiambo", "Dionisio Schuyler", "Royston Min", "Viktor Eka",
                                "Abrahan Mack", "Adde Michal", "Baldur Sanjin", "Craig Gutsy", "Damien Black",
                                "Gilberto Mathias", "Ilkin Urbano", "Kazuhiko Atallah", "Ludvig Milivoj",
                                "Suad Qasim", "Torcull Diarmuid", "Viktor Menelaos", "Zacharie Aimilios"
                            ]
                            
                            if speaker in xtts_speakers:
                                tts_kwargs["speaker"] = speaker
                                logger.info(f"🎤 Usando locutor XTTS: {original_speaker}")
                            else:
                                # Use Ana Florence as default for Spanish
                                tts_kwargs["speaker"] = "Ana Florence"
                                logger.info(f"🎤 Locutor '{original_speaker}' no reconocido, usando Ana Florence para español")
                        else:
                            logger.info("🎤 Modelo de un solo locutor")
                else:
                    # No speaker specified, use default for XTTS models
                    if "xtts" in model_id.lower():
                        tts_kwargs["speaker"] = "Ana Florence"  # Good default for Spanish
                        logger.info("🎤 Sin locutor especificado, usando Ana Florence para español")
                
                # Handle language selection for multi-lingual models
                if hasattr(self.config, 'coqui_language') and self.config.coqui_language:
                    language = self.config.coqui_language
                    # For multilingual models, always use the configured language
                    if "xtts" in model_id.lower() or "/multilingual/" in model_id.lower():
                        tts_kwargs["language"] = language
                        logger.info(f"🌍 Usando idioma configurado: {language}")
                else:
                    # No language specified, use Spanish for XTTS models
                    if "xtts" in model_id.lower():
                        tts_kwargs["language"] = "es"  # Spanish by default
                        logger.info("🌍 Sin idioma especificado, usando español por defecto")
                
                # Add synthesis parameters
                if hasattr(self.config, 'coqui_length_scale') and self.config.coqui_length_scale is not None:
                    # Length scale affects speech rate (lower = faster)
                    length_scale = float(self.config.coqui_length_scale)
                    logger.info(f"Using length scale: {length_scale}")
                
                if hasattr(self.config, 'coqui_noise_scale') and self.config.coqui_noise_scale is not None:
                    # Noise scale affects speech variability
                    noise_scale = float(self.config.coqui_noise_scale)
                    logger.info(f"Using noise scale: {noise_scale}")
                
                if hasattr(self.config, 'coqui_noise_w_scale') and self.config.coqui_noise_w_scale is not None:
                    # Noise w scale affects duration variability
                    noise_w_scale = float(self.config.coqui_noise_w_scale)
                    logger.info(f"Using noise w scale: {noise_w_scale}")
                
                # Handle speed/rate parameter for XTTS models
                if hasattr(self.config, 'speed') and self.config.speed is not None:
                    speed = float(self.config.speed)
                    if speed != 1.0:
                        logger.info(f"Using speed: {speed}")
                
                # For XTTS models, handle text chunking to respect character limits
                if "xtts" in model_id.lower():
                    # Usar la funcionalidad nativa de XTTS para división de texto
                    tts_kwargs["enable_text_splitting"] = True
                    logger.info("Enabled native text splitting for XTTS model")
                    
                    # Para textos muy largos, usar nuestro chunking adicional como respaldo
                    if len(text) > 1000:  # Conservative limit based on token count
                        logger.info(f"Text length ({len(text)}) exceeds safe limit, using enhanced chunking")
                        
                        # Suprimir warnings temporalmente durante el chunking
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            self._synthesize_xtts_chunks(tts, text, str(tmpwav), tts_kwargs, logger)
                        # Skip the normal synthesis since chunking handles it
                        logger.info("Enhanced chunk synthesis completed")
                    else:
                        # Para textos cortos, usar síntesis normal con división nativa
                        logger.info(f"Using native XTTS text splitting for text of {len(text)} characters")
                        tts.tts_to_file(**tts_kwargs)
                else:
                    logger.info(f"TTS synthesis parameters: {tts_kwargs}")
                    # Perform TTS synthesis for non-XTTS models
                    tts.tts_to_file(**tts_kwargs)
                
            except TypeError as e:
                logger.warning(f"Parameter error ({e}), trying fallback synthesis")
                # Fallback for compatibility
                tts.tts_to_file(text=text, file_path=str(tmpwav))
            except Exception as e:
                logger.error(f"TTS synthesis failed: {e}")
                raise

            # Log GPU memory after synthesis
            if device == "cuda" and torch.cuda.is_available():
                logger.info(f"GPU memory allocated after synthesis: {torch.cuda.memory_allocated()/1024**2:.2f} MB")

            if not tmpwav.exists():
                raise FileNotFoundError(f"Coqui TTS failed to create output file: {tmpwav}")

            # set audio tags before conversion if needed
            if audio_tags:
                set_audio_tags(tmpwav, audio_tags)

            exported_file = output_file
            try:
                # Load audio and apply high quality settings
                audio_segment = AudioSegment.from_wav(tmpwav)
                self._export_with_high_quality(audio_segment, output_file)
                del audio_segment
            except Exception as conv_err:
                logger.warning(f"Failed to export with high quality ({conv_err}); falling back to basic export")
                if self.config.output_format.lower() == 'wav':
                    shutil.copy2(tmpwav, output_file)
                else:
                    audio_segment = AudioSegment.from_wav(tmpwav)
                    audio_segment.export(output_file, format=self.config.output_format)
                    del audio_segment

            if audio_tags:
                try:
                    set_audio_tags(exported_file, audio_tags)
                except Exception as tag_err:
                    logger.warning(f"Failed to set audio tags on {exported_file}: {tag_err}")

            logger.info(f"Coqui conversion completed, output file: {exported_file}")

        finally:
            if tmpdir_obj:
                try:
                    tmpdir_obj.cleanup()
                except Exception:
                    pass

    def estimate_cost(self, total_chars):
        return 0

    def get_break_string(self):
        return "."

    def get_output_file_extension(self):
        return self.config.output_format

    def _synthesize_xtts_chunks(self, tts, text, output_path, base_kwargs, logger):
        """
        Synthesize text using XTTS with ENHANCED noise reduction and intelligent audio processing
        """
        from pydub import AudioSegment
        import tempfile
        import os
        
        # Import our new universal audio processing systems
        try:
            from audiobook_generator.utils.universal_audio_cleaner import UniversalAudioCleaner, detect_tts_type
            from audiobook_generator.utils.intelligent_audio_combiner import IntelligentAudioCombiner
            use_advanced_processing = True
            logger.info("🎵 Using ADVANCED audio processing for noise-free chunk combination")
        except ImportError as e:
            logger.warning(f"Advanced audio processing not available: {e}, using basic processing")
            use_advanced_processing = False
        
        # Detect TTS type for optimal configuration
        tts_type = detect_tts_type("coqui", base_kwargs.get('text', ''))
        
        # Initialize advanced processors if available
        if use_advanced_processing:
            audio_cleaner = UniversalAudioCleaner(sample_rate=22050, enable_aggressive_cleaning=True)
            audio_combiner = IntelligentAudioCombiner(tts_type=tts_type)
        
        # Split text into chunks respecting token boundaries
        chunks = self._split_text_for_xtts(text, max_tokens=350)
        logger.info(f"Split text into {len(chunks)} chunks for ENHANCED XTTS processing")
        
        audio_segments = []
        chunk_texts = []  # Para el combiner inteligente
        temp_files = []
        
        try:
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                    
                logger.info(f"Processing chunk {i+1}/{len(chunks)}: {len(chunk)} chars (~{len(chunk.split())} words)")
                
                # Create temporary file for this chunk
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    chunk_path = tmp_file.name
                    temp_files.append(chunk_path)
                
                # Update kwargs for this chunk
                chunk_kwargs = base_kwargs.copy()
                chunk_kwargs['text'] = chunk
                chunk_kwargs['file_path'] = chunk_path
                
                # Synthesize this chunk with warnings suppressed
                try:
                    # Suprimir warnings de límite de caracteres durante síntesis de chunks
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        tts.tts_to_file(**chunk_kwargs)
                    
                    # Load audio
                    chunk_audio = AudioSegment.from_wav(chunk_path)
                    
                    # 🆕 ENHANCED AUDIO PROCESSING - Eliminar pops, clics y artifacts
                    if use_advanced_processing:
                        # Usar el nuevo sistema universal de limpieza
                        chunk_audio = audio_cleaner.clean_chunk_audio(
                            chunk_audio, 
                            chunk_index=i, 
                            total_chunks=len(chunks),
                            tts_type=tts_type
                        )
                        logger.debug(f"✨ Applied advanced cleaning to chunk {i+1}")
                    else:
                        # Fallback a limpieza básica
                        chunk_audio = self._basic_chunk_cleaning(chunk_audio, i, len(chunks))
                    
                    audio_segments.append(chunk_audio)
                    chunk_texts.append(chunk)  # Guardar texto para análisis inteligente
                    
                    # 📝 NO agregar pausas aquí - el combiner inteligente las manejará
                        
                except Exception as e:
                    logger.error(f"Failed to synthesize chunk {i+1}: {str(e)}")
                    logger.error(f"Problematic chunk content: {chunk[:100]}...")
                    # Continue with next chunk instead of failing completely
                    continue
            
            if not audio_segments:
                raise Exception("No audio segments were successfully generated")
            
            # 🚀 ENHANCED AUDIO COMBINATION - Sin pops, clics ni ruidos
            if use_advanced_processing:
                # Usar el nuevo sistema inteligente de combinación
                combined_audio = audio_combiner.combine_audio_segments(
                    audio_segments, 
                    chunk_texts=chunk_texts,
                    validate_integrity=True
                )
                logger.info(f"🎵 Used INTELLIGENT audio combination with noise elimination")
            else:
                # Fallback a combinación básica mejorada
                combined_audio = self._enhanced_basic_combination(audio_segments, logger)
            
            # Post-procesamiento final si no se usó el sistema avanzado
            if not use_advanced_processing:
                combined_audio = self._normalize_audio_level(combined_audio)
                combined_audio = self._apply_soft_limiter(combined_audio, logger)
            
            # Exportar con calidad alta
            self._export_with_high_quality(combined_audio, output_path)
            
            logger.info(f"🎉 Successfully combined {len(audio_segments)} audio segments "
                       f"with ENHANCED processing (duration: {len(combined_audio)}ms)")
                
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

    def _normalize_audio_level(self, audio_segment):
        """Normaliza el nivel de audio para evitar diferencias de volumen"""
        target_dBFS = -20.0  # Nivel target en dBFS
        current_dBFS = audio_segment.dBFS
        
        if current_dBFS < -50.0:  # Audio muy silencioso
            return audio_segment
        
        change_in_dBFS = target_dBFS - current_dBFS
        return audio_segment.apply_gain(change_in_dBFS)

    def _apply_soft_limiter(self, audio_segment, logger=None):
        """Aplica un limiter suave para evitar distorsión de manera eficiente en memoria"""
        try:
            # Si el audio es corto (menos de 30 segundos), usar método normal
            if len(audio_segment) < 30000:  # 30 segundos
                if audio_segment.max_dBFS > -3.0:
                    return audio_segment.compress_dynamic_range(
                        threshold=-12.0,
                        ratio=4.0,
                        attack=5.0,
                        release=50.0
                    )
                return audio_segment
            
            # Para audio largo, procesar en chunks para evitar MemoryError
            chunk_size = 10000  # 10 segundos por chunk
            processed_chunks = []
            
            for i in range(0, len(audio_segment), chunk_size):
                chunk = audio_segment[i:i + chunk_size]
                
                # Aplicar limiter solo si es necesario
                if chunk.max_dBFS > -3.0:
                    try:
                        processed_chunk = chunk.compress_dynamic_range(
                            threshold=-12.0,
                            ratio=4.0,
                            attack=5.0,
                            release=50.0
                        )
                        processed_chunks.append(processed_chunk)
                    except MemoryError:
                        # Si falla, usar solo normalización simple
                        if logger:
                            logger.warning(f"MemoryError en chunk {i//chunk_size + 1}, usando normalización simple")
                        if chunk.max_dBFS > -1.0:
                            processed_chunk = chunk.apply_gain(-1.0 - chunk.max_dBFS)
                        else:
                            processed_chunk = chunk
                        processed_chunks.append(processed_chunk)
                else:
                    processed_chunks.append(chunk)
            
            # Combinar chunks procesados
            if processed_chunks:
                result = processed_chunks[0]
                for chunk in processed_chunks[1:]:
                    result += chunk
                return result
            else:
                return audio_segment
                
        except Exception as e:
            if logger:
                logger.warning(f"Error en soft limiter: {e}, usando audio original")
            return audio_segment

    def _combine_audio_smoothly(self, audio_segments, logger):
        """Combina segmentos de audio con transiciones suaves"""
        if not audio_segments:
            return None
        
        if len(audio_segments) == 1:
            return audio_segments[0]
        
        # Empezar con el primer segmento
        result = audio_segments[0]
        
        # Combinar el resto con crossfade muy sutil
        for i in range(1, len(audio_segments)):
            segment = audio_segments[i]
            
            # Si es silencio, solo append
            if self._is_silence(segment):
                result += segment
            else:
                # Crossfade muy sutil (10ms) solo si ambos tienen contenido
                if len(result) > 20 and len(segment) > 20:
                    result = result.append(segment, crossfade=10)
                else:
                    result += segment
        
        return result

    def _is_silence(self, audio_segment):
        """Detecta si un segmento es silencio"""
        return audio_segment.dBFS < -50.0 or len(audio_segment) < 200

    def _apply_audio_quality_settings(self, audio_segment):
        """Apply quality settings to audio segment"""
        
        # Convert to mono/stereo
        if hasattr(self.config, 'coqui_audio_channels'):
            target_channels = self.config.coqui_audio_channels
            if target_channels == 1 and audio_segment.channels > 1:
                audio_segment = audio_segment.set_channels(1)
            elif target_channels == 2 and audio_segment.channels == 1:
                # Convert mono to stereo by duplicating channel
                audio_segment = audio_segment.set_channels(2)
        
        # Set sample rate
        if hasattr(self.config, 'coqui_sample_rate'):
            target_rate = int(self.config.coqui_sample_rate)
            if audio_segment.frame_rate != target_rate:
                audio_segment = audio_segment.set_frame_rate(target_rate)
        
        # Apply volume normalization if enabled
        if getattr(self.config, 'coqui_normalize_volume', True):
            audio_segment = self._normalize_audio_level(audio_segment)
        
        # Apply limiter if enabled
        if getattr(self.config, 'coqui_enable_limiter', True):
            audio_segment = self._apply_soft_limiter(audio_segment, None)  # No logger available here
        
        return audio_segment

    def _export_with_high_quality(self, audio_segment, output_path):
        """Export audio with high quality settings"""
        from pathlib import Path
        
        # Apply quality settings first
        audio_segment = self._apply_audio_quality_settings(audio_segment)
        
        # Get format from output path
        format_type = Path(output_path).suffix.lower().lstrip('.')
        
        if format_type == "mp3":
            # High quality MP3 export
            bitrate = getattr(self.config, 'coqui_audio_bitrate', '320k')
            mp3_quality = getattr(self.config, 'coqui_mp3_quality', 0)
            
            # Use high quality parameters
            audio_segment.export(
                output_path, 
                format="mp3",
                bitrate=bitrate,
                parameters=[
                    "-q:a", str(mp3_quality),      # Quality (0=best)
                    "-compression_level", "0",      # No compression
                    "-joint_stereo", "0",          # No joint stereo
                    "-reservoir", "1",             # Enable bit reservoir
                    "-abr", "1" if "k" in bitrate else "0"  # Enable ABR
                ]
            )
        elif format_type == "wav":
            # High quality WAV export
            bit_depth = getattr(self.config, 'coqui_wav_bit_depth', 24)
            sample_rate = getattr(self.config, 'coqui_sample_rate', 44100)
            
            if bit_depth == 16:
                codec = "pcm_s16le"
            elif bit_depth == 24:
                codec = "pcm_s24le" 
            elif bit_depth == 32:
                codec = "pcm_s32le"
            else:
                codec = "pcm_s24le"  # Default to 24-bit
                
            audio_segment.export(
                output_path,
                format="wav",
                parameters=[
                    "-acodec", codec, 
                    "-ar", str(sample_rate),
                    "-ac", str(audio_segment.channels)
                ]
            )
        else:
            # For other formats, use default high quality
            audio_segment.export(output_path, format=format_type, bitrate="320k")
        
        logger.info(f"🎵 Exported audio with HIGH QUALITY: {format_type.upper()}, "
                   f"{getattr(self.config, 'coqui_sample_rate', 44100)}Hz, "
                   f"{getattr(self.config, 'coqui_wav_bit_depth', 24)}-bit, "
                   f"{getattr(self.config, 'coqui_audio_bitrate', '320k')}")

    def _split_text_for_xtts(self, text, max_tokens=350):
        """
        Split text into chunks that respect XTTS token limits.
        XTTS has a maximum of 400 tokens, using 350 for safety margin.
        
        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk (default 350 for safety)
        
        Returns:
            List of text chunks
        """
        import re
        
        # Estimación aproximada: 1 token ≈ 3-4 caracteres en español
        # Usamos 3 caracteres por token para ser conservadores
        estimated_chars_per_token = 3
        max_chars_per_chunk = max_tokens * estimated_chars_per_token  # ~1050 chars
        
        if len(text) <= max_chars_per_chunk:
            return [text]
        
        chunks = []
        
        # Primero dividir por párrafos para mantener coherencia
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Si el párrafo solo es muy largo, procesarlo por oraciones
            if len(paragraph) > max_chars_per_chunk:
                # Guardar chunk actual si existe
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Procesar párrafo largo por oraciones
                sentence_chunks = self._split_long_paragraph(paragraph, max_chars_per_chunk)
                chunks.extend(sentence_chunks)
            else:
                # Verificar si podemos agregar el párrafo al chunk actual
                test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                if len(test_chunk) <= max_chars_per_chunk:
                    current_chunk = test_chunk
                else:
                    # Guardar chunk actual y empezar nuevo
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
        
        # Agregar último chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]

    def _split_long_paragraph(self, paragraph, max_chars):
        """Split a long paragraph into smaller chunks by sentences."""
        import re
        
        # Dividir por oraciones (patrones de puntuación)
        sentence_pattern = r'([.!?]+[\s]*)'
        parts = re.split(sentence_pattern, paragraph)
        
        # Reconstruir oraciones completas
        sentences = []
        for i in range(0, len(parts), 2):
            sentence = parts[i]
            if i + 1 < len(parts):
                sentence += parts[i + 1]
            if sentence.strip():
                sentences.append(sentence.strip())
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(sentence) > max_chars:
                # Oración muy larga, dividir por palabras
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                word_chunks = self._split_by_words(sentence, max_chars)
                chunks.extend(word_chunks)
            else:
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                if len(test_chunk) <= max_chars:
                    current_chunk = test_chunk
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def _split_by_words(self, text, max_chars):
        """Split text by words when sentences are too long."""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(word) > max_chars:
                # Palabra extremadamente larga, truncar (caso muy raro)
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(word[:max_chars])
            else:
                test_chunk = current_chunk + " " + word if current_chunk else word
                if len(test_chunk) <= max_chars:
                    current_chunk = test_chunk
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = word
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    # 🆕 MÉTODOS DE FALLBACK PARA SISTEMAS SIN PROCESAMIENTO AVANZADO
    
    def _basic_chunk_cleaning(self, audio_segment, chunk_index, total_chunks):
        """Limpieza básica de chunks cuando no está disponible el sistema avanzado"""
        try:
            # 1. Remover DC offset básico
            try:
                import numpy as np
                samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                if audio_segment.channels == 2:
                    samples = samples.reshape((-1, 2))
                    samples = samples - np.mean(samples, axis=0)
                    samples = samples.flatten()
                else:
                    samples = samples - np.mean(samples)
                
                samples = np.clip(samples, -32767, 32767)
                audio_segment = audio_segment._spawn(samples.astype(np.int16).tobytes())
            except:
                pass  # Si falla, usar audio original
            
            # 2. Normalización básica
            audio_segment = self._normalize_audio_level(audio_segment)
            
            # 3. Fades básicos
            is_first = (chunk_index == 0)
            is_last = (chunk_index == total_chunks - 1)
            
            if not is_first and len(audio_segment) > 50:
                audio_segment = audio_segment.fade_in(25)
            if not is_last and len(audio_segment) > 50:
                audio_segment = audio_segment.fade_out(25)
            
            return audio_segment
            
        except Exception as e:
            logger.warning(f"Basic chunk cleaning failed: {e}")
            return audio_segment
    
    def _enhanced_basic_combination(self, audio_segments, logger):
        """Combinación básica mejorada cuando no está disponible el sistema avanzado"""
        try:
            if not audio_segments:
                return None
            
            if len(audio_segments) == 1:
                return audio_segments[0]
            
            # Filtrar silencios muy cortos
            valid_segments = []
            for segment in audio_segments:
                if not self._is_silence(segment) or len(segment) > 100:
                    valid_segments.append(segment)
            
            if not valid_segments:
                return audio_segments[0] if audio_segments else None
            
            # Combinar con crossfades adaptativos
            result = valid_segments[0]
            
            for i in range(1, len(valid_segments)):
                current_segment = valid_segments[i]
                
                # Calcular crossfade basado en diferencia de volumen
                if i > 0:
                    prev_volume = result[-100:].dBFS if len(result) > 100 else result.dBFS
                    curr_volume = current_segment[:100].dBFS if len(current_segment) > 100 else current_segment.dBFS
                    
                    volume_diff = abs(prev_volume - curr_volume)
                    
                    if volume_diff < 3:
                        crossfade_duration = 20
                    elif volume_diff < 8:
                        crossfade_duration = 40
                    else:
                        crossfade_duration = 60
                    
                    # Limitar crossfade por duración de segmentos
                    max_crossfade = min(len(result), len(current_segment)) // 4
                    crossfade_duration = min(crossfade_duration, max_crossfade)
                
                # Aplicar crossfade o concatenación simple
                if crossfade_duration > 0 and not self._is_silence(current_segment):
                    try:
                        result = result.append(current_segment, crossfade=crossfade_duration)
                    except:
                        # Si falla el crossfade, usar concatenación simple con pausa
                        pause = AudioSegment.silent(duration=100)
                        result = result + pause + current_segment
                else:
                    # Para silencios, concatenación directa
                    result = result + current_segment
            
            logger.info("Used enhanced basic audio combination")
            return result
            
        except Exception as e:
            logger.warning(f"Enhanced basic combination failed: {e}, using simple concatenation")
            # Fallback final: concatenación simple
            result = audio_segments[0]
            for segment in audio_segments[1:]:
                result += segment
            return result


def get_coqui_supported_models(coqui_path: str = None):
    """Return a comprehensive list of Coqui TTS models organized by type and language."""
    
    # Multilingual models (including XTTS-v2) - Best for Spanish
    multilingual_models = [
        "tts_models/multilingual/multi-dataset/xtts_v2",  # XTTS-v2 - Best quality for Spanish with voice cloning
        "tts_models/multilingual/multi-dataset/your_tts",  # YourTTS - Voice cloning support
        "tts_models/multilingual/multi-dataset/xtts_v1.1",  # XTTS-v1.1 
        "tts_models/multilingual/multi-dataset/bark",  # Bark - Natural speech with emotions
    ]
    
    # Spanish specific models - HIGH PRIORITY
    spanish_models = [
        "tts_models/es/css10/vits",  # High quality Spanish VITS model
        "tts_models/es/mai/tacotron2-DDC",  # Spanish Tacotron2 model
    ]
    
    # Single language models organized by language
    models = multilingual_models + spanish_models + [
        # English models
        "tts_models/en/ljspeech/tacotron2-DDC",
        "tts_models/en/ljspeech/tacotron2-DDC_ph",
        "tts_models/en/ljspeech/glow-tts",
        "tts_models/en/ljspeech/speedy-speech",
        "tts_models/en/ljspeech/vits",
        "tts_models/en/ljspeech/overflow",
        "tts_models/en/ljspeech/neural_hmm",
        "tts_models/en/vctk/vits",
        "tts_models/en/vctk/fast_pitch",
        "tts_models/en/sam/tacotron-DDC",
        "tts_models/en/blizzard2013/capacitron-t2-c50",
        "tts_models/en/blizzard2013/capacitron-t2-c150_v2",
        "tts_models/en/multi-dataset/tortoise-v2",
        "tts_models/en/jenny/jenny",

        # Spanish models
        "tts_models/es/css10/vits",
        "tts_models/es/mai/tacotron2-DDC",

        # French models
        "tts_models/fr/css10/vits",
        "tts_models/fr/mai/tacotron2-DDC",

        # German models
        "tts_models/de/css10/vits-neon",
        "tts_models/de/thorsten/tacotron2-DCA",
        "tts_models/de/thorsten/vits",
        "tts_models/de/thorsten/tacotron2-DDC",

        # Italian models
        "tts_models/it/mai_female/glow-tts",
        "tts_models/it/mai_female/vits",
        "tts_models/it/mai_male/glow-tts",
        "tts_models/it/mai_male/vits",

        # Portuguese models
        "tts_models/pt/cv/vits",

        # Japanese models
        "tts_models/ja/kokoro/tacotron2-DDC",

        # Chinese models
        "tts_models/zh-CN/baker/tacotron2-DDC-GST",

        # Dutch models
        "tts_models/nl/css10/vits",
        "tts_models/nl/mai/tacotron2-DDC",

        # Other languages
        "tts_models/uk/mai/glow-tts",
        "tts_models/uk/mai/vits",
        "tts_models/tr/common-voice/glow-tts",
        "tts_models/ca/custom/vits",
        "tts_models/fa/custom/glow-tts",
        "tts_models/bn/custom/vits-male",
        "tts_models/bn/custom/vits-female",
        "tts_models/be/common-voice/glow-tts",
        
        # Common Voice models (multiple languages)
        "tts_models/bg/cv/vits",
        "tts_models/cs/cv/vits", 
        "tts_models/da/cv/vits",
        "tts_models/et/cv/vits",
        "tts_models/ga/cv/vits",
        "tts_models/el/cv/vits",
        "tts_models/fi/css10/vits",
        "tts_models/hr/cv/vits",
        "tts_models/hu/css10/vits",
        "tts_models/lt/cv/vits",
        "tts_models/lv/cv/vits",
        "tts_models/mt/cv/vits",
        "tts_models/pl/mai_female/vits",
        "tts_models/ro/cv/vits",
        "tts_models/sk/cv/vits",
        "tts_models/sl/cv/vits",
        "tts_models/sv/cv/vits",
    ]

    # Add any local models if they exist
    try:
        base = Path(coqui_path) if coqui_path else Path(__file__).parent.parent.parent / "coqui_models"
        if base.exists() and base.is_dir():
            for child in base.iterdir():
                if child.is_dir():
                    local_model = f"local:{child.name}"
                    if local_model not in models:
                        models.append(local_model)
    except Exception:
        pass

    return models


def get_coqui_supported_languages():
    """Return supported languages for Coqui TTS models, prioritizing Spanish."""
    return [
        "es",    # Español - PRIORIDAD
        "en", 
        "fr", 
        "de", 
        "it", 
        "pt", 
        "ru", 
        "ja", 
        "zh-cn", 
        "ko",
        "pl",
        "tr",
        "nl",
        "cs",
        "ar",
        "hu",
        "hi"
    ]


def get_coqui_models_by_language(language: str):
    """Return Coqui models for a specific language, including multilingual models."""
    all_models = get_coqui_supported_models()
    
    # First add models specific to the language
    language_specific = [model for model in all_models if f"/{language}/" in model or model.startswith(f"tts_models/{language}/")]
    
    # Always include multilingual models for any language
    multilingual_models = [model for model in all_models if "/multilingual/" in model]
    
    # For Spanish specifically, prioritize best models
    if language == "es":
        priority_models = [
            "tts_models/multilingual/multi-dataset/xtts_v2",  # XTTS-v2 FIRST
            "tts_models/es/css10/vits",  # Best Spanish-specific model
            "tts_models/es/mai/tacotron2-DDC",  # Alternative Spanish model
            "tts_models/multilingual/multi-dataset/your_tts",  # YourTTS for voice cloning
        ]
        
        # Create final list with priorities first, then language-specific, then other multilinguals
        result = []
        for model in priority_models:
            if model in all_models and model not in result:
                result.append(model)
        
        # Add other language-specific models
        for model in language_specific:
            if model not in result:
                result.append(model)
        
        # Add other multilingual models
        for model in multilingual_models:
            if model not in result:
                result.append(model)
        
        return result
    else:
        # For other languages, combine language-specific + multilingual
        combined = language_specific + multilingual_models
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for model in combined:
            if model not in seen:
                seen.add(model)
                result.append(model)
        return result


def get_coqui_supported_voices(model_name: str = None):
    """Get available voices for a specific Coqui TTS model."""
    try:
        # Import TTS here to check model capabilities
        from TTS.api import TTS
        
        if not model_name:
            return []
        
        # For XTTS models, predefined speakers optimized for Spanish
        if "xtts" in model_name.lower():
            return [
                # Female voices - Good for Spanish
                "Ana Florence",      # Excelente para español
                "Sofia Hellen",      # Muy buena calidad en español
                "Tanja Adelina",     # Natural en español
                "Claribel Dervla",   # Voz clara
                "Alison Dietlinde",  # Profesional
                "Gracie Wise",       # Expresiva
                "Daisy Studious",    # Educativa
                "Tammie Ema",        # Conversacional
                "Asya Anara",        # Melodiosa
                "Brenda Stern",      # Firme
                "Gitta Nikolina",    # Suave
                "Henriette Usha",    # Elegante
                "Tammy Grit",        # Decidida
                "Vjollca Johnnie",   # Única
                "Annmarie Nele",     # Amigable
                
                # Male voices - Good for Spanish
                "Andrew Chipper",    # Alegre y claro
                "Dionisio Schuyler", # Profundo y rico
                "Viktor Eka",        # Serio y profesional
                "Badr Odhiambo",     # Cálido y natural
                "Royston Min",       # Versátil
                
                # Voice cloning option
                "🎤 Clonación de Voz (sube archivo de referencia)"
            ]
        
        # For Spanish specific models
        elif "/es/" in model_name:
            if "css10" in model_name:
                return [
                    "Hablante Femenino CSS10",  # CSS10 Spanish dataset voice
                    "Default"
                ]
            elif "mai" in model_name:
                return [
                    "Hablante M.A.I.",  # M.A.I. Spanish dataset voice
                    "Default"
                ]
        
        # Try to load the model and get speakers dynamically
        try:
            tts = TTS(model_name)
            if tts.is_multi_speaker and tts.speakers:
                # Add Spanish descriptive names if possible
                spanish_speakers = []
                for i, speaker in enumerate(tts.speakers):
                    if isinstance(speaker, str):
                        spanish_speakers.append(f"{speaker} (Voz {i+1})")
                    else:
                        spanish_speakers.append(f"Voz {i+1}")
                return spanish_speakers if spanish_speakers else tts.speakers
            elif tts.is_multi_lingual and hasattr(tts, 'speakers') and tts.speakers:
                return tts.speakers
            else:
                return ["Voz por Defecto"]
        except Exception as e:
            logger.debug(f"Could not load model {model_name} to check speakers: {e}")
            return ["Voz por Defecto"]
            
    except ImportError:
        logger.warning("TTS package not available for voice detection")
        return ["Voz por Defecto"]
    except Exception as e:
        logger.error(f"Error getting voices for model {model_name}: {e}")
        return ["Voz por Defecto"]


def get_coqui_supported_languages_for_model(model_name: str = None):
    """Get supported languages for a specific Coqui TTS model."""
    try:
        from TTS.api import TTS
        
        if not model_name:
            return []
            
        # XTTS-v2 supported languages
        if "xtts" in model_name.lower():
            return [
                "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", 
                "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"
            ]
        
        # Try to load model and get languages
        try:
            tts = TTS(model_name)
            if tts.is_multi_lingual and tts.languages:
                return tts.languages
            else:
                # Extract language from model path
                if "/" in model_name:
                    parts = model_name.split("/")
                    if len(parts) >= 2:
                        return [parts[1]]  # Language is usually the second part
                return ["en"]  # Default to English
        except Exception as e:
            logger.debug(f"Could not load model {model_name} to check languages: {e}")
            # Fallback: extract from model name
            if "/" in model_name:
                parts = model_name.split("/")
                if len(parts) >= 2:
                    return [parts[1]]
            return ["en"]
            
    except ImportError:
        logger.warning("TTS package not available for language detection")
        return ["en"]
    except Exception as e:
        logger.error(f"Error getting languages for model {model_name}: {e}")
        return ["en"]


def get_coqui_model_info(model_name: str):
    """Get detailed information about a Coqui TTS model."""
    try:
        from TTS.api import TTS
        
        info = {
            "is_multi_speaker": False,
            "is_multi_lingual": False,
            "speakers": [],
            "languages": [],
            "supports_voice_cloning": False,
            "model_type": "single"
        }
        
        if "xtts" in model_name.lower():
            info.update({
                "is_multi_speaker": True,
                "is_multi_lingual": True,
                "supports_voice_cloning": True,
                "model_type": "xtts",
                "speakers": get_coqui_supported_voices(model_name),
                "languages": get_coqui_supported_languages_for_model(model_name)
            })
            return info
        
        if "your_tts" in model_name.lower():
            info.update({
                "is_multi_speaker": True,
                "is_multi_lingual": True,
                "supports_voice_cloning": True,
                "model_type": "your_tts"
            })
        
        # Try to get actual model info
        try:
            tts = TTS(model_name)
            info.update({
                "is_multi_speaker": tts.is_multi_speaker,
                "is_multi_lingual": tts.is_multi_lingual,
                "speakers": tts.speakers if tts.is_multi_speaker else ["Default"],
                "languages": tts.languages if tts.is_multi_lingual else get_coqui_supported_languages_for_model(model_name)
            })
        except Exception as e:
            logger.debug(f"Could not load model {model_name} for info: {e}")
            # Fallback info based on model name
            info["speakers"] = get_coqui_supported_voices(model_name)
            info["languages"] = get_coqui_supported_languages_for_model(model_name)
        
        return info
        
    except ImportError:
        logger.warning("TTS package not available for model info")
        return {
            "is_multi_speaker": False,
            "is_multi_lingual": False,
            "speakers": ["Default"],
            "languages": ["en"],
            "supports_voice_cloning": False,
            "model_type": "unknown"
        }
    except Exception as e:
        logger.error(f"Error getting model info for {model_name}: {e}")
        return {
            "is_multi_speaker": False,
            "is_multi_lingual": False,
            "speakers": ["Default"],
            "languages": ["en"],
            "supports_voice_cloning": False,
            "model_type": "unknown"
        }


def get_coqui_supported_output_formats():
    """Return supported output formats for Coqui TTS."""
    return ["mp3", "wav"]
