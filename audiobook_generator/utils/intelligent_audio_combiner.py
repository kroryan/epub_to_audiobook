"""
Sistema Avanzado de Combinación de Audio con Prevención de Duplicación
y Transiciones Inteligentes para TTS Locales
"""

import logging
import numpy as np
from pydub import AudioSegment
from typing import List, Tuple, Optional, Dict, Any
import hashlib
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntelligentAudioCombiner:
    """
    Sistema avanzado para combinar chunks de audio con:
    - Prevención de duplicación de chunks
    - Transiciones inteligentes
    - Crossfades adaptativos
    - Validación de integridad
    """
    
    def __init__(self, tts_type: str = "default"):
        self.tts_type = tts_type
        self.processed_chunks = {}  # Cache de chunks procesados
        self.chunk_hashes = set()   # Para detectar duplicación
        self.transition_cache = {}  # Cache de análisis de transiciones
        
        # Configuraciones por tipo de TTS
        self.configs = {
            'coqui': {
                'min_crossfade': 30,
                'max_crossfade': 120,
                'default_pause': 180,
                'transition_analysis': True,
                'duplicate_detection': True
            },
            'kokoro': {
                'min_crossfade': 50,
                'max_crossfade': 150,
                'default_pause': 200,
                'transition_analysis': True,
                'duplicate_detection': True,
                'aggressive_smoothing': True
            },
            'piper': {
                'min_crossfade': 25,
                'max_crossfade': 100,
                'default_pause': 150,
                'transition_analysis': True,
                'duplicate_detection': True
            },
            'default': {
                'min_crossfade': 30,
                'max_crossfade': 120,
                'default_pause': 180,
                'transition_analysis': True,
                'duplicate_detection': True
            }
        }
        
        self.config = self.configs.get(tts_type, self.configs['default'])
    
    def combine_audio_segments(self, audio_segments: List[AudioSegment], 
                             chunk_texts: List[str] = None,
                             validate_integrity: bool = True) -> AudioSegment:
        """
        Combina segmentos de audio con prevención de duplicación y transiciones inteligentes
        """
        if not audio_segments:
            raise ValueError("No audio segments provided")
        
        # 1. Filtrar y validar segmentos
        validated_segments = self._validate_and_filter_segments(
            audio_segments, chunk_texts, validate_integrity
        )
        
        if not validated_segments:
            raise ValueError("No valid audio segments after filtering")
        
        if len(validated_segments) == 1:
            return validated_segments[0]['audio']
        
        # 2. Análisis de transiciones entre segmentos
        transition_plan = self._analyze_all_transitions(validated_segments)
        
        # 3. Combinación inteligente con crossfades adaptativos
        combined_audio = self._intelligent_combine(validated_segments, transition_plan)
        
        # 4. Post-procesamiento final
        combined_audio = self._final_post_processing(combined_audio)
        
        logger.info(f"Successfully combined {len(validated_segments)} audio segments "
                   f"with intelligent transitions (final duration: {len(combined_audio)}ms)")
        
        return combined_audio
    
    def _validate_and_filter_segments(self, audio_segments: List[AudioSegment], 
                                    chunk_texts: List[str] = None,
                                    validate_integrity: bool = True) -> List[Dict[str, Any]]:
        """Valida segmentos y detecta duplicación"""
        validated = []
        
        for i, audio in enumerate(audio_segments):
            try:
                # Información del chunk
                chunk_info = {
                    'audio': audio,
                    'index': i,
                    'text': chunk_texts[i] if chunk_texts and i < len(chunk_texts) else "",
                    'duration': len(audio),
                    'is_silence': self._is_silence(audio)
                }
                
                # Skip chunks muy cortos o inválidos
                if len(audio) < 10:  # Menos de 10ms
                    logger.debug(f"Skipping chunk {i}: too short ({len(audio)}ms)")
                    continue
                
                # Detección de duplicación si está habilitada
                if self.config.get('duplicate_detection', True) and validate_integrity:
                    chunk_hash = self._calculate_audio_hash(audio)
                    if chunk_hash in self.chunk_hashes:
                        logger.warning(f"Detected duplicate chunk {i}, skipping")
                        continue
                    self.chunk_hashes.add(chunk_hash)
                    chunk_info['hash'] = chunk_hash
                
                # Análisis adicional del chunk
                chunk_info.update(self._analyze_chunk_properties(audio))
                
                validated.append(chunk_info)
                
            except Exception as e:
                logger.warning(f"Error validating chunk {i}: {e}")
                continue
        
        logger.info(f"Validated {len(validated)} out of {len(audio_segments)} audio segments")
        return validated
    
    def _calculate_audio_hash(self, audio: AudioSegment) -> str:
        """Calcula hash del audio para detectar duplicación"""
        try:
            # Usar propiedades del audio para generar hash
            audio_data = {
                'duration': len(audio),
                'channels': audio.channels,
                'frame_rate': audio.frame_rate,
                'max_dBFS': round(audio.max_dBFS, 2) if audio.max_dBFS > -60 else -60,
                'dBFS': round(audio.dBFS, 2) if audio.dBFS > -60 else -60,
            }
            
            # También usar una muestra del audio para mayor precisión
            if len(audio) > 100:
                # Tomar muestra del medio del audio
                sample_start = len(audio) // 2 - 50
                sample_end = len(audio) // 2 + 50
                sample = audio[sample_start:sample_end]
                
                # Añadir propiedades de la muestra
                audio_data.update({
                    'sample_max_dBFS': round(sample.max_dBFS, 2) if sample.max_dBFS > -60 else -60,
                    'sample_dBFS': round(sample.dBFS, 2) if sample.dBFS > -60 else -60,
                })
            
            # Generar hash
            data_string = json.dumps(audio_data, sort_keys=True)
            return hashlib.md5(data_string.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.debug(f"Could not calculate audio hash: {e}")
            # Fallback a hash simple
            return hashlib.md5(f"{len(audio)}_{audio.channels}_{audio.frame_rate}".encode()).hexdigest()[:16]
    
    def _analyze_chunk_properties(self, audio: AudioSegment) -> Dict[str, Any]:
        """Analiza propiedades del chunk para tomar decisiones inteligentes"""
        try:
            properties = {
                'volume_level': self._categorize_volume_level(audio.dBFS),
                'dynamic_range': audio.max_dBFS - audio.dBFS if audio.dBFS > -60 else 0,
                'has_leading_silence': self._has_boundary_silence(audio, at_start=True),
                'has_trailing_silence': self._has_boundary_silence(audio, at_start=False),
                'content_type': self._classify_content_type(audio)
            }
            
            return properties
            
        except Exception as e:
            logger.debug(f"Could not analyze chunk properties: {e}")
            return {
                'volume_level': 'medium',
                'dynamic_range': 0,
                'has_leading_silence': False,
                'has_trailing_silence': False,
                'content_type': 'speech'
            }
    
    def _categorize_volume_level(self, dBFS: float) -> str:
        """Categoriza el nivel de volumen"""
        if dBFS > -15:
            return 'loud'
        elif dBFS > -25:
            return 'medium'
        elif dBFS > -40:
            return 'quiet'
        else:
            return 'very_quiet'
    
    def _has_boundary_silence(self, audio: AudioSegment, at_start: bool) -> bool:
        """Detecta si hay silencio significativo al inicio o final"""
        try:
            check_duration = min(100, len(audio) // 4)  # Revisar hasta 100ms
            
            if at_start:
                check_section = audio[:check_duration]
            else:
                check_section = audio[-check_duration:]
            
            return check_section.dBFS < -45.0  # Umbral de silencio
            
        except Exception:
            return False
    
    def _classify_content_type(self, audio: AudioSegment) -> str:
        """Clasifica el tipo de contenido del audio"""
        try:
            # Análisis simple basado en características
            dynamic_range = audio.max_dBFS - audio.dBFS
            
            if dynamic_range > 20:
                return 'dynamic_speech'  # Habla con mucha variación
            elif dynamic_range > 10:
                return 'normal_speech'   # Habla normal
            elif dynamic_range > 5:
                return 'monotone_speech' # Habla monótona
            else:
                return 'near_silence'    # Casi silencio
                
        except Exception:
            return 'speech'
    
    def _is_silence(self, audio: AudioSegment) -> bool:
        """Detecta si un segmento es principalmente silencio"""
        return audio.dBFS < -50.0 or len(audio) < 50
    
    def _analyze_all_transitions(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analiza todas las transiciones entre segmentos consecutivos"""
        transitions = []
        
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]
            
            # Crear clave para cache
            cache_key = f"{current_segment.get('hash', i)}_{next_segment.get('hash', i+1)}"
            
            if cache_key in self.transition_cache:
                transition = self.transition_cache[cache_key]
            else:
                transition = self._analyze_single_transition(current_segment, next_segment)
                self.transition_cache[cache_key] = transition
            
            transitions.append(transition)
        
        return transitions
    
    def _analyze_single_transition(self, segment1: Dict[str, Any], 
                                 segment2: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza una transición específica entre dos segmentos"""
        audio1 = segment1['audio']
        audio2 = segment2['audio']
        
        # Analizar final del primer segmento
        end_section_duration = min(150, len(audio1) // 4)
        end_section = audio1[-end_section_duration:] if len(audio1) > end_section_duration else audio1
        
        # Analizar inicio del segundo segmento
        start_section_duration = min(150, len(audio2) // 4)
        start_section = audio2[:start_section_duration] if len(audio2) > start_section_duration else audio2
        
        # Análisis de compatibilidad
        volume_difference = abs(end_section.dBFS - start_section.dBFS)
        
        # Determinar tipo de transición
        if segment1['is_silence'] or segment2['is_silence']:
            transition_type = 'silence'
        elif volume_difference < 3:
            transition_type = 'smooth'
        elif volume_difference < 8:
            transition_type = 'moderate'
        else:
            transition_type = 'sharp'
        
        # Calcular crossfade óptimo
        crossfade_duration = self._calculate_optimal_crossfade(
            segment1, segment2, transition_type, volume_difference
        )
        
        # Determinar si necesita pausa adicional
        needs_pause = self._needs_additional_pause(segment1, segment2)
        pause_duration = self._calculate_pause_duration(segment1, segment2) if needs_pause else 0
        
        return {
            'type': transition_type,
            'volume_difference': volume_difference,
            'crossfade_duration': crossfade_duration,
            'needs_pause': needs_pause,
            'pause_duration': pause_duration,
            'compatibility_score': self._calculate_compatibility_score(
                volume_difference, segment1, segment2
            )
        }
    
    def _calculate_optimal_crossfade(self, segment1: Dict[str, Any], segment2: Dict[str, Any],
                                   transition_type: str, volume_difference: float) -> int:
        """Calcula la duración óptima de crossfade"""
        base_duration = {
            'silence': 0,      # No crossfade con silencio
            'smooth': self.config['min_crossfade'],
            'moderate': (self.config['min_crossfade'] + self.config['max_crossfade']) // 2,
            'sharp': self.config['max_crossfade']
        }.get(transition_type, self.config['min_crossfade'])
        
        # Ajustar según diferencia de volumen
        volume_factor = min(2.0, volume_difference / 5.0)  # Factor de 1.0 a 2.0
        adjusted_duration = int(base_duration * volume_factor)
        
        # Limitar según duración de los segmentos
        min_segment_duration = min(len(segment1['audio']), len(segment2['audio']))
        max_allowed = min_segment_duration // 4  # Máximo 25% del segmento más corto
        
        return max(0, min(adjusted_duration, max_allowed))
    
    def _needs_additional_pause(self, segment1: Dict[str, Any], segment2: Dict[str, Any]) -> bool:
        """Determina si necesita pausa adicional entre segmentos"""
        # Necesita pausa si:
        # 1. El primer segmento no termina en silencio
        # 2. El segundo no empieza en silencio
        # 3. Los volúmenes son muy diferentes
        # 4. Es una transición entre diferentes tipos de contenido
        
        return (not segment1['has_trailing_silence'] and 
                not segment2['has_leading_silence'] and
                not segment1['is_silence'] and 
                not segment2['is_silence'])
    
    def _calculate_pause_duration(self, segment1: Dict[str, Any], segment2: Dict[str, Any]) -> int:
        """Calcula duración de pausa adicional si es necesaria"""
        base_pause = self.config['default_pause']
        
        # Ajustar según características de los segmentos
        if segment1['content_type'] == 'dynamic_speech' or segment2['content_type'] == 'dynamic_speech':
            return int(base_pause * 1.2)  # Pausa más larga para habla dinámica
        elif segment1['volume_level'] == 'loud' and segment2['volume_level'] == 'quiet':
            return int(base_pause * 1.3)  # Pausa más larga para cambios de volumen grandes
        elif segment1['content_type'] != segment2['content_type']:
            return int(base_pause * 1.1)  # Pausa ligeramente más larga para cambios de contenido
        else:
            return base_pause
    
    def _calculate_compatibility_score(self, volume_difference: float, 
                                     segment1: Dict[str, Any], segment2: Dict[str, Any]) -> float:
        """Calcula un score de compatibilidad entre segmentos (0.0 a 1.0)"""
        score = 1.0
        
        # Penalizar diferencias de volumen
        score -= min(0.4, volume_difference / 20.0)
        
        # Penalizar cambios de tipo de contenido
        if segment1['content_type'] != segment2['content_type']:
            score -= 0.1
        
        # Bonus por silencios naturales
        if segment1['has_trailing_silence'] or segment2['has_leading_silence']:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _intelligent_combine(self, segments: List[Dict[str, Any]], 
                           transitions: List[Dict[str, Any]]) -> AudioSegment:
        """Combina segmentos usando análisis de transiciones"""
        if not segments:
            raise ValueError("No segments to combine")
        
        result = segments[0]['audio']
        
        for i, transition in enumerate(transitions):
            next_segment = segments[i + 1]['audio']
            
            # Aplicar pausa si es necesaria
            if transition['needs_pause'] and transition['pause_duration'] > 0:
                pause = AudioSegment.silent(duration=transition['pause_duration'])
                result += pause
            
            # Aplicar crossfade inteligente
            if transition['crossfade_duration'] > 0 and not segments[i + 1]['is_silence']:
                result = self._apply_intelligent_crossfade(
                    result, next_segment, transition
                )
            else:
                # Concatenación simple para silencios o crossfade = 0
                result += next_segment
            
            logger.debug(f"Applied {transition['type']} transition "
                        f"(crossfade: {transition['crossfade_duration']}ms, "
                        f"pause: {transition['pause_duration']}ms)")
        
        return result
    
    def _apply_intelligent_crossfade(self, audio1: AudioSegment, audio2: AudioSegment,
                                   transition: Dict[str, Any]) -> AudioSegment:
        """Aplica crossfade inteligente basado en análisis de transición"""
        crossfade_duration = transition['crossfade_duration']
        transition_type = transition['type']
        
        try:
            if (crossfade_duration <= 0 or 
                len(audio1) < crossfade_duration or 
                len(audio2) < crossfade_duration):
                return audio1 + audio2
            
            if transition_type == 'smooth':
                # Crossfade lineal para transiciones suaves
                return audio1.append(audio2, crossfade=crossfade_duration)
            
            elif transition_type == 'moderate':
                # Crossfade con curva suave
                return self._curved_crossfade(audio1, audio2, crossfade_duration)
            
            elif transition_type == 'sharp':
                # Crossfade más agresivo con pre-procesamiento
                return self._aggressive_crossfade(audio1, audio2, crossfade_duration)
            
            else:
                # Fallback
                return audio1.append(audio2, crossfade=crossfade_duration)
                
        except Exception as e:
            logger.warning(f"Crossfade failed: {e}, using simple concatenation")
            return audio1 + audio2
    
    def _curved_crossfade(self, audio1: AudioSegment, audio2: AudioSegment, duration: int) -> AudioSegment:
        """Crossfade con curva de atenuación suave"""
        try:
            # Preparar secciones para crossfade
            fade_out_section = audio1[-duration:]
            fade_in_section = audio2[:duration]
            
            # Aplicar fades con curva exponencial
            fade_out_section = fade_out_section.fade_out(duration)
            fade_in_section = fade_in_section.fade_in(duration)
            
            # Combinar con overlay balanceado
            combined_section = fade_out_section.overlay(fade_in_section)
            
            # Reconstruir audio completo
            return audio1[:-duration] + combined_section + audio2[duration:]
            
        except Exception:
            return audio1.append(audio2, crossfade=duration)
    
    def _aggressive_crossfade(self, audio1: AudioSegment, audio2: AudioSegment, duration: int) -> AudioSegment:
        """Crossfade agresivo para transiciones difíciles"""
        try:
            # Pre-procesar las zonas de transición
            transition_zone1 = audio1[-duration * 2:-duration] if len(audio1) > duration * 2 else AudioSegment.empty()
            transition_zone2 = audio2[duration:duration * 2] if len(audio2) > duration * 2 else AudioSegment.empty()
            
            # Aplicar compresión suave en las zonas de transición
            if len(transition_zone1) > 0:
                try:
                    transition_zone1 = transition_zone1.compress_dynamic_range(
                        threshold=-20.0, ratio=2.0, attack=5.0, release=50.0
                    )
                    audio1 = audio1[:-duration * 2] + transition_zone1 + audio1[-duration:]
                except:
                    pass  # Si falla la compresión, usar audio original
            
            if len(transition_zone2) > 0:
                try:
                    transition_zone2 = transition_zone2.compress_dynamic_range(
                        threshold=-20.0, ratio=2.0, attack=5.0, release=50.0
                    )
                    audio2 = audio2[:duration] + transition_zone2 + audio2[duration * 2:]
                except:
                    pass
            
            # Aplicar crossfade normal después del pre-procesamiento
            return audio1.append(audio2, crossfade=duration)
            
        except Exception:
            return audio1.append(audio2, crossfade=duration)
    
    def _final_post_processing(self, audio: AudioSegment) -> AudioSegment:
        """Post-procesamiento final del audio combinado"""
        try:
            # 1. Normalización final muy suave
            if audio.dBFS > -50:  # Solo si hay contenido real
                target_dBFS = -18.0
                current_dBFS = audio.dBFS
                gain_change = target_dBFS - current_dBFS
                
                # Limitar cambios drásticos
                if abs(gain_change) <= 6.0:
                    audio = audio.apply_gain(gain_change)
            
            # 2. Limiter final suave para evitar clipping
            if audio.max_dBFS > -3.0:
                try:
                    audio = audio.compress_dynamic_range(
                        threshold=-10.0,
                        ratio=3.0,
                        attack=1.0,
                        release=20.0
                    )
                except:
                    # Si falla la compresión, aplicar gain simple
                    if audio.max_dBFS > -1.0:
                        reduction = -1.0 - audio.max_dBFS
                        audio = audio.apply_gain(reduction)
            
            # 3. Fades muy sutiles en los extremos
            if len(audio) > 100:
                audio = audio.fade_in(20).fade_out(20)
            
            logger.debug(f"Final post-processing completed (duration: {len(audio)}ms)")
            return audio
            
        except Exception as e:
            logger.warning(f"Final post-processing failed: {e}")
            return audio


# Función de utilidad para usar el combiner
def combine_audio_intelligently(audio_segments: List[AudioSegment], 
                              chunk_texts: List[str] = None,
                              tts_type: str = "default") -> AudioSegment:
    """
    Función de conveniencia para combinar audio inteligentemente
    """
    combiner = IntelligentAudioCombiner(tts_type=tts_type)
    return combiner.combine_audio_segments(audio_segments, chunk_texts)