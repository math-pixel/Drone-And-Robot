import time
import board
import neopixel


class LEDController:
    """Classe pour contrôler un bandeau de LEDs adressables Neopixel"""
    
    def __init__(self, pin, num_leds, brightness=1.0):
        """
        Initialise le contrôleur de LEDs
        
        Args:
            pin: Pin GPIO du bandeau (ex: board.D18)
            num_leds: Nombre de LEDs sur le bandeau
            brightness: Luminosité (0.0 à 1.0)
        """
        self.num_leds = num_leds
        self.pixels = neopixel.NeoPixel(
            pin, 
            num_leds, 
            brightness=brightness,
            auto_write=False  # On contrôle manuellement les updates
        )
    
    def lightsON(self, r=255, g=255, b=255):
        """
        Allume toutes les LEDs du bandeau
        
        Args:
            r: Valeur rouge (0-255), défaut: 255
            g: Valeur verte (0-255), défaut: 255
            b: Valeur bleue (0-255), défaut: 255
        """
        self.pixels.fill((r, g, b))
        self.pixels.show()
    
    def lightsOFF(self):
        """Éteint toutes les LEDs du bandeau"""
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
    
    def lightOFF(self, led_start, led_end):
        """
        Éteint les LEDs comprises entre led_start et led_end (inclus)
        
        Args:
            led_start: Index de la première LED à éteindre
            led_end: Index de la dernière LED à éteindre
        """
        # Validation des indices
        led_start = max(0, led_start)
        led_end = min(self.num_leds - 1, led_end)
        
        for i in range(led_start, led_end + 1):
            self.pixels[i] = (0, 0, 0)
        self.pixels.show()
    
    def lightUp(self, led_start, led_end, r=255, g=255, b=255, ease=0):
        """
        Allume les LEDs comprises entre led_start et led_end
        
        Args:
            led_start: Index de la première LED à allumer
            led_end: Index de la dernière LED à allumer
            r: Valeur rouge (0-255), défaut: 255
            g: Valeur verte (0-255), défaut: 255
            b: Valeur bleue (0-255), défaut: 255
            ease: Vitesse d'animation (0 = instantané, plus c'est grand, plus c'est lent)
                  La valeur représente le délai en millisecondes entre chaque LED
        """
        # Validation des indices
        led_start = max(0, led_start)
        led_end = min(self.num_leds - 1, led_end)
        
        if ease == 0:
            # Affichage instantané
            for i in range(led_start, led_end + 1):
                self.pixels[i] = (r, g, b)
            self.pixels.show()
        else:
            # Affichage progressif LED par LED
            delay = ease / 1000  # Convertit ms en secondes
            for i in range(led_start, led_end + 1):
                self.pixels[i] = (r, g, b)
                self.pixels.show()
                time.sleep(delay)

if __name__ == "__main__":
    import board

    # Initialisation : bandeau sur pin D18 avec 60 LEDs
    leds = LEDController(pin=board.D18, num_leds=60)

    # Allumer tout en blanc
    leds.lightsON()

    # Allumer tout en rouge
    leds.lightsON(r=255, g=0, b=0)

    # Éteindre tout
    leds.lightsOFF()

    # Éteindre seulement les LEDs 10 à 20
    leds.lightOFF(10, 20)

    # Allumer les LEDs 0 à 15 en bleu instantanément
    leds.lightUp(0, 15, r=0, g=0, b=255)

    # Allumer les LEDs 20 à 40 en vert avec animation (50ms entre chaque LED)
    leds.lightUp(20, 40, r=0, g=255, b=0, ease=50)

    # Animation lente en violet (200ms entre chaque LED)
    leds.lightUp(0, 59, r=128, g=0, b=255, ease=200)