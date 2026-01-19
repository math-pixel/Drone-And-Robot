import time
import threading
from dataclasses import dataclass
from typing import Optional, Any

import numpy as np
import sounddevice as sd


@dataclass
class LevelConfig:
    sample_rate: int = 16000
    block_size: int = 1024
    channels: int = 1
    device: Optional[int] = None  # None = default input
    smoothing: float = 0.25       # 0..1 (higher = smoother)
    calibration_db: float = 0.0
    noise_floor_db: float = -60.0 # ~silence
    max_db: float = -1.0          # ~very loud (near clipping)


class MicrophoneLevelMeter:
    """
    Cross-platform (macOS/Linux/RPi) mic level meter using sounddevice.

    Key Linux/RPi fixes:
    - Force mono mapping (and keep in float32)
    - Handle status flags + occasional callback anomalies
    - Allow selecting input device by:
        * cfg.device (index)
        * env MICROPHONE_DEVICE (index)
    - Optionally switch hostapi by using system default settings
    """

    def __init__(self, cfg: LevelConfig = LevelConfig()):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._rms_smooth: float = 0.0
        self._last_db: float = float(self.cfg.noise_floor_db)
        self._last_level: int = 0

    # -----------------------------
    # Device helpers (Linux/RPi)
    # -----------------------------
    def _resolve_device(self) -> Optional[int]:
        if self.cfg.device is not None:
            return self.cfg.device

        env = os.getenv("MICROPHONE_DEVICE")
        if env is not None:
            try:
                return int(env)
            except ValueError:
                pass

        return None

    @staticmethod
    def list_devices() -> None:
        print(sd.query_devices())

    # -----------------------------
    # Public API
    # -----------------------------
    def start(self) -> None:
        if self._stream is not None:
            return

        device = self._resolve_device()

        # On Linux/RPi, specifying device can help when default is wrong.
        # Also, setting "channels=1" is important (mono).
        self._stream = sd.InputStream(
            samplerate=int(self.cfg.sample_rate),
            blocksize=int(self.cfg.block_size),
            channels=int(self.cfg.channels),
            device=device,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None

    def get_level_0_to_5(self) -> int:
        with self._lock:
            return int(self._last_level)

    def get_db(self) -> float:
        with self._lock:
            return float(self._last_db)

    # -----------------------------
    # Internals
    # -----------------------------
    def _callback(self, indata: Any, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
        # status can be non-empty on Linux (over/underflow). Don’t crash.
        if status:
            # keep last values, just ignore the glitchy buffer
            return

        try:
            x = np.asarray(indata, dtype=np.float32)
            if x.size == 0:
                return

            # force mono: take first channel if multi-channel
            if x.ndim > 1:
                x = x[:, 0]

            # RMS
            rms = float(np.sqrt(np.mean(x * x) + 1e-12))
        except Exception:
            return

        with self._lock:
            a = float(self.cfg.smoothing)
            self._rms_smooth = (a * self._rms_smooth) + ((1.0 - a) * rms)

            db = 20.0 * float(np.log10(self._rms_smooth + 1e-12)) + float(self.cfg.calibration_db)
            self._last_db = db
            self._last_level = self._db_to_level(db)

    def _db_to_level(self, db: float) -> int:
        nf = float(self.cfg.noise_floor_db)
        mx = float(self.cfg.max_db)

        if db <= nf:
            return 0
        if db >= mx:
            return 5

        t = (db - nf) / (mx - nf)  # 0..1
        lvl = int(np.floor(t * 6.0))  # 0..5
        return max(0, min(5, lvl))


# --- needed for env in _resolve_device ---
import os


if __name__ == "__main__":
    # Tips RPi:
    # - If no input: run `python MicrophoneLevelMeter.py` then `MicrophoneLevelMeter.list_devices()`
    # - Or set MICROPHONE_DEVICE=2 (example) before launching.
    meter = MicrophoneLevelMeter(LevelConfig())
    meter.start()

    try:
        print("Mic level meter started. Speak / clap / shout. Ctrl+C to stop.")
        while True:
            lvl = meter.get_level_0_to_5()
            db = meter.get_db()
            bars = "█" * lvl + "·" * (5 - lvl)
            shout = "  <-- CRI" if lvl >= 4 else ""
            print(f"level={lvl} [{bars}]  db={db:6.1f}{shout}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        meter.stop()
        print("Stopped.")
