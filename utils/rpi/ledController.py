# ledController.py

from neopixel import NeoPixel
from machine import Pin
import time

class LEDController:
    """Contrôleur NeoPixel avec animation fluide"""

    def __init__(self, pin_num, num_leds, num_columns, leds_by_column, flip_vertical=True):
        self.num_leds = num_leds
        self.num_columns = num_columns
        self.leds_by_column = leds_by_column
        self.flip_vertical = flip_vertical  # ✅ inverse haut/bas si True
        self.np = NeoPixel(Pin(pin_num), num_leds)
        self.current_level = 0  # Niveau actuel (nombre de LEDs par colonne)

    def lights_off(self):
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()
        self.current_level = 0

    def _row_to_index(self, logical_row):
        # logical_row: 0 = bas, leds_by_column-1 = haut
        if self.flip_vertical:
            return (self.leds_by_column - 1) - logical_row
        return logical_row

    def _set_row(self, logical_row, r, g, b):
        """Allume une rangée (même LED sur toutes les colonnes)."""
        row_index = self._row_to_index(logical_row)

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
            self._set_row(self.current_level, r, g, b)  # current_level = "row logique" depuis le bas
            self.current_level += 1
            time.sleep(delay)

        # Descend (éteint une par une)
        while self.current_level > target:
            self.current_level -= 1
            self._set_row(self.current_level, 0, 0, 0)
            time.sleep(delay)

    def light_up(self, start, end, r, g, b):
        # Optionnel: si tu veux aussi inverser ici, dis-moi comment tu utilises start/end (par colonne ou global)
        for i in range(start, min(end + 1, self.num_leds)):
            self.np[i] = (r, g, b)
        self.np.write()
