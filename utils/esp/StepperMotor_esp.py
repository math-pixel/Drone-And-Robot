# stepper.py - À uploader sur l'ESP32

from machine import Pin
import time


class Stepper28BYJ48:
    """
    Classe pour contrôler un moteur 28BYJ-48 sur ESP32 (MicroPython)
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
        """
        Initialise le moteur
        
        Args:
            in1, in2, in3, in4: Numéros de GPIO
            mode: 'half' (précis) ou 'full' (puissant)
        """
        # Créer les objets Pin
        self.pins = [
            Pin(in1, Pin.OUT),
            Pin(in2, Pin.OUT),
            Pin(in3, Pin.OUT),
            Pin(in4, Pin.OUT)
        ]
        
        self.sequence = self.HALF_STEP if mode == 'half' else self.FULL_STEP
        self.steps_per_rev = 4096 if mode == 'half' else 2048
        self.seq_index = 0
        
        # Système de position
        self._position = 0.0
        self._step_count = 0
        
        # Éteindre toutes les bobines
        self._set_pins([0, 0, 0, 0])
    
    def _set_pins(self, values):
        """Définit l'état des 4 pins"""
        for pin, val in zip(self.pins, values):
            pin.value(val)
    
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
        """Définit la position actuelle SANS bouger le moteur"""
        self._position = float(angle)
        self._step_count = self._degrees_to_steps(angle)
        print(f"Position initialisee a {angle} deg")
    
    def set_zero(self):
        """Définit la position actuelle comme étant le ZÉRO"""
        self.init_position(0)
    
    def get_position(self):
        """Retourne la position actuelle en degrés"""
        return self._position
    
    def get_heading(self):
        """Retourne le heading (0-360°)"""
        return self._position % 360
    
    def get_steps(self):
        """Retourne le nombre de pas depuis le zéro"""
        return self._step_count
    
    # =========================================
    # MOUVEMENTS
    # =========================================
    
    def step(self, steps, delay_ms=1):
        """
        Avance d'un nombre de pas
        
        Args:
            steps: Nombre de pas (+ ou -)
            delay_ms: Délai entre chaque pas en millisecondes
        """
        direction = 1 if steps > 0 else -1
        
        for _ in range(abs(steps)):
            self._set_pins(self.sequence[self.seq_index])
            self.seq_index = (self.seq_index + direction) % len(self.sequence)
            self._step_count += direction
            time.sleep_ms(delay_ms)
        
        # Mettre à jour la position
        self._position = self._steps_to_degrees(self._step_count)
    
    def rotate(self, degrees, delay_ms=1):
        """Rotation RELATIVE de X degrés"""
        steps = self._degrees_to_steps(degrees)
        self.step(steps, delay_ms)
    
    def go_to(self, target_angle, delay_ms=1):
        """Va à une position ABSOLUE"""
        delta = target_angle - self._position
        if delta != 0:
            self.rotate(delta, delay_ms)
    
    def go_to_shortest(self, target_angle, delay_ms=1):
        """Va à une position par le chemin le plus court"""
        current = self.get_heading()
        target = target_angle % 360
        
        delta = target - current
        
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        
        self.rotate(delta, delay_ms)
    
    def home(self, delay_ms=1):
        """Retourne à la position ZÉRO"""
        self.go_to(0, delay_ms)
    
    def turns(self, n, delay_ms=1):
        """Fait n tours complets"""
        self.step(int(n * self.steps_per_rev), delay_ms)
    
    # =========================================
    # UTILITAIRES
    # =========================================
    
    def status(self):
        """Affiche le statut actuel"""
        print("=" * 40)
        print(f"Position:  {self._position:.2f} deg")
        print(f"Heading:   {self.get_heading():.2f} deg")
        print(f"Pas:       {self._step_count}")
        print("=" * 40)
    
    def stop(self):
        """Arrête le moteur et coupe les bobines"""
        self._set_pins([0, 0, 0, 0])