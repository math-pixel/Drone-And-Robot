import pygame


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
    
    def load(self, name: str, path: str):
        """Load an audio file and assign it a name."""
        try:
            self.sounds[name] = pygame.mixer.Sound(path)
            print(f"✓ Sound '{name}' loaded from {path}")
        except Exception as e:
            print(f"✗ Error loading '{name}': {e}")
    
    def load_multiple(self, files: dict):
        """Load multiple audio files.
        
        Args:
            files: {"name": "path/to/file.wav", ...}
        """
        for name, path in files.items():
            self.load(name, path)
    
    def play(self, name: str, volume: float = 1.0, loop: bool = False):
        """Play a sound with specified volume.
        
        Args:
            name: Name of the sound to play
            volume: Volume between 0.0 and 1.0
            loop: True to loop indefinitely
        
        Returns:
            The channel playing the sound, or None if error
        """
        if name not in self.sounds:
            print(f"✗ Sound '{name}' not found")
            return None
        
        sound = self.sounds[name]
        sound.set_volume(max(0.0, min(1.0, volume)))  # Clamp between 0 and 1
        
        loops = -1 if loop else 0
        channel = sound.play(loops=loops)
        self.channels[name] = channel
        
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
        self.unload_all()
        pygame.mixer.quit()


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    import time
    
    # Create player
    player = AudioPlayer()
    
    # Load multiple sounds at once
    player.load_multiple({
        "music": "music.wav",
        "explosion": "explosion.wav",
        "jump": "jump.wav"
    })
    
    # Or load one by one
    player.load("faux", "./utils/faux.mp3")
    
    # Display loaded sounds
    player.list_sounds()
    
    # Play with different volumes
    player.play("music", volume=0.3, loop=True)  # Background music at 30%
    
    time.sleep(2)
    
    player.play("faux", volume=0.8)  # Sound effect at 80%
    
    time.sleep(1)
    
    # Change volume while playing
    player.set_volume("music", 0.5)
    print(f"Music volume: {player.get_volume('music'):.0%}")
    
    # Check if playing
    print(f"Music is playing: {player.is_playing('music')}")
    
    time.sleep(2)
    
    # Pause and resume
    player.pause("music")
    time.sleep(1)
    player.resume("music")
    
    time.sleep(2)
    
    # Stop and cleanup
    player.stop_all()
    player.close()