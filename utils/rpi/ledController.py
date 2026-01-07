# ======================================================
# LED CONTROLLER
# ======================================================

from neopixel import NeoPixel
from machine import Pin
import time

class LEDController:
    """Contrôleur NeoPixel avec animation fluide"""
    
    def __init__(self, pin_num, num_leds, num_columns, leds_by_column):
        self.num_leds = num_leds
        self.num_columns = num_columns
        self.leds_by_column = leds_by_column
        self.np = NeoPixel(Pin(pin_num), num_leds)
        self.current_level = 0  # Niveau actuel (nombre de LEDs par colonne)
    
    def lights_off(self):
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()
        self.current_level = 0
    
    def _set_row(self, row_index, r, g, b):
        """Allume une rangée (même LED sur toutes les colonnes)."""
        for col in range(self.num_columns):
            led_index = col * self.leds_by_column + row_index
            if led_index < self.num_leds:
                self.np[led_index] = (r, g, b)
        self.np.write()
    
    def set_level(self, target, r, g, b, delay=0.03):
        """
        Anime les LEDs une par une jusqu'à la cible.
        
        target: nombre de LEDs à allumer par colonne
        delay: temps entre chaque LED (en secondes)
        """
        target = max(0, min(self.leds_by_column, target))
        
        # Monte (allume une par une)
        while self.current_level < target:
            self._set_row(self.current_level, r, g, b)
            self.current_level += 1
            time.sleep(delay)
        
        # Descend (éteint une par une)
        while self.current_level > target:
            self.current_level -= 1
            self._set_row(self.current_level, 0, 0, 0)
            time.sleep(delay)
