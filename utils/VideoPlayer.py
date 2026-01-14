import vlc
import threading
from typing import Dict, Callable, Optional
import time


class VideoPlayer:
    """Lecteur vidéo simple pour Raspberry Pi"""

    def __init__(self, fullscreen: bool = True):
        # options = [
        #     "--no-video-title-show",
        #     "--vout=macosx",
        #     "--video-on-top",
        # ]
                
        options = [
            "--no-xlib",
            "--aout=alsa",
            "--video-on-top",
            "--mouse-hide-timeout=0",
            "--autoscale",
            #"--scale=1",
            #"--zoom=1",
            "--aspect-ratio=16:9",
            "--width=1920",
            "--height=1080"
        ]

        if fullscreen:
            pass
            #options.append("--fullscreen")

        self._instance = vlc.Instance(" ".join(options))
        self._player = self._instance.media_player_new()
        self._videos: Dict[str, str] = {}
        self._on_finished_callback: Optional[Callable[[str], None]] = None
        self._current_video_id: Optional[str] = None
        self._lock = threading.Lock()

        event_manager = self._player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_end)

    def load(self, videos: Dict[str, str]) -> None:
        with self._lock:
            self._videos.update(videos)
            print(f"✓ {len(videos)} vidéo(s) chargée(s)")

    def play(self, video_id: str) -> bool:
        with self._lock:
            if video_id not in self._videos:
                print(f"✗ Vidéo '{video_id}' non trouvée")
                return False
            path = self._videos[video_id]

        #self.stop()

        media = self._instance.media_new(path)
        self._player.set_media(media)
        self._current_video_id = video_id
        self._player.play()

        # if self._fullscreen:
        #     threading.Thread(target=self._set_fullscreen_delayed, daemon=True).start()

        print(f"▶ Lecture: {video_id}")
        return True

    def stop(self) -> None:
        self._player.stop()
        self._current_video_id = None

    def pause(self) -> None:
        self._player.pause()

    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(max(0, min(100, volume)))

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def get_position(self) -> float:
        return self._player.get_position()

    def on_finished(self, callback: Callable[[str], None]) -> None:
        self._on_finished_callback = callback

    def _handle_end(self, event) -> None:
        video_id = self._current_video_id
        self._current_video_id = None

        if self._on_finished_callback and video_id:
            threading.Thread(
                target=self._on_finished_callback,
                args=(video_id,),
                daemon=True,
            ).start()

    def list_videos(self) -> list:
        return list(self._videos.keys())

    def release(self) -> None:
        self.stop()
        self._player.release()


if __name__ == "__main__":
    
    player = VideoPlayer(fullscreen=True)
    
    # Charger les vidéos
    player.load({
        "cine_1": "/videos/cine_1_1.mp4",
        "cine_5": "/videos/cine_1_5.mp4",
    })
    
    player.set_volume(80)
    
    # Callback quand une vidéo se termine
    def on_video_end(video_id: str):
        print(f"✓ {video_id} terminée!")
        
        if video_id == "cine_1":
            player.play("cine_5")
        elif video_id == "cine_5":
            print("✓ Toutes les vidéos jouées!")
            # Optionnel : relancer en boucle
            # player.play("cine_1")
    
    player.on_finished(on_video_end)
    
    # Lancer la première vidéo
    player.play("cine_1")
    
    # Boucle principale
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹ Arrêt...")
        player.release()
