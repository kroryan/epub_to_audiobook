"""
Sistema Universal de Limpieza de Audio para TTS Locales
Elimina pops, clics, ruidos y artifacts entre chunks que son comunes en TTS locales
"""

import logging
import numpy as np
from pydub import AudioSegment
from typing import List, Tuple, Optional
import warnings

logger = logging.getLogger(__name__)


class UniversalAudioCleaner:
    """
    Sistema universal para limpiar audio de TTS locales y eliminar artifacts.
    Diseñado para funcionar con Coqui, Kokoro, Piper y cualquier TTS local.
    """
    
    def __init__(self, sample_rate: int = 44100, enable_aggressive_cleaning: bool = True):
        self.sample_rate = sample_rate
        self.enable_aggressive_cleaning = enable_aggressive_cleaning
        
        # Configuraciones específicas por tipo de TTS
        self.tts_configs = {
            'coqui': {
                'dc_removal': True,
                'high_freq_filter': True,
                'breath_removal': True,
                'fade_duration': 75,
                'silence_threshold': -40.0
            },
            'kokoro': {
                'dc_removal': True,
                'high_freq_filter': True,
                'breath_removal': True,
                'fade_duration': 100,
                'silence_threshold': -35.0,
                'aggressive_denoising': True
            },
            'piper': {
                'dc_removal': True,
                'high_freq_filter': False,  # Piper ya tiene buen filtrado
                'breath_removal': True,
                'fade_duration': 50,
                'silence_threshold': -45.0
            },
            'default': {
                'dc_removal': True,
                'high_freq_filter': True,
                'breath_removal': True,
                'fade_duration': 75,
                'silence_threshold': -40.0
            }
        }
    
    def clean_chunk_audio(self, audio: AudioSegment, chunk_index: int = 0, 
                         total_chunks: int = 1, tts_type: str = 'default') -> AudioSegment:
        """
        Limpia un chunk individual de audio eliminando artifacts comunes de TTS locales
        """
        try:
            config = self.tts_configs.get(tts_type, self.tts_configs['default'])
            
            # 1. Verificación básica
            if len(audio) < 50:  # Audio muy corto, no procesar
                return audio
            
            # 2. Detección y corrección de problemas comunes
            audio = self._detect_and_fix_common_issues(audio, config)
            
            # 3. Limpieza específica por posición
            is_first = (chunk_index == 0)
            is_last = (chunk_index == total_chunks - 1)
            audio = self._position_specific_cleaning(audio, is_first, is_last, config)
            
            # 4. Normalización inteligente
            audio = self._intelligent_normalization(audio, config)
            
            # 5. Aplicar fades inteligentes
            audio = self._apply_intelligent_fades(audio, is_first, is_last, config)
            
            logger.debug(f"Cleaned audio chunk {chunk_index + 1}/{total_chunks} "
                        f"(duration: {len(audio)}ms, type: {tts_type})")
            
            return audio
            
        except Exception as e:
            logger.warning(f"Error cleaning audio chunk {chunk_index}: {e}")
            return audio
    
    def _detect_and_fix_common_issues(self, audio: AudioSegment, config: dict) -> AudioSegment:
        """Detecta y corrige problemas comunes de TTS locales"""
        
        # 1. Remover DC offset (muy común en TTS locales)
        if config.get('dc_removal', True):
            audio = self._remove_dc_offset(audio)
        
        # 2. Detectar y corregir clipping
        audio = self._fix_clipping(audio)
        
        # 3. Detectar y remover pops/clics al inicio y final
        audio = self._remove_boundary_artifacts(audio)
        
        # 4. Filtrar ruido de alta frecuencia si es necesario
        if config.get('high_freq_filter', True):
            audio = self._apply_high_frequency_filter(audio)
        
        # 5. Remover respiraciones/ruidos si está habilitado
        if config.get('breath_removal', True):
            audio = self._remove_breath_artifacts(audio)
        
        return audio
    
    def _remove_dc_offset(self, audio: AudioSegment) -> AudioSegment:
        """Remueve DC offset que causa pops"""
        try:
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                # Remover DC offset por canal
                samples = samples - np.mean(samples, axis=0)
                samples = samples.flatten()
            else:
                # Remover DC offset
                samples = samples - np.mean(samples)
            
            # Evitar overflow
            samples = np.clip(samples, -32767, 32767)
            
            return audio._spawn(samples.astype(np.int16).tobytes())
            
        except Exception as e:
            logger.debug(f"Could not remove DC offset: {e}")
            return audio
    
    def _fix_clipping(self, audio: AudioSegment) -> AudioSegment:
        """Detecta y corrige clipping digital"""
        try:
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # Detectar clipping (valores en los extremos)
            clipping_threshold = 32000  # Cerca del máximo de 16-bit
            clipped_samples = np.abs(samples) >= clipping_threshold
            
            if np.any(clipped_samples):
                # Aplicar compresión suave a las áreas clipeadas
                compression_ratio = 0.9
                samples[clipped_samples] *= compression_ratio
                
                logger.debug("Fixed digital clipping in audio chunk")
                
                return audio._spawn(samples.astype(np.int16).tobytes())
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not fix clipping: {e}")
            return audio
    
    def _remove_boundary_artifacts(self, audio: AudioSegment) -> AudioSegment:
        """Remueve artifacts al inicio y final del chunk"""
        try:
            # Analizar primeros y últimos 50ms para detectar artifacts
            boundary_ms = min(50, len(audio) // 4)
            
            if len(audio) <= boundary_ms * 2:
                return audio
            
            start_section = audio[:boundary_ms]
            end_section = audio[-boundary_ms:]
            
            # Detectar pops/clics por cambios abruptos de volumen
            start_needs_fix = self._detect_sudden_volume_change(start_section, from_silence=True)
            end_needs_fix = self._detect_sudden_volume_change(end_section, from_silence=False)
            
            if start_needs_fix or end_needs_fix:
                # Aplicar fade-in/out muy corto para suavizar
                fade_duration = min(25, boundary_ms)
                if start_needs_fix and len(audio) > fade_duration:
                    audio = audio.fade_in(fade_duration)
                if end_needs_fix and len(audio) > fade_duration:
                    audio = audio.fade_out(fade_duration)
                
                logger.debug("Fixed boundary artifacts")
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not remove boundary artifacts: {e}")
            return audio
    
    def _detect_sudden_volume_change(self, audio_section: AudioSegment, from_silence: bool) -> bool:
        """Detecta cambios abruptos de volumen que indican pops/clics"""
        try:
            if len(audio_section) < 10:
                return False
            
            # Analizar primeros y últimos 10ms
            first_part = audio_section[:10]
            last_part = audio_section[-10:]
            
            first_dBFS = first_part.dBFS if first_part.dBFS > -60 else -60
            last_dBFS = last_part.dBFS if last_part.dBFS > -60 else -60
            
            # Detectar cambio abrupto (más de 15dB en 10ms)
            if from_silence:
                # Desde silencio: revisar si el audio arranca muy fuerte
                return first_dBFS > -25  # Audio arranca muy fuerte
            else:
                # Hacia silencio: revisar si termina abruptamente
                change = abs(last_dBFS - first_dBFS)
                return change > 15  # Cambio abrupto de más de 15dB
                
        except Exception:
            return False
    
    def _apply_high_frequency_filter(self, audio: AudioSegment) -> AudioSegment:
        """Aplica filtro pasa-bajos suave para remover artifacts de alta frecuencia"""
        try:
            if audio.frame_rate < 22050:  # No filtrar audio de baja calidad
                return audio
            
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # Filtro pasa-bajos muy suave (media móvil)
            window_size = 3  # Ventana muy pequeña para preservar calidad
            kernel = np.ones(window_size) / window_size
            
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                filtered = np.apply_along_axis(
                    lambda x: np.convolve(x, kernel, mode='same'), 
                    axis=0, arr=samples
                )
                filtered = filtered.flatten()
            else:
                filtered = np.convolve(samples, kernel, mode='same')
            
            # Preservar la energía del audio original
            original_rms = np.sqrt(np.mean(samples**2))
            filtered_rms = np.sqrt(np.mean(filtered**2))
            
            if filtered_rms > 0:
                filtered = filtered * (original_rms / filtered_rms)
            
            return audio._spawn(filtered.astype(np.int16).tobytes())
            
        except Exception as e:
            logger.debug(f"Could not apply high frequency filter: {e}")
            return audio
    
    def _remove_breath_artifacts(self, audio: AudioSegment) -> AudioSegment:
        """Remueve respiraciones y ruidos de fondo típicos de TTS locales"""
        try:
            # Los TTS locales a veces generan ruidos de fondo sutiles
            # Aplicar gate de ruido muy suave
            noise_gate_threshold = -50.0  # dBFS
            
            # Dividir en segmentos pequeños para análisis
            segment_duration = 100  # 100ms
            processed_segments = []
            
            for i in range(0, len(audio), segment_duration):
                segment = audio[i:i + segment_duration]
                
                if segment.dBFS < noise_gate_threshold:
                    # Segmento muy silencioso, reducir volumen gradualmente
                    reduction_factor = 0.3
                    segment = segment.apply_gain(20 * np.log10(reduction_factor))
                
                processed_segments.append(segment)
            
            # Recombinar segmentos
            if processed_segments:
                result = processed_segments[0]
                for segment in processed_segments[1:]:
                    result += segment
                return result
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not remove breath artifacts: {e}")
            return audio
    
    def _position_specific_cleaning(self, audio: AudioSegment, is_first: bool, 
                                  is_last: bool, config: dict) -> AudioSegment:
        """Limpieza específica según la posición del chunk"""
        try:
            silence_threshold = config.get('silence_threshold', -40.0)
            
            # Para primer chunk: remover silencio inicial excesivo
            if is_first:
                audio = self._trim_initial_silence(audio, silence_threshold)
            
            # Para último chunk: remover silencio final excesivo  
            if is_last:
                audio = self._trim_final_silence(audio, silence_threshold)
            
            # Para chunks intermedios: normalizar pausas
            if not is_first and not is_last:
                audio = self._normalize_intermediate_pauses(audio, silence_threshold)
            
            return audio
            
        except Exception as e:
            logger.debug(f"Error in position specific cleaning: {e}")
            return audio
    
    def _trim_initial_silence(self, audio: AudioSegment, threshold: float) -> AudioSegment:
        """Remueve silencio inicial excesivo manteniendo transición natural"""
        try:
            chunk_size = 10  # Analizar en chunks de 10ms
            start_point = 0
            
            # Buscar donde empieza el contenido real
            for i in range(0, min(500, len(audio)), chunk_size):  # Máximo 500ms
                chunk = audio[i:i + chunk_size]
                if chunk.dBFS > threshold:
                    start_point = max(0, i - 30)  # Dejar 30ms de padding
                    break
            
            if start_point > 0:
                audio = audio[start_point:]
                logger.debug(f"Trimmed {start_point}ms of initial silence")
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not trim initial silence: {e}")
            return audio
    
    def _trim_final_silence(self, audio: AudioSegment, threshold: float) -> AudioSegment:
        """Remueve silencio final excesivo manteniendo transición natural"""
        try:
            chunk_size = 10
            end_point = len(audio)
            
            # Buscar donde termina el contenido real
            for i in range(len(audio), max(0, len(audio) - 500), -chunk_size):
                chunk = audio[i - chunk_size:i]
                if chunk.dBFS > threshold:
                    end_point = min(len(audio), i + 30)  # Dejar 30ms de padding
                    break
            
            if end_point < len(audio):
                audio = audio[:end_point]
                logger.debug(f"Trimmed {len(audio) - end_point}ms of final silence")
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not trim final silence: {e}")
            return audio
    
    def _normalize_intermediate_pauses(self, audio: AudioSegment, threshold: float) -> AudioSegment:
        """Normaliza pausas internas para chunks intermedios"""
        try:
            # Para chunks intermedios, asegurar que no hay pausas muy largas internas
            # que podrían causar artifacts en la concatenación
            max_internal_pause = 300  # 300ms máximo de pausa interna
            
            # Detectar pausas largas internas
            silence_segments = self._detect_long_silences(audio, threshold, max_internal_pause)
            
            if silence_segments:
                # Acortar pausas excesivas
                audio = self._shorten_long_silences(audio, silence_segments, max_internal_pause)
                logger.debug(f"Normalized {len(silence_segments)} internal pauses")
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not normalize internal pauses: {e}")
            return audio
    
    def _detect_long_silences(self, audio: AudioSegment, threshold: float, 
                            max_duration: int) -> List[Tuple[int, int]]:
        """Detecta silencios largos que exceden el máximo permitido"""
        silences = []
        chunk_size = 50  # 50ms chunks para análisis
        silence_start = None
        
        try:
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i:i + chunk_size]
                is_silent = chunk.dBFS < threshold
                
                if is_silent and silence_start is None:
                    silence_start = i
                elif not is_silent and silence_start is not None:
                    silence_duration = i - silence_start
                    if silence_duration > max_duration:
                        silences.append((silence_start, i))
                    silence_start = None
            
            # Verificar si termina en silencio
            if silence_start is not None:
                silence_duration = len(audio) - silence_start
                if silence_duration > max_duration:
                    silences.append((silence_start, len(audio)))
            
            return silences
            
        except Exception:
            return []
    
    def _shorten_long_silences(self, audio: AudioSegment, silence_segments: List[Tuple[int, int]], 
                             target_duration: int) -> AudioSegment:
        """Acorta silencios largos al tiempo objetivo"""
        try:
            # Procesar de atrás hacia adelante para mantener posiciones válidas
            for start, end in reversed(silence_segments):
                current_duration = end - start
                if current_duration > target_duration:
                    # Reemplazar silencio largo con silencio más corto
                    new_silence = AudioSegment.silent(duration=target_duration)
                    audio = audio[:start] + new_silence + audio[end:]
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not shorten long silences: {e}")
            return audio
    
    def _intelligent_normalization(self, audio: AudioSegment, config: dict) -> AudioSegment:
        """Normalización inteligente que evita artifacts"""
        try:
            current_dBFS = audio.dBFS
            
            # No normalizar audio ya muy silencioso
            if current_dBFS < -50.0:
                return audio
            
            # Target más conservador para evitar artifacts
            target_dBFS = -18.0
            
            # Calcular cambio necesario
            change_needed = target_dBFS - current_dBFS
            
            # Limitar cambios drásticos que pueden introducir artifacts
            max_change = 8.0  # Máximo 8dB de cambio
            change_needed = np.clip(change_needed, -max_change, max_change)
            
            # Aplicar cambio gradual si es muy grande
            if abs(change_needed) > 4.0:
                # Aplicar en dos pasos para evitar artifacts
                first_change = change_needed * 0.6
                audio = audio.apply_gain(first_change)
                
                # Verificar si necesita segundo paso
                remaining_change = change_needed - first_change
                if abs(remaining_change) > 1.0:
                    audio = audio.apply_gain(remaining_change)
            else:
                audio = audio.apply_gain(change_needed)
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not apply intelligent normalization: {e}")
            return audio
    
    def _apply_intelligent_fades(self, audio: AudioSegment, is_first: bool, 
                               is_last: bool, config: dict) -> AudioSegment:
        """Aplica fades inteligentes basados en el contenido"""
        try:
            base_fade_duration = config.get('fade_duration', 75)
            
            # Calcular fade duration basado en contenido
            fade_in_duration = self._calculate_fade_duration(audio, is_fade_in=True, 
                                                           base_duration=base_fade_duration, 
                                                           is_boundary=is_first)
            fade_out_duration = self._calculate_fade_duration(audio, is_fade_in=False, 
                                                            base_duration=base_fade_duration, 
                                                            is_boundary=is_last)
            
            # Aplicar fades solo donde sea necesario
            if not is_first and fade_in_duration > 0:
                audio = audio.fade_in(fade_in_duration)
            
            if not is_last and fade_out_duration > 0:
                audio = audio.fade_out(fade_out_duration)
            
            return audio
            
        except Exception as e:
            logger.debug(f"Could not apply intelligent fades: {e}")
            return audio
    
    def _calculate_fade_duration(self, audio: AudioSegment, is_fade_in: bool, 
                               base_duration: int, is_boundary: bool) -> int:
        """Calcula duración de fade óptima basada en el contenido"""
        try:
            if len(audio) < base_duration * 2:
                return min(25, len(audio) // 4)  # Fade mínimo para audio corto
            
            # Analizar sección relevante
            if is_fade_in:
                analyze_section = audio[:base_duration * 2]
            else:
                analyze_section = audio[-base_duration * 2:]
            
            # Calcular variabilidad del audio
            dynamic_range = analyze_section.max_dBFS - analyze_section.dBFS
            
            # Ajustar fade basado en dinámica
            if dynamic_range > 15:  # Audio muy dinámico
                multiplier = 0.8
            elif dynamic_range > 8:  # Audio moderadamente dinámico
                multiplier = 1.0
            else:  # Audio plano
                multiplier = 1.2
            
            # Reducir fade para chunks boundary
            if is_boundary:
                multiplier *= 0.6
            
            calculated_duration = int(base_duration * multiplier)
            return max(10, min(calculated_duration, len(audio) // 4))
            
        except Exception:
            return base_duration // 2


# Funciones de utilidad para integración
def detect_tts_type(provider_name: str = "", model_name: str = "") -> str:
    """Detecta el tipo de TTS basado en el provider y modelo"""
    provider_lower = provider_name.lower()
    model_lower = model_name.lower()
    
    if "coqui" in provider_lower or "xtts" in model_lower:
        return "coqui"
    elif "kokoro" in provider_lower or "kokoro" in model_lower:
        return "kokoro"
    elif "piper" in provider_lower:
        return "piper"
    else:
        return "default"


def clean_audio_chunk(audio: AudioSegment, chunk_index: int = 0, 
                     total_chunks: int = 1, tts_type: str = "default",
                     sample_rate: int = 44100) -> AudioSegment:
    """
    Función de conveniencia para limpiar un chunk de audio
    """
    cleaner = UniversalAudioCleaner(sample_rate=sample_rate)
    return cleaner.clean_chunk_audio(audio, chunk_index, total_chunks, tts_type)