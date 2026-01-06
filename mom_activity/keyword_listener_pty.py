import asyncio
import os
import re
import sys
import pty
import signal
from typing import Callable, Optional, Dict


class KeywordSTT:
    def __init__(
        self,
        stt_script: str = "stt_from_mic_mlx.py",
        keywords: Optional[list[str]] = None,
        on_keyword: Optional[Callable[[str], None]] = None,
        rolling_max: int = 20000,
    ):
        self.stt_script = stt_script
        self.keywords = keywords or ["start", "stop", "bonjour", "pizza", "mode turbo"]
        self.on_keyword = on_keyword
        self.rolling_max = rolling_max

        self._pid: Optional[int] = None
        self._fd: Optional[int] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._rolling = ""
        self._patterns = self._build_patterns(self.keywords)
        self._last_counts: Dict[str, int] = {kw: 0 for kw in self.keywords}

    # ✅ MODIF 1: normalisation -> enlève les virgules (et ponctuation proche)
    @staticmethod
    def _normalize(s: str) -> str:
        s = s.replace(",", "").replace("，", "")
        s = s.replace(".", "").replace("…", "")
        s = s.replace(";", "").replace(":", "").replace("!", "").replace("?", "")
        return " ".join(s.lower().split())

    # ✅ MODIF 2: patterns compilés sur la version normalisée + mapping "pattern->keyword original"
    def _build_patterns(self, keywords: list[str]) -> Dict[str, re.Pattern]:
        patterns: Dict[str, re.Pattern] = {}
        for kw in keywords:
            kw_norm = self._normalize(kw)

            # on compile TOUJOURS sur la forme normalisée
            # (ça permet: "Je n'irai plus." == "Je n'irai plus")
            patterns[kw] = re.compile(re.escape(kw_norm), re.IGNORECASE)

        return patterns

    def start(self):
        if self._pid is not None:
            return

        cmd = [sys.executable, "-u", self.stt_script]

        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(cmd[0], cmd)

        self._pid = pid
        self._fd = fd
        self._loop = asyncio.get_running_loop()
        self._loop.add_reader(fd, self._on_readable)

    def stop(self):
        if self._loop is not None and self._fd is not None:
            try:
                self._loop.remove_reader(self._fd)
            except Exception:
                pass

        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass

        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGINT)
            except Exception:
                pass
            try:
                os.kill(self._pid, signal.SIGTERM)
            except Exception:
                pass

        self._pid = None
        self._fd = None
        self._loop = None

    def _on_readable(self):
        if self._fd is None:
            return

        try:
            data = os.read(self._fd, 1024)
            if not data:
                self.stop()
                return
        except OSError:
            self.stop()
            return

        text = data.decode("utf-8", errors="ignore")
        sys.stdout.write(text)
        sys.stdout.flush()

        self._rolling = (self._rolling + text)[-self.rolling_max :]
        n = self._normalize(self._rolling)  # ✅ MODIF 3: rolling normalisé (virgules etc retirées)

        for kw, pat in self._patterns.items():
            c = len(pat.findall(n))

            if c > self._last_counts[kw]:
                self._last_counts[kw] = c
                if self.on_keyword:
                    try:
                        self.on_keyword(kw)  # renvoie le kw original (avec accents/ponctuation originale)
                    except Exception:
                        pass
            elif c < self._last_counts[kw]:
                self._last_counts[kw] = c


if __name__ == "__main__":
    async def _run():
        def on_kw(kw: str):
            print(f"\n✅ DETECTED: {kw}\n")

        stt = KeywordSTT(stt_script="./stt_from_mic_mlx.py", on_keyword=on_kw)
        stt.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            stt.stop()

    asyncio.run(_run())
