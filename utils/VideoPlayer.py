import vlc
import threading
from typing import Dict, Callable, Optional


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
        ]
        if fullscreen:
            options.append("--fullscreen")

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

        self.stop()

        media = self._instance.media_new(path)
        self._player.set_media(media)
        self._current_video_id = video_id
        self._player.play()

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
    import time

    player = VideoPlayer(fullscreen=True)

    player.load(
        {
            # "intro": "/home/pi/videos/intro.mp4",
            "intro": "./utils/choix_tshirt.mp4",
        }
    )

    def on_video_end(video_id: str):
        print(f"✓ Vidéo '{video_id}' terminée!")
        if video_id == "intro":
            player.play("presentation")
        elif video_id == "presentation":
            player.play("credits")

    player.on_finished(on_video_end)
    player.set_volume(80)
    player.play("intro")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹ Arrêt...")
        player.release()
