import time
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd


@dataclass
class LevelConfig:
    sample_rate: int = 16000
    block_size: int = 1024
    channels: int = 1
    device: Optional[int] = None
    smoothing: float = 0.25  # 0..1 (higher = smoother)
    calibration_db: float = 0.0
    noise_floor_db: float = -60.0  # ~silence
    max_db: float = -1.0          # ~very loud (near clipping)


class MicrophoneLevelMeter:
    def __init__(self, cfg: LevelConfig = LevelConfig()):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._rms_smooth: float = 0.0
        self._last_db: float = self.cfg.noise_floor_db
        self._last_level: int = 0

    def start(self) -> None:
        if self._stream is not None:
            return

        self._stream = sd.InputStream(
            samplerate=self.cfg.sample_rate,
            blocksize=self.cfg.block_size,
            channels=self.cfg.channels,
            device=self.cfg.device,
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

    def _callback(self, indata, frames, time_info, status) -> None:
        x = np.asarray(indata, dtype=np.float32)
        if x.ndim > 1:
            x = x[:, 0]

        rms = float(np.sqrt(np.mean(x * x) + 1e-12))

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
    
    def get_db(self) -> float:
        with self._lock:
            return float(self._last_db)


if __name__ == "__main__":
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
