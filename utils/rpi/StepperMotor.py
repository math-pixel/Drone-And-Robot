import time

try:
    import lgpio
    USE_LGPIO = True
except ImportError:
    import RPi.GPIO as GPIO
    USE_LGPIO = False


class Stepper28BYJ48:
    """
    Classe pour contrôler un moteur 28BYJ-48 avec suivi de position
    """
    
    HALF_STEP = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1]
    ]
    
    FULL_STEP = [
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1],
        [1, 0, 0, 1]
    ]
    
    def __init__(self, in1, in2, in3, in4, mode='half'):
        self.pins = [in1, in2, in3, in4]
        self.sequence = self.HALF_STEP if mode == 'half' else self.FULL_STEP
        self.steps_per_rev = 4096 if mode == 'half' else 2048
        self.seq_index = 0
        
        # === SYSTÈME DE POSITION ===
        self._position = 0.0          # Position actuelle en degrés
        self._step_count = 0          # Compteur de pas total
        self._zero_offset = 0.0       # Offset du zéro
        
        # Initialisation GPIO
        if USE_LGPIO:
            self.h = lgpio.gpiochip_open(0)
            for pin in self.pins:
                lgpio.gpio_claim_output(self.h, pin, 0)
        else:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in self.pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 0)
    
    def _set_pins(self, values):
        if USE_LGPIO:
            for pin, val in zip(self.pins, values):
                lgpio.gpio_write(self.h, pin, val)
        else:
            for pin, val in zip(self.pins, values):
                GPIO.output(pin, val)
    
    def _steps_to_degrees(self, steps):
        """Convertit des pas en degrés"""
        return (steps / self.steps_per_rev) * 360
    
    def _degrees_to_steps(self, degrees):
        """Convertit des degrés en pas"""
        return int((degrees / 360) * self.steps_per_rev)
    
    # =========================================
    # SYSTÈME DE POSITION / HEADING
    # =========================================
    
    def init_position(self, angle):
        """
        Définit la position actuelle SANS bouger le moteur.
        Utile pour calibrer le zéro ou définir où se trouve le moteur.
        
        Exemple: 
            - Le moteur est physiquement à 90°
            - Tu appelles init_position(90)
            - Maintenant get_position() retourne 90
        """
        self._position = float(angle)
        self._step_count = self._degrees_to_steps(angle)
        print(f"📍 Position initialisée à {angle}°")
    
    def set_zero(self):
        """
        Définit la position actuelle comme étant le ZÉRO.
        Équivalent à init_position(0)
        """
        self.init_position(0)
        print("📍 Position actuelle définie comme ZÉRO")
    
    def get_position(self):
        """Retourne la position actuelle en degrés"""
        return self._position
    
    def get_heading(self):
        """
        Retourne le heading (0-360°)
        Toujours positif, comme une boussole
        """
        return self._position % 360
    
    def get_steps(self):
        """Retourne le nombre de pas depuis le zéro"""
        return self._step_count
    
    # =========================================
    # MOUVEMENTS
    # =========================================
    
    def step(self, steps, delay=0.001):
        """Avance d'un nombre de pas (relatif)"""
        direction = 1 if steps > 0 else -1
        
        for _ in range(abs(steps)):
            self._set_pins(self.sequence[self.seq_index])
            self.seq_index = (self.seq_index + direction) % len(self.sequence)
            self._step_count += direction
            time.sleep(delay)
        
        # Mettre à jour la position
        self._position = self._steps_to_degrees(self._step_count)
    
    def rotate(self, degrees, delay=0.001):
        """
        Rotation RELATIVE de X degrés
        
        Exemple:
            - Position actuelle: 45°
            - rotate(30)
            - Nouvelle position: 75°
        """
        steps = self._degrees_to_steps(degrees)
        self.step(steps, delay)
    
    def go_to(self, target_angle, delay=0.001):
        """
        Va à une position ABSOLUE
        
        Exemple:
            - Position actuelle: 45°
            - go_to(90)
            - Le moteur tourne de 45° pour arriver à 90°
        """
        delta = target_angle - self._position
        if delta != 0:
            print(f"🎯 Aller de {self._position:.1f}° → {target_angle}° (delta: {delta:+.1f}°)")
            self.rotate(delta, delay)
    
    def go_to_shortest(self, target_angle, delay=0.001):
        """
        Va à une position absolue par le chemin le plus court (max 180°)
        Utile pour les mouvements de type boussole/heading
        """
        current = self.get_heading()
        target = target_angle % 360
        
        delta = target - current
        
        # Prendre le chemin le plus court
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        
        print(f"🎯 Chemin court: {current:.1f}° → {target}° (delta: {delta:+.1f}°)")
        self.rotate(delta, delay)
    
    def home(self, delay=0.001):
        """Retourne à la position ZÉRO"""
        print(f"🏠 Retour au zéro depuis {self._position:.1f}°")
        self.go_to(0, delay)
    
    def turns(self, n, delay=0.001):
        """Fait n tours complets"""
        self.step(int(n * self.steps_per_rev), delay)
    
    # =========================================
    # UTILITAIRES
    # =========================================
    
    def status(self):
        """Affiche le statut actuel"""
        print("=" * 40)
        print(f"📍 Position:  {self._position:.2f}°")
        print(f"🧭 Heading:   {self.get_heading():.2f}°")
        print(f"👣 Pas:       {self._step_count}")
        print("=" * 40)
    
    def stop(self):
        """Arrête le moteur"""
        self._set_pins([0, 0, 0, 0])
    
    def cleanup(self):
        """Libère les ressources GPIO"""
        self.stop()
        if USE_LGPIO:
            lgpio.gpiochip_close(self.h)
        else:
            GPIO.cleanup()


# =========================================
# EXEMPLE D'UTILISATION
# =========================================

if __name__ == "__main__":
    
    import time
    motor = Stepper28BYJ48(
        in1=17,
        in2=18,
        in3=27,
        in4=22,
        mode='half'
    )
    
    try:
        # === CALIBRATION INITIALE ===
        # Imaginons que le moteur est physiquement positionné à 45°
        motor.init_position(0)
        motor.status()
        
        # === MOUVEMENT RELATIF ===
        print("\n▶ Rotation relative de +30°")
        motor.rotate(30)
        motor.status()
        # Position: 45 + 30 = 75°
        
        time.sleep(3)
        # === MOUVEMENT ABSOLU ===
        print("\n▶ Aller à la position 180°")
        motor.go_to(180)
        motor.status()
        # Position: 180°
        
        time.sleep(3)
        # === RETOUR AU ZÉRO ===
        print("\n▶ Retour à zéro")
        motor.home()
        motor.status()
        # Position: 0°
        
        time.sleep(3)
        # === REDÉFINIR LE ZÉRO ===
        print("\n▶ Rotation de 90° puis définir comme nouveau zéro")
        motor.rotate(90)
        motor.set_zero()
        motor.status()
        # Position: 0° (mais physiquement on a tourné)
        
        time.sleep(3)
        # === CHEMIN LE PLUS COURT ===
        print("\n▶ Test chemin le plus court")
        motor.go_to(270)  # Aller à 270°
        motor.status()
        
        time.sleep(3)
        motor.go_to_shortest(10)  # Aller à 10° par le chemin le plus court
        motor.status()
        # Au lieu de -260°, il fera +100° (plus court!)
        
    except KeyboardInterrupt:
        print("\n⛔ Arrêt!")
    
    finally:
        motor.stop()
        motor.cleanup()