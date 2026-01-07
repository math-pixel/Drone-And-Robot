import vlc
import threading
from typing import Dict, Callable, Optional


class VideoPlayer:
    """Lecteur vidéo simple pour Raspberry Pi"""
    
    def __init__(self, fullscreen: bool = True):
        # Options VLC optimisées pour Raspberry Pi
        options = [
            '--no-xlib',           # Évite les warnings X11
            '--aout=alsa',         # Sortie audio ALSA
        ]
        if fullscreen:
            options.append('--fullscreen')
        
        self._instance = vlc.Instance(' '.join(options))
        self._player = self._instance.media_player_new()
        self._videos: Dict[str, str] = {}
        self._on_finished_callback: Optional[Callable[[str], None]] = None
        self._current_video_id: Optional[str] = None
        self._lock = threading.Lock()
        
        # Attacher l'événement de fin de vidéo
        event_manager = self._player.event_manager()
        event_manager.event_attach(
            vlc.EventType.MediaPlayerEndReached, 
            self._handle_end
        )
    
    def load(self, videos: Dict[str, str]) -> None:
        """
        Charge un dictionnaire de vidéos.
        
        Args:
            videos: Dict avec {id: chemin_fichier}
            
        Exemple:
            player.load({
                "intro": "/home/pi/videos/intro.mp4",
                "main": "/home/pi/videos/main.mp4",
                "outro": "/home/pi/videos/outro.mp4"
            })
        """
        with self._lock:
            self._videos.update(videos)
            print(f"✓ {len(videos)} vidéo(s) chargée(s)")
    
    def play(self, video_id: str) -> bool:
        """
        Joue une vidéo par son ID.
        
        Args:
            video_id: L'identifiant de la vidéo à jouer
            
        Returns:
            True si la lecture a démarré, False sinon
        """
        with self._lock:
            if video_id not in self._videos:
                print(f"✗ Vidéo '{video_id}' non trouvée")
                return False
            
            path = self._videos[video_id]
        
        # Arrêter la vidéo en cours si nécessaire
        self.stop()
        
        # Créer et jouer le nouveau média
        media = self._instance.media_new(path)
        self._player.set_media(media)
        self._current_video_id = video_id
        self._player.play()
        
        print(f"▶ Lecture: {video_id}")
        return True
    
    def stop(self) -> None:
        """Arrête la lecture en cours."""
        self._player.stop()
        self._current_video_id = None
    
    def pause(self) -> None:
        """Met en pause / reprend la lecture."""
        self._player.pause()
    
    def set_volume(self, volume: int) -> None:
        """
        Règle le volume (0-100).
        """
        self._player.audio_set_volume(max(0, min(100, volume)))
    
    def is_playing(self) -> bool:
        """Retourne True si une vidéo est en cours de lecture."""
        return self._player.is_playing()
    
    def get_position(self) -> float:
        """Retourne la position actuelle (0.0 à 1.0)."""
        return self._player.get_position()
    
    def on_finished(self, callback: Callable[[str], None]) -> None:
        """
        Définit le callback appelé quand une vidéo se termine.
        
        Args:
            callback: Fonction appelée avec l'ID de la vidéo terminée
            
        Exemple:
            player.on_finished(lambda vid_id: print(f"{vid_id} terminée!"))
        """
        self._on_finished_callback = callback
    
    def _handle_end(self, event) -> None:
        """Handler interne pour la fin de vidéo."""
        video_id = self._current_video_id
        self._current_video_id = None
        
        if self._on_finished_callback and video_id:
            # Appeler le callback dans un thread séparé pour éviter les deadlocks
            threading.Thread(
                target=self._on_finished_callback,
                args=(video_id,),
                daemon=True
            ).start()
    
    def list_videos(self) -> list:
        """Retourne la liste des IDs de vidéos chargées."""
        return list(self._videos.keys())
    
    def release(self) -> None:
        """Libère les ressources."""
        self.stop()
        self._player.release()


if __name__ == "__main__":

    import time

def main():
    # Créer le lecteur
    player = VideoPlayer(fullscreen=True)
    
    # Charger les vidéos
    player.load({
        "intro": "/home/pi/videos/intro.mp4",
        "presentation": "/home/pi/videos/presentation.mp4",
        "credits": "/home/pi/videos/credits.mp4"
    })
    
    # Définir le callback de fin
    def on_video_end(video_id: str):
        print(f"✓ Vidéo '{video_id}' terminée!")
        
        # Exemple: enchaîner les vidéos
        if video_id == "intro":
            player.play("presentation")
        elif video_id == "presentation":
            player.play("credits")
    
    player.on_finished(on_video_end)
    
    # Régler le volume
    player.set_volume(80)
    
    # Lancer la première vidéo
    player.play("intro")
    
    # Garder le programme en vie
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹ Arrêt...")
        player.release()

    main()