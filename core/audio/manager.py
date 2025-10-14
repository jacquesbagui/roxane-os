"""
Roxane OS - Audio Manager
Gestionnaire audio pour la reconnaissance et synthèse vocale
"""

import asyncio
import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger
import io
import tempfile
import os

from core.interfaces import IModule, ActionResult


@dataclass
class AudioConfig:
    """Configuration audio"""
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = 'float32'
    chunk_size: int = 1024


class AudioManager(IModule):
    """
    Gestionnaire audio
    
    Single Responsibility: Gestion de l'audio (enregistrement, lecture, synthèse)
    Dependency Inversion: Interface pour différents backends audio
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise le gestionnaire audio
        
        Args:
            config: Configuration audio
        """
        self.config = config or {}
        self.audio_config = AudioConfig(
            sample_rate=self.config.get('sample_rate', 16000),
            channels=self.config.get('channels', 1),
            dtype=self.config.get('dtype', 'float32'),
            chunk_size=self.config.get('chunk_size', 1024)
        )
        self.is_recording = False
        self.is_playing = False
        logger.info("Audio manager initialized")
    
    async def initialize(self) -> bool:
        """Initialise le gestionnaire audio"""
        try:
            # Vérifier la disponibilité des périphériques audio
            devices = sd.query_devices()
            logger.info(f"Found {len(devices)} audio devices")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio manager: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Nettoie les ressources audio"""
        if self.is_recording:
            await self.stop_recording()
        if self.is_playing:
            await self.stop_playing()
    
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """
        Exécute une action audio
        
        Args:
            action_type: Type d'action ('record', 'play', 'synthesize', 'devices')
            parameters: Paramètres de l'action
            
        Returns:
            ActionResult avec les résultats
        """
        try:
            if action_type == 'record':
                return await self._record_audio(parameters)
            elif action_type == 'play':
                return await self._play_audio(parameters)
            elif action_type == 'synthesize':
                return await self._synthesize_speech(parameters)
            elif action_type == 'devices':
                return await self._list_devices()
            elif action_type == 'stop_recording':
                return await self._stop_recording()
            elif action_type == 'stop_playing':
                return await self._stop_playing()
            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown action type: {action_type}"
                )
        except Exception as e:
            logger.error(f"Audio action failed: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )
    
    async def _record_audio(self, parameters: Dict[str, Any]) -> ActionResult:
        """Enregistre de l'audio"""
        duration = parameters.get('duration', 5.0)
        filename = parameters.get('filename', None)
        
        if self.is_recording:
            return ActionResult(
                success=False,
                error="Already recording"
            )
        
        try:
            self.is_recording = True
            
            # Enregistrer l'audio
            audio_data = await self._record_audio_data(duration)
            
            # Sauvegarder si un nom de fichier est fourni
            if filename:
                await self._save_audio(audio_data, filename)
            
            return ActionResult(
                success=True,
                data={
                    'duration': duration,
                    'sample_rate': self.audio_config.sample_rate,
                    'channels': self.audio_config.channels,
                    'filename': filename,
                    'data_length': len(audio_data)
                }
            )
        except Exception as e:
            self.is_recording = False
            return ActionResult(
                success=False,
                error=f"Recording failed: {e}"
            )
    
    async def _record_audio_data(self, duration: float) -> np.ndarray:
        """Enregistre les données audio"""
        def record_callback():
            return sd.rec(
                int(duration * self.audio_config.sample_rate),
                samplerate=self.audio_config.sample_rate,
                channels=self.audio_config.channels,
                dtype=self.audio_config.dtype
            )
        
        # Exécuter l'enregistrement dans un thread séparé
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, record_callback)
        
        # Attendre la fin de l'enregistrement
        await asyncio.sleep(duration)
        
        return audio_data
    
    async def _save_audio(self, audio_data: np.ndarray, filename: str) -> None:
        """Sauvegarde les données audio"""
        def save_callback():
            sf.write(filename, audio_data, self.audio_config.sample_rate)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, save_callback)
    
    async def _play_audio(self, parameters: Dict[str, Any]) -> ActionResult:
        """Joue de l'audio"""
        filename = parameters.get('filename', '')
        data = parameters.get('data', None)
        
        if self.is_playing:
            return ActionResult(
                success=False,
                error="Already playing"
            )
        
        if not filename and data is None:
            return ActionResult(
                success=False,
                error="Filename or data is required"
            )
        
        try:
            self.is_playing = True
            
            if filename:
                # Jouer depuis un fichier
                await self._play_audio_file(filename)
            else:
                # Jouer depuis des données
                await self._play_audio_data(data)
            
            return ActionResult(
                success=True,
                data={
                    'filename': filename,
                    'played': True
                }
            )
        except Exception as e:
            self.is_playing = False
            return ActionResult(
                success=False,
                error=f"Playback failed: {e}"
            )
    
    async def _play_audio_file(self, filename: str) -> None:
        """Joue un fichier audio"""
        def play_callback():
            data, sample_rate = sf.read(filename)
            sd.play(data, sample_rate)
            sd.wait()  # Attendre la fin de la lecture
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, play_callback)
    
    async def _play_audio_data(self, data: np.ndarray) -> None:
        """Joue des données audio"""
        def play_callback():
            sd.play(data, self.audio_config.sample_rate)
            sd.wait()  # Attendre la fin de la lecture
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, play_callback)
    
    async def _synthesize_speech(self, parameters: Dict[str, Any]) -> ActionResult:
        """Synthétise la parole"""
        text = parameters.get('text', '')
        voice = parameters.get('voice', 'default')
        speed = parameters.get('speed', 1.0)
        
        if not text:
            return ActionResult(
                success=False,
                error="Text is required"
            )
        
        try:
            # Pour l'instant, générer un signal de test
            # Dans une implémentation complète, utiliser TTS ou espeak
            audio_data = await self._generate_test_audio(text)
            
            return ActionResult(
                success=True,
                data={
                    'text': text,
                    'voice': voice,
                    'speed': speed,
                    'audio_data_length': len(audio_data),
                    'note': 'Test audio generated - TTS integration needed'
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Speech synthesis failed: {e}"
            )
    
    async def _generate_test_audio(self, text: str) -> np.ndarray:
        """Génère un signal audio de test"""
        def generate_callback():
            # Générer un signal sinusoïdal simple
            duration = len(text) * 0.1  # 100ms par caractère
            t = np.linspace(0, duration, int(duration * self.audio_config.sample_rate))
            frequency = 440  # La note A4
            signal = np.sin(2 * np.pi * frequency * t) * 0.3
            return signal
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, generate_callback)
    
    async def _list_devices(self) -> ActionResult:
        """Liste les périphériques audio"""
        try:
            devices = sd.query_devices()
            
            device_list = []
            for i, device in enumerate(devices):
                device_list.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate'],
                    'is_default_input': i == sd.default.device[0],
                    'is_default_output': i == sd.default.device[1]
                })
            
            return ActionResult(
                success=True,
                data={
                    'devices': device_list,
                    'default_input': sd.default.device[0],
                    'default_output': sd.default.device[1]
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to list devices: {e}"
            )
    
    async def _stop_recording(self) -> ActionResult:
        """Arrête l'enregistrement"""
        if not self.is_recording:
            return ActionResult(
                success=False,
                error="Not currently recording"
            )
        
        try:
            sd.stop()
            self.is_recording = False
            
            return ActionResult(
                success=True,
                data={'stopped': True}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to stop recording: {e}"
            )
    
    async def _stop_playing(self) -> ActionResult:
        """Arrête la lecture"""
        if not self.is_playing:
            return ActionResult(
                success=False,
                error="Not currently playing"
            )
        
        try:
            sd.stop()
            self.is_playing = False
            
            return ActionResult(
                success=True,
                data={'stopped': True}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to stop playing: {e}"
            )
    
    async def stop_recording(self) -> None:
        """Arrête l'enregistrement (méthode publique)"""
        if self.is_recording:
            sd.stop()
            self.is_recording = False
    
    async def stop_playing(self) -> None:
        """Arrête la lecture (méthode publique)"""
        if self.is_playing:
            sd.stop()
            self.is_playing = False
    
    def get_capabilities(self) -> List[str]:
        """Retourne les capacités du module"""
        return ['record', 'play', 'synthesize', 'devices', 'stop_recording', 'stop_playing']
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        return {
            'name': 'AudioManager',
            'version': '1.0.0',
            'description': 'Gestionnaire audio pour reconnaissance et synthèse vocale',
            'capabilities': self.get_capabilities(),
            'config': {
                'sample_rate': self.audio_config.sample_rate,
                'channels': self.audio_config.channels,
                'dtype': self.audio_config.dtype
            }
        }
