#!/usr/bin/env python3
"""
Contrôle du moteur 28BYJ-48 via le shell
Utilise les touches pour tourner de 1°, 5° ou 10°
"""

import time
import sys
import tty
import termios

try:
    import lgpio
    USE_LGPIO = True
except ImportError:
    import RPi.GPIO as GPIO
    USE_LGPIO = False

# === CONFIGURATION ===
IN1 = 17
IN2 = 18
IN3 = 27
IN4 = 22
PINS = [IN1, IN2, IN3, IN4]

SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

STEPS_PER_REV = 4096
DELAY = 0.001

# === VARIABLES GLOBALES ===
position = 0.0
seq_index = 0

# === INITIALISATION GPIO ===
if USE_LGPIO:
    h = lgpio.gpiochip_open(0)
    for pin in PINS:
        lgpio.gpio_claim_output(h, pin, 0)
else:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)

def set_pins(values):
    if USE_LGPIO:
        for pin, val in zip(PINS, values):
            lgpio.gpio_write(h, pin, val)
    else:
        for pin, val in zip(PINS, values):
            GPIO.output(pin, val)

def rotate(degrees):
    """Fait tourner le moteur de X degrés"""
    global position, seq_index
    
    steps = int((degrees / 360) * STEPS_PER_REV)
    direction = 1 if steps > 0 else -1
    
    for _ in range(abs(steps)):
        set_pins(SEQUENCE[seq_index])
        seq_index = (seq_index + direction) % len(SEQUENCE)
        time.sleep(DELAY)
    
    set_pins([0, 0, 0, 0])
    position += degrees

def get_key():
    """Lit une touche du clavier"""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def cleanup():
    set_pins([0, 0, 0, 0])
    if USE_LGPIO:
        lgpio.gpiochip_close(h)
    else:
        GPIO.cleanup()

def show_help():
    print("\n" + "=" * 50)
    print("🎮 CONTRÔLE MOTEUR 28BYJ-48")
    print("=" * 50)
    print("")
    print("  SENS HORAIRE (+)      SENS ANTI-HORAIRE (-)")
    print("  ─────────────────     ─────────────────────")
    print("  [1] → +1°             [q] → -1°")
    print("  [5] → +5°             [t] → -5°")
    print("  [0] → +10°            [p] → -10°")
    print("")
    print("  [h] → Afficher l'aide")
    print("  [z] → Remettre position à zéro")
    print("  [r] → Retourner à la position zéro")
    print("  [s] → Afficher position actuelle")
    print("  [x] ou [Ctrl+C] → Quitter")
    print("=" * 50)

def show_position():
    heading = position % 360
    print(f"📍 Position: {position:+.1f}° | Heading: {heading:.1f}°")

# === BOUCLE PRINCIPALE ===
if __name__ == "__main__":
    show_help()
    show_position()
    print("\n⌨️  En attente de commande...")
    
    try:
        while True:
            key = get_key()
            
            # Sens horaire (+)
            if key == '1':
                rotate(1)
                print(f"↻ +1°  → Position: {position:+.1f}°")
            
            elif key == '5':
                rotate(5)
                print(f"↻ +5°  → Position: {position:+.1f}°")
            
            elif key == '0':
                rotate(10)
                print(f"↻ +10° → Position: {position:+.1f}°")
            
            # Sens anti-horaire (-)
            elif key == 'q':
                rotate(-1)
                print(f"↺ -1°  → Position: {position:+.1f}°")
            
            elif key == 't':
                rotate(-5)
                print(f"↺ -5°  → Position: {position:+.1f}°")
            
            elif key == 'p':
                rotate(-10)
                print(f"↺ -10° → Position: {position:+.1f}°")
            
            # Commandes spéciales
            elif key == 'z':
                position = 0
                print("📍 Position remise à zéro")
            
            elif key == 'r':
                print(f"🏠 Retour au zéro depuis {position:+.1f}°...")
                rotate(-position)
                print("📍 Position: 0°")
            
            elif key == 's':
                show_position()
            
            elif key == 'h':
                show_help()
            
            elif key == 'x' or ord(key) == 3:  # x ou Ctrl+C
                print("\n👋 Arrêt du programme")
                break
    
    except KeyboardInterrupt:
        print("\n👋 Arrêt du programme")
    
    finally:
        cleanup()