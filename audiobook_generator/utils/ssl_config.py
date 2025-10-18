"""
Configuración automática SSL para Coqui TTS
Este módulo resuelve automáticamente problemas de certificados SSL
que ocurren en PC nuevos al descargar modelos de Hugging Face.
"""

import os
import ssl
import warnings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SSLConfigManager:
    """Gestor de configuración SSL para evitar errores de certificado"""
    
    def __init__(self):
        self.original_ssl_context = None
        self.ssl_configured = False
    
    def setup_ssl_environment(self) -> bool:
        """
        Configura el entorno SSL para evitar errores de certificado.
        
        Returns:
            bool: True si la configuración fue exitosa
        """
        try:
            # 1. Configurar variables de entorno SSL/TLS
            ssl_env_vars = {
                'PYTHONHTTPSVERIFY': '0',
                'CURL_CA_BUNDLE': '',
                'REQUESTS_CA_BUNDLE': '',
                'SSL_VERIFY': 'false',
                'HF_HUB_DISABLE_TELEMETRY': '1',
                'HF_HUB_DISABLE_PROGRESS_BARS': '1',
                'TRANSFORMERS_VERBOSITY': 'error',
                'TF_CPP_MIN_LOG_LEVEL': '2',
                'TOKENIZERS_PARALLELISM': 'false',
                # Variables para licencia Coqui automática
                'COQUI_TOS': 'AGREED',
                'TTS_AGREE_LICENSE': 'yes',
                'COQUI_AGREE_LICENSE': '1'
            }
            
            for key, value in ssl_env_vars.items():
                os.environ[key] = value
            
            # 2. Configurar SSL context global
            if not self.original_ssl_context:
                self.original_ssl_context = ssl._create_default_https_context
            
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # 3. Configurar warnings
            self._suppress_ssl_warnings()
            
            # 4. Configurar requests si está disponible
            self._configure_requests()
            
            self.ssl_configured = True
            logger.info("🔧 Configuración SSL aplicada correctamente")
            return True
            
        except Exception as e:
            logger.warning(f"Error configurando SSL: {e}")
            return False
    
    def _suppress_ssl_warnings(self):
        """Suprimir warnings relacionados con SSL"""
        try:
            import urllib3
            from urllib3.exceptions import InsecureRequestWarning
            
            urllib3.disable_warnings(InsecureRequestWarning)
            
            # Suprimir warnings específicos
            warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
            warnings.filterwarnings('ignore', message='.*SSL.*', category=UserWarning)
            warnings.filterwarnings('ignore', message='.*certificate.*', category=UserWarning)
            warnings.filterwarnings('ignore', message='.*unverified.*', category=UserWarning)
            
        except ImportError:
            # urllib3 no disponible
            pass
    
    def _configure_requests(self):
        """Configurar requests para ignorar verificación SSL"""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            import urllib3
            
            # Crear session global con SSL deshabilitado
            session = requests.Session()
            session.verify = False
            
            # Configurar retry strategy (adaptado para nuevas versiones de urllib3)
            try:
                # Nuevo formato para urllib3 2.0+
                retry_strategy = Retry(
                    total=3,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["HEAD", "GET", "OPTIONS"],  # Nuevo parámetro
                    backoff_factor=1
                )
            except TypeError:
                try:
                    # Formato anterior para urllib3 1.x
                    retry_strategy = Retry(
                        total=3,
                        status_forcelist=[429, 500, 502, 503, 504],
                        method_whitelist=["HEAD", "GET", "OPTIONS"],  # Formato anterior
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
            
            # Headers estándar
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
        except ImportError:
            # requests no disponible
            pass
        except Exception as e:
            logger.debug(f"Error configurando requests: {e}")
    
    def restore_ssl_context(self):
        """Restaurar configuración SSL original"""
        if self.original_ssl_context:
            ssl._create_default_https_context = self.original_ssl_context
            self.ssl_configured = False
    
    def is_ssl_error(self, error: Exception) -> bool:
        """Detectar si un error está relacionado con SSL/certificados"""
        error_msg = str(error).lower()
        ssl_keywords = [
            'ssl', 'certificate', 'handshake', 'tls', 
            'cert', 'connection reset', 'connection aborted',
            'max retries exceeded', 'certificate verify failed'
        ]
        
        return any(keyword in error_msg for keyword in ssl_keywords)
    
    def provide_troubleshooting_info(self, error: Exception):
        """Proporcionar información de troubleshooting para errores SSL"""
        logger.error("🚨 ERROR DE CERTIFICADO SSL DETECTADO 🚨")
        logger.error("=" * 60)
        logger.error("Este error es común en PC nuevos o redes corporativas.")
        logger.error("")
        logger.error("SOLUCIONES AUTOMÁTICAS APLICADAS:")
        logger.error("✅ Configuración SSL permisiva activada")
        logger.error("✅ Variables de entorno SSL configuradas")
        logger.error("✅ Warnings SSL suprimidos")
        logger.error("")
        logger.error("SI EL PROBLEMA PERSISTE:")
        logger.error("")
        logger.error("1. 🌐 VERIFICAR INTERNET:")
        logger.error("   - Prueba abrir https://huggingface.co en el navegador")
        logger.error("")
        logger.error("2. 🔥 FIREWALL/ANTIVIRUS:")
        logger.error("   - Deshabilitar temporalmente")
        logger.error("   - Agregar excepción para Python")
        logger.error("")
        logger.error("3. 🏢 RED CORPORATIVA:")
        logger.error("   - Configurar proxy si es necesario")
        logger.error("   - Contactar IT para acceso a huggingface.co")
        logger.error("")
        logger.error("4. 📱 HOTSPOT MÓVIL (último recurso):")
        logger.error("   - Usar datos móviles para la primera descarga")
        logger.error("")
        logger.error("5. 🔄 REINSTALAR CERTIFICADOS:")
        logger.error("   - Ejecutar: scripts/install_coqui_ssl_fix.ps1")
        logger.error("")
        logger.error(f"Error técnico: {error}")
        logger.error("=" * 60)


# Instancia global del gestor SSL
ssl_manager = SSLConfigManager()

def auto_configure_ssl():
    """Configurar SSL automáticamente (función de conveniencia)"""
    return ssl_manager.setup_ssl_environment()

def is_ssl_error(error: Exception) -> bool:
    """Detectar errores SSL (función de conveniencia)"""
    return ssl_manager.is_ssl_error(error)

def provide_ssl_help(error: Exception):
    """Mostrar ayuda para errores SSL (función de conveniencia)"""
    ssl_manager.provide_troubleshooting_info(error)

# Configurar SSL automáticamente al importar este módulo
if __name__ != "__main__":
    auto_configure_ssl()