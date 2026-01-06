import os
import re
import sys
import pty

KEYWORDS = ["start", "stop", "bonjour", "pizza", "mode turbo"]

def normalize(s: str) -> str:
    return " ".join(s.lower().split())

def build_patterns(keywords: list[str]):
    patterns = {}
    for kw in keywords:
        kw_norm = normalize(kw)
        if " " in kw_norm:
            # phrase
            patterns[kw] = re.compile(re.escape(kw_norm), re.IGNORECASE)
        else:
            # mot seul
            patterns[kw] = re.compile(rf"\b{re.escape(kw_norm)}\b", re.IGNORECASE)
    return patterns

PATTERNS = build_patterns(KEYWORDS)

def main():
    cmd = [sys.executable, "-u", "stt_from_mic_mlx.py"]

    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(cmd[0], cmd)

    rolling = ""
    last_counts = {kw: 0 for kw in KEYWORDS}

    try:
        while True:
            data = os.read(fd, 1024)
            if not data:
                break

            text = data.decode("utf-8", errors="ignore")
            sys.stdout.write(text)
            sys.stdout.flush()

            rolling = (rolling + text)[-20000:]  # garde large, mais borné
            n = normalize(rolling)

            for kw, pat in PATTERNS.items():
                c = len(pat.findall(n))

                if c > last_counts[kw]:
                    print(f"\n✅ DETECTED: {kw}\n")
                    last_counts[kw] = c
                elif c < last_counts[kw]:
                    # si le buffer tronque/retire du texte, on resync
                    last_counts[kw] = c

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
