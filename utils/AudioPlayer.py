import pygame
import threading


class AudioPlayer:
    def __init__(self, buffer_size: int = 512):
        """Initialize audio player with low latency."""
        pygame.mixer.pre_init(
            frequency=44100,
            size=-16,
            channels=2,
            buffer=buffer_size
        )
        pygame.mixer.init()
        self.sounds = {}    # Dictionary to store sounds
        self.channels = {}  # Channels to control each sound
        
        # NOUVEAU : Callback système
        self.on_sound_finished = None  # Callback quand un son finit
        self._current_sound_name = None
        self._monitoring = False
        self._monitor_thread = None
    
    def set_on_finished_callback(self, callback):
        """Définit la callback appelée quand un son finit.
        
        Args:
            callback: Fonction qui reçoit le nom du son terminé
        """
        self.on_sound_finished = callback
    
    def _start_monitoring(self, name: str):
        """Lance la surveillance de fin de son"""
        self._current_sound_name = name
        
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_sound, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_sound(self):
        """Surveille si le son est terminé et appelle la callback"""
        import time
        while self._monitoring:
            if self._current_sound_name:
                if not self.is_playing(self._current_sound_name):
                    # Son terminé
                    finished_name = self._current_sound_name
                    self._current_sound_name = None
                    
                    # Appeler la callback
                    if self.on_sound_finished:
                        self.on_sound_finished(finished_name)
                    
                    # Arrêter la surveillance si plus de son
                    if not self._current_sound_name:
                        self._monitoring = False
                        return
            
            time.sleep(0.05)  # Vérifier toutes les 50ms
    
    def load(self, name: str, path: str):
        """Load an audio file and assign it a name."""
        try:
            self.sounds[name] = pygame.mixer.Sound(path)
            print(f"✓ Sound '{name}' loaded from {path}")
        except Exception as e:
            print(f"✗ Error loading '{name}': {e}")
    
    def load_multiple(self, files: dict):
        """Load multiple audio files."""
        for name, path in files.items():
            self.load(name, path)
    
    def play(self, name: str, volume: float = 1.0, loop: bool = False, notify_on_finish: bool = True):
        """Play a sound with specified volume.
        
        Args:
            name: Name of the sound to play
            volume: Volume between 0.0 and 1.0
            loop: True to loop indefinitely
            notify_on_finish: True to trigger callback when finished
        
        Returns:
            The channel playing the sound, or None if error
        """
        if name not in self.sounds:
            print(f"✗ Sound '{name}' not found")
            return None
        
        sound = self.sounds[name]
        sound.set_volume(max(0.0, min(1.0, volume)))
        
        loops = -1 if loop else 0
        channel = sound.play(loops=loops)
        self.channels[name] = channel
        
        # NOUVEAU : Démarrer la surveillance si callback demandée
        if notify_on_finish and not loop and self.on_sound_finished:
            self._start_monitoring(name)
        
        return channel
    
    def set_volume(self, name: str, volume: float):
        """Change volume of a sound (even while playing)."""
        if name in self.sounds:
            self.sounds[name].set_volume(max(0.0, min(1.0, volume)))
    
    def set_global_volume(self, volume: float):
        """Change volume of all sounds."""
        for name in self.sounds:
            self.set_volume(name, volume)
    
    def stop(self, name: str):
        """Stop a specific sound."""
        if name in self.channels and self.channels[name]:
            self.channels[name].stop()
    
    def stop_all(self):
        """Stop all sounds."""
        pygame.mixer.stop()
    
    def pause(self, name: str):
        """Pause a sound."""
        if name in self.channels and self.channels[name]:
            self.channels[name].pause()
    
    def resume(self, name: str):
        """Resume a paused sound."""
        if name in self.channels and self.channels[name]:
            self.channels[name].unpause()
    
    def is_playing(self, name: str) -> bool:
        """Check if a sound is currently playing."""
        if name in self.channels and self.channels[name]:
            return self.channels[name].get_busy()
        return False
    
    def is_any_playing(self) -> bool:
        """Check if any sound is currently playing."""
        return pygame.mixer.get_busy()
    
    def get_volume(self, name: str) -> float:
        """Get current volume of a sound."""
        if name in self.sounds:
            return self.sounds[name].get_volume()
        return 0.0
    
    def get_duration(self, name: str) -> float:
        """Get duration of a sound in seconds."""
        if name in self.sounds:
            return self.sounds[name].get_length()
        return 0.0
    
    def list_sounds(self):
        """Display all loaded sounds."""
        print("\n🎵 Loaded sounds:")
        for name, sound in self.sounds.items():
            volume = sound.get_volume()
            duration = sound.get_length()
            print(f"   - {name}: {duration:.2f}s, volume: {volume:.0%}")
    
    def unload(self, name: str):
        """Unload a specific sound from memory."""
        if name in self.sounds:
            self.stop(name)
            del self.sounds[name]
            if name in self.channels:
                del self.channels[name]
            print(f"✓ Sound '{name}' unloaded")
    
    def unload_all(self):
        """Unload all sounds from memory."""
        self.stop_all()
        self.sounds.clear()
        self.channels.clear()
    
    def close(self):
        """Release audio resources."""
        self._monitoring = False
        self.unload_all()
        pygame.mixer.quit()