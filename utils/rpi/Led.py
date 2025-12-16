import time
import threading
import math
import random
from rpi_ws281x import PixelStrip, Color
from enum import Enum
from typing import List, Tuple, Union, Optional, Callable


class TypeLED(Enum):
    """Types de LED supportés"""
    WS2812 = 0x00100800   # GRB
    WS2812B = 0x00100800  # GRB
    WS2811 = 0x00100800   # GRB
    SK6812 = 0x00100800   # GRB
    SK6812W = 0x18100800  # GRBW
    SK6812_RGBW = 0x18100800
    WS2812_RGB = 0x00100800


class BandeauLED:
    """
    Classe complète pour contrôler un bandeau de LED adressables
    Supporte: WS2812, WS2812B, WS2811, SK6812, SK6812W (RGBW)
    
    Fonctionnalités:
    - Contrôle individuel et global des LEDs
    - Effets et animations (rainbow, chase, fire, etc.)
    - Segments indépendants
    - Support RGB, HSV, HEX
    - Animations non-bloquantes
    - Gradients et patterns
    """
    
    # Couleurs prédéfinies
    COULEURS = {
        'rouge': (255, 0, 0),
        'vert': (0, 255, 0),
        'bleu': (0, 0, 255),
        'blanc': (255, 255, 255),
        'noir': (0, 0, 0),
        'jaune': (255, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'orange': (255, 165, 0),
        'rose': (255, 105, 180),
        'violet': (148, 0, 211),
        'indigo': (75, 0, 130),
        'turquoise': (64, 224, 208),
        'or': (255, 215, 0),
        'argent': (192, 192, 192),
        'corail': (255, 127, 80),
        'saumon': (250, 128, 114),
        'lime': (50, 205, 50),
        'aqua': (0, 255, 255),
        'navy': (0, 0, 128),
    }
    
    def __init__(
        self,
        num_leds: int,
        pin: int = 18,
        frequence: int = 800000,
        dma: int = 10,
        luminosite: int = 255,
        inverser: bool = False,
        canal: int = 0,
        type_led: TypeLED = TypeLED.WS2812B
    ):
        """
        Initialise le bandeau LED
        
        Args:
            num_leds: Nombre de LEDs sur le bandeau
            pin: GPIO (18=PWM0, 12=PWM0, 21=PCM, 10=SPI)
            frequence: Fréquence du signal (800kHz pour WS2812)
            dma: Canal DMA (10 recommandé)
            luminosite: Luminosité initiale (0-255)
            inverser: Inverser le signal (pour level shifter)
            canal: Canal PWM (0 ou 1)
            type_led: Type de LED (WS2812B, SK6812, etc.)
        """
        self.num_leds = num_leds
        self.pin = pin
        self._luminosite = luminosite
        self.type_led = type_led
        
        # État interne
        self._buffer = [(0, 0, 0)] * num_leds
        self._running = False
        self._animation_thread = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Segments
        self._segments = {}
        
        # Initialisation du strip
        self._strip = PixelStrip(
            num_leds,
            pin,
            frequence,
            dma,
            inverser,
            luminosite,
            canal,
            type_led.value
        )
        self._strip.begin()
        
        # Éteindre toutes les LEDs au démarrage
        self.tout_eteindre()
    
    # ===============================================
    # PROPRIÉTÉS
    # ===============================================
    
    @property
    def luminosite(self) -> int:
        """Retourne la luminosité actuelle (0-255)"""
        return self._luminosite
    
    @luminosite.setter
    def luminosite(self, valeur: int):
        """Définit la luminosité (0-255)"""
        self._luminosite = max(0, min(255, valeur))
        self._strip.setBrightness(self._luminosite)
        self._strip.show()
    
    @property
    def luminosite_pourcent(self) -> float:
        """Retourne la luminosité en pourcentage (0-100)"""
        return (self._luminosite / 255) * 100
    
    @luminosite_pourcent.setter
    def luminosite_pourcent(self, valeur: float):
        """Définit la luminosité en pourcentage (0-100)"""
        self.luminosite = int((valeur / 100) * 255)
    
    @property
    def est_anime(self) -> bool:
        """Retourne True si une animation est en cours"""
        return self._running
    
    @property
    def buffer(self) -> List[Tuple[int, int, int]]:
        """Retourne une copie du buffer actuel"""
        return self._buffer.copy()
    
    # ===============================================
    # CONVERSION DE COULEURS
    # ===============================================
    
    @staticmethod
    def hex_vers_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convertit une couleur HEX en RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_vers_hex(r: int, g: int, b: int) -> str:
        """Convertit RGB en HEX"""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def hsv_vers_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
        """
        Convertit HSV en RGB
        
        Args:
            h: Teinte (0-360)
            s: Saturation (0-1)
            v: Valeur (0-1)
        
        Returns:
            Tuple (R, G, B) avec valeurs 0-255
        """
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255)
        )
    
    @staticmethod
    def rgb_vers_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convertit RGB en HSV"""
        r, g, b = r / 255, g / 255, b / 255
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c
        
        # Valeur
        v = max_c
        
        # Saturation
        s = 0 if max_c == 0 else diff / max_c
        
        # Teinte
        if diff == 0:
            h = 0
        elif max_c == r:
            h = 60 * (((g - b) / diff) % 6)
        elif max_c == g:
            h = 60 * (((b - r) / diff) + 2)
        else:
            h = 60 * (((r - g) / diff) + 4)
        
        return (h, s, v)
    
    def _parse_couleur(self, couleur) -> Tuple[int, int, int]:
        """Parse une couleur dans différents formats"""
        if isinstance(couleur, str):
            if couleur.startswith('#'):
                return self.hex_vers_rgb(couleur)
            elif couleur.lower() in self.COULEURS:
                return self.COULEURS[couleur.lower()]
            else:
                raise ValueError(f"Couleur inconnue: {couleur}")
        elif isinstance(couleur, (list, tuple)) and len(couleur) >= 3:
            return (int(couleur[0]), int(couleur[1]), int(couleur[2]))
        else:
            raise ValueError(f"Format de couleur invalide: {couleur}")
    
    def _color_object(self, r: int, g: int, b: int) -> int:
        """Crée un objet Color pour la bibliothèque"""
        return Color(int(r), int(g), int(b))
    
    # ===============================================
    # CONTRÔLE DES LEDS
    # ===============================================
    
    def set_pixel(self, index: int, couleur, auto_afficher: bool = True):
        """
        Définit la couleur d'une LED
        
        Args:
            index: Index de la LED (0 à num_leds-1)
            couleur: Tuple RGB, HEX string, ou nom de couleur
            auto_afficher: Afficher immédiatement
        """
        if 0 <= index < self.num_leds:
            rgb = self._parse_couleur(couleur)
            self._buffer[index] = rgb
            self._strip.setPixelColor(index, self._color_object(*rgb))
            if auto_afficher:
                self._strip.show()
    
    def set_pixels(self, indices: List[int], couleur, auto_afficher: bool = True):
        """Définit la couleur de plusieurs LEDs"""
        rgb = self._parse_couleur(couleur)
        for index in indices:
            if 0 <= index < self.num_leds:
                self._buffer[index] = rgb
                self._strip.setPixelColor(index, self._color_object(*rgb))
        if auto_afficher:
            self._strip.show()
    
    def set_plage(self, debut: int, fin: int, couleur, auto_afficher: bool = True):
        """Définit la couleur d'une plage de LEDs"""
        indices = list(range(debut, min(fin, self.num_leds)))
        self.set_pixels(indices, couleur, auto_afficher)
    
    def set_toutes(self, couleur, auto_afficher: bool = True):
        """Définit la couleur de toutes les LEDs"""
        rgb = self._parse_couleur(couleur)
        for i in range(self.num_leds):
            self._buffer[i] = rgb
            self._strip.setPixelColor(i, self._color_object(*rgb))
        if auto_afficher:
            self._strip.show()
    
    def get_pixel(self, index: int) -> Tuple[int, int, int]:
        """Retourne la couleur d'une LED"""
        if 0 <= index < self.num_leds:
            return self._buffer[index]
        return (0, 0, 0)
    
    def afficher(self):
        """Force l'affichage du buffer"""
        self._strip.show()
    
    def tout_eteindre(self, auto_afficher: bool = True):
        """Éteint toutes les LEDs"""
        self.set_toutes((0, 0, 0), auto_afficher)
    
    def tout_allumer(self, couleur='blanc', auto_afficher: bool = True):
        """Allume toutes les LEDs"""
        self.set_toutes(couleur, auto_afficher)
    
    # ===============================================
    # SEGMENTS
    # ===============================================
    
    def creer_segment(self, nom: str, debut: int, fin: int):
        """Crée un segment nommé"""
        self._segments[nom] = (debut, min(fin, self.num_leds))
    
    def supprimer_segment(self, nom: str):
        """Supprime un segment"""
        if nom in self._segments:
            del self._segments[nom]
    
    def set_segment(self, nom: str, couleur, auto_afficher: bool = True):
        """Définit la couleur d'un segment"""
        if nom in self._segments:
            debut, fin = self._segments[nom]
            self.set_plage(debut, fin, couleur, auto_afficher)
    
    def get_segment(self, nom: str) -> Optional[Tuple[int, int]]:
        """Retourne les bornes d'un segment"""
        return self._segments.get(nom)
    
    @property
    def segments(self) -> dict:
        """Retourne tous les segments"""
        return self._segments.copy()
    
    # ===============================================
    # EFFETS DE BASE
    # ===============================================
    
    def gradient(
        self,
        couleur_debut,
        couleur_fin,
        debut: int = 0,
        fin: int = None,
        auto_afficher: bool = True
    ):
        """Crée un dégradé entre deux couleurs"""
        if fin is None:
            fin = self.num_leds
        
        rgb1 = self._parse_couleur(couleur_debut)
        rgb2 = self._parse_couleur(couleur_fin)
        
        longueur = fin - debut
        for i in range(longueur):
            ratio = i / max(1, longueur - 1)
            r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
            g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
            b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
            self._buffer[debut + i] = (r, g, b)
            self._strip.setPixelColor(debut + i, self._color_object(r, g, b))
        
        if auto_afficher:
            self._strip.show()
    
    def gradient_multi(
        self,
        couleurs: List,
        debut: int = 0,
        fin: int = None,
        auto_afficher: bool = True
    ):
        """Crée un dégradé multi-couleurs"""
        if fin is None:
            fin = self.num_leds
        if len(couleurs) < 2:
            return
        
        longueur = fin - debut
        segment_length = longueur / (len(couleurs) - 1)
        
        for i in range(longueur):
            segment_index = int(i / segment_length)
            if segment_index >= len(couleurs) - 1:
                segment_index = len(couleurs) - 2
            
            local_ratio = (i - segment_index * segment_length) / segment_length
            
            rgb1 = self._parse_couleur(couleurs[segment_index])
            rgb2 = self._parse_couleur(couleurs[segment_index + 1])
            
            r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * local_ratio)
            g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * local_ratio)
            b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * local_ratio)
            
            self._buffer[debut + i] = (r, g, b)
            self._strip.setPixelColor(debut + i, self._color_object(r, g, b))
        
        if auto_afficher:
            self._strip.show()
    
    def motif(self, couleurs: List, decalage: int = 0, auto_afficher: bool = True):
        """Applique un motif répétitif"""
        parsed = [self._parse_couleur(c) for c in couleurs]
        for i in range(self.num_leds):
            idx = (i + decalage) % len(parsed)
            self._buffer[i] = parsed[idx]
            self._strip.setPixelColor(i, self._color_object(*parsed[idx]))
        
        if auto_afficher:
            self._strip.show()
    
    # ===============================================
    # ANIMATIONS (NON-BLOQUANTES)
    # ===============================================
    
    def _animation_loop(self, func: Callable, interval: float, *args, **kwargs):
        """Boucle d'animation générique"""
        self._running = True
        self._stop_event.clear()
        
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    func(*args, **kwargs)
                self._stop_event.wait(interval)
        finally:
            self._running = False
    
    def demarrer_animation(
        self,
        func: Callable,
        interval: float = 0.05,
        *args,
        **kwargs
    ):
        """Démarre une animation en arrière-plan"""
        self.arreter_animation()
        self._animation_thread = threading.Thread(
            target=self._animation_loop,
            args=(func, interval) + args,
            kwargs=kwargs,
            daemon=True
        )
        self._animation_thread.start()
    
    def arreter_animation(self):
        """Arrête l'animation en cours"""
        self._stop_event.set()
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join(timeout=1.0)
        self._running = False
    
    # ===============================================
    # EFFETS ANIMÉS
    # ===============================================
    
    def arc_en_ciel(self, vitesse: float = 0.02, decalage_step: int = 1):
        """Animation arc-en-ciel (non-bloquante)"""
        self._rainbow_offset = 0
        
        def _update():
            for i in range(self.num_leds):
                hue = (i * 360 / self.num_leds + self._rainbow_offset) % 360
                rgb = self.hsv_vers_rgb(hue, 1.0, 1.0)
                self._strip.setPixelColor(i, self._color_object(*rgb))
                self._buffer[i] = rgb
            self._strip.show()
            self._rainbow_offset = (self._rainbow_offset + decalage_step) % 360
        
        self.demarrer_animation(_update, vitesse)
    
    def chenillard(
        self,
        couleur='blanc',
        couleur_fond='noir',
        longueur: int = 5,
        vitesse: float = 0.05,
        inverse: bool = False
    ):
        """Animation chenillard (non-bloquante)"""
        self._chase_pos = 0
        rgb = self._parse_couleur(couleur)
        rgb_bg = self._parse_couleur(couleur_fond)
        
        def _update():
            for i in range(self.num_leds):
                self._strip.setPixelColor(i, self._color_object(*rgb_bg))
            
            for j in range(longueur):
                if inverse:
                    pos = (self.num_leds - 1 - self._chase_pos + j) % self.num_leds
                else:
                    pos = (self._chase_pos + j) % self.num_leds
                self._strip.setPixelColor(pos, self._color_object(*rgb))
            
            self._strip.show()
            self._chase_pos = (self._chase_pos + 1) % self.num_leds
        
        self.demarrer_animation(_update, vitesse)
    
    def clignotement(
        self,
        couleur='blanc',
        vitesse: float = 0.5
    ):
        """Animation clignotement (non-bloquante)"""
        self._blink_state = False
        rgb = self._parse_couleur(couleur)
        
        def _update():
            if self._blink_state:
                for i in range(self.num_leds):
                    self._strip.setPixelColor(i, self._color_object(*rgb))
            else:
                for i in range(self.num_leds):
                    self._strip.setPixelColor(i, self._color_object(0, 0, 0))
            self._strip.show()
            self._blink_state = not self._blink_state
        
        self.demarrer_animation(_update, vitesse)
    
    def respiration(
        self,
        couleur='blanc',
        vitesse: float = 0.02,
        min_lum: int = 0,
        max_lum: int = 255
    ):
        """Animation respiration/pulsation (non-bloquante)"""
        self._breath_value = 0
        self._breath_direction = 1
        rgb = self._parse_couleur(couleur)
        
        def _update():
            factor = self._breath_value / 255
            r = int(rgb[0] * factor)
            g = int(rgb[1] * factor)
            b = int(rgb[2] * factor)
            
            for i in range(self.num_leds):
                self._strip.setPixelColor(i, self._color_object(r, g, b))
            self._strip.show()
            
            self._breath_value += self._breath_direction * 5
            if self._breath_value >= max_lum:
                self._breath_value = max_lum
                self._breath_direction = -1
            elif self._breath_value <= min_lum:
                self._breath_value = min_lum
                self._breath_direction = 1
        
        self.demarrer_animation(_update, vitesse)
    
    def etincelles(
        self,
        couleur='blanc',
        couleur_fond='noir',
        probabilite: float = 0.1,
        vitesse: float = 0.05
    ):
        """Animation étincelles/sparkle (non-bloquante)"""
        rgb = self._parse_couleur(couleur)
        rgb_bg = self._parse_couleur(couleur_fond)
        
        def _update():
            for i in range(self.num_leds):
                if random.random() < probabilite:
                    self._strip.setPixelColor(i, self._color_object(*rgb))
                else:
                    self._strip.setPixelColor(i, self._color_object(*rgb_bg))
            self._strip.show()
        
        self.demarrer_animation(_update, vitesse)
    
    def feu(self, intensite: int = 120, vitesse: float = 0.03):
        """Animation effet feu (non-bloquante)"""
        self._heat = [0] * self.num_leds
        cooling = 55
        sparking = 120
        
        def _update():
            # Refroidissement
            for i in range(self.num_leds):
                cool = random.randint(0, ((cooling * 10) // self.num_leds) + 2)
                self._heat[i] = max(0, self._heat[i] - cool)
            
            # Diffusion de la chaleur
            for i in range(self.num_leds - 1, 1, -1):
                self._heat[i] = (self._heat[i - 1] + self._heat[i - 2] * 2) // 3
            
            # Étincelles aléatoires
            if random.randint(0, 255) < sparking:
                y = random.randint(0, min(7, self.num_leds - 1))
                self._heat[y] = min(255, self._heat[y] + random.randint(160, 255))
            
            # Conversion chaleur -> couleur
            for i in range(self.num_leds):
                t = self._heat[i]
                if t > 170:
                    r, g, b = 255, 255, min(255, (t - 170) * 3)
                elif t > 85:
                    r, g, b = 255, min(255, (t - 85) * 3), 0
                else:
                    r, g, b = min(255, t * 3), 0, 0
                
                self._strip.setPixelColor(i, self._color_object(r, g, b))
            
            self._strip.show()
        
        self.demarrer_animation(_update, vitesse)
    
    def eau(self, vitesse: float = 0.05):
        """Animation effet eau/vagues (non-bloquante)"""
        self._water_phase = 0
        
        def _update():
            for i in range(self.num_leds):
                wave = math.sin(self._water_phase + i * 0.3) * 0.5 + 0.5
                wave2 = math.sin(self._water_phase * 0.7 + i * 0.5) * 0.3 + 0.7
                
                r = int(0 * wave * wave2)
                g = int(100 * wave * wave2)
                b = int(255 * wave * wave2)
                
                self._strip.setPixelColor(i, self._color_object(r, g, b))
            
            self._strip.show()
            self._water_phase += 0.15
        
        self.demarrer_animation(_update, vitesse)
    
    def comete(
        self,
        couleur='blanc',
        longueur_queue: int = 10,
        vitesse: float = 0.03,
        fondu: float = 0.6
    ):
        """Animation comète avec queue (non-bloquante)"""
        self._comet_pos = 0
        rgb = self._parse_couleur(couleur)
        
        def _update():
            # Fondu de toutes les LEDs
            for i in range(self.num_leds):
                current = self._buffer[i]
                faded = (
                    int(current[0] * fondu),
                    int(current[1] * fondu),
                    int(current[2] * fondu)
                )
                self._buffer[i] = faded
                self._strip.setPixelColor(i, self._color_object(*faded))
            
            # Tête de la comète
            pos = self._comet_pos % self.num_leds
            self._buffer[pos] = rgb
            self._strip.setPixelColor(pos, self._color_object(*rgb))
            
            self._strip.show()
            self._comet_pos += 1
        
        self.demarrer_animation(_update, vitesse)
    
    def scanner(
        self,
        couleur='rouge',
        largeur: int = 5,
        vitesse: float = 0.03
    ):
        """Animation scanner (style Knight Rider) (non-bloquante)"""
        self._scan_pos = 0
        self._scan_direction = 1
        rgb = self._parse_couleur(couleur)
        
        def _update():
            for i in range(self.num_leds):
                distance = abs(i - self._scan_pos)
                if distance < largeur:
                    factor = 1 - (distance / largeur)
                    r = int(rgb[0] * factor)
                    g = int(rgb[1] * factor)
                    b = int(rgb[2] * factor)
                    self._strip.setPixelColor(i, self._color_object(r, g, b))
                else:
                    self._strip.setPixelColor(i, self._color_object(0, 0, 0))
            
            self._strip.show()
            
            self._scan_pos += self._scan_direction
            if self._scan_pos >= self.num_leds - 1:
                self._scan_direction = -1
            elif self._scan_pos <= 0:
                self._scan_direction = 1
        
        self.demarrer_animation(_update, vitesse)
    
    def stroboscope(
        self,
        couleur='blanc',
        flashes: int = 3,
        vitesse_flash: float = 0.05,
        pause: float = 0.3
    ):
        """Animation stroboscope (non-bloquante)"""
        self._strobe_count = 0
        self._strobe_state = True
        rgb = self._parse_couleur(couleur)
        
        def _update():
            if self._strobe_count < flashes * 2:
                if self._strobe_count % 2 == 0:
                    for i in range(self.num_leds):
                        self._strip.setPixelColor(i, self._color_object(*rgb))
                else:
                    for i in range(self.num_leds):
                        self._strip.setPixelColor(i, self._color_object(0, 0, 0))
                self._strip.show()
                self._strobe_count += 1
            else:
                self._strobe_count = 0
                time.sleep(pause - vitesse_flash)
        
        self.demarrer_animation(_update, vitesse_flash)
    
    def vague_couleur(
        self,
        couleurs: List = None,
        vitesse: float = 0.05,
        longueur_onde: float = 20
    ):
        """Animation vague de couleurs (non-bloquante)"""
        if couleurs is None:
            couleurs = ['rouge', 'orange', 'jaune', 'vert', 'cyan', 'bleu', 'violet']
        
        self._wave_offset = 0
        parsed = [self._parse_couleur(c) for c in couleurs]
        
        def _update():
            for i in range(self.num_leds):
                pos = (i + self._wave_offset) / longueur_onde
                idx = int(pos) % len(parsed)
                next_idx = (idx + 1) % len(parsed)
                blend = pos % 1
                
                r = int(parsed[idx][0] * (1 - blend) + parsed[next_idx][0] * blend)
                g = int(parsed[idx][1] * (1 - blend) + parsed[next_idx][1] * blend)
                b = int(parsed[idx][2] * (1 - blend) + parsed[next_idx][2] * blend)
                
                self._strip.setPixelColor(i, self._color_object(r, g, b))
            
            self._strip.show()
            self._wave_offset += 1
        
        self.demarrer_animation(_update, vitesse)
    
    def theatre_chase(
        self,
        couleur='blanc',
        couleur_fond='noir',
        espacement: int = 3,
        vitesse: float = 0.1
    ):
        """Animation theatre chase (non-bloquante)"""
        self._theater_offset = 0
        rgb = self._parse_couleur(couleur)
        rgb_bg = self._parse_couleur(couleur_fond)
        
        def _update():
            for i in range(self.num_leds):
                if (i + self._theater_offset) % espacement == 0:
                    self._strip.setPixelColor(i, self._color_object(*rgb))
                else:
                    self._strip.setPixelColor(i, self._color_object(*rgb_bg))
            
            self._strip.show()
            self._theater_offset = (self._theater_offset + 1) % espacement
        
        self.demarrer_animation(_update, vitesse)
    
    def neige(
        self,
        intensite: float = 0.05,
        vitesse: float = 0.05
    ):
        """Animation neige/flocons (non-bloquante)"""
        self._snow = [0.0] * self.num_leds
        
        def _update():
            # Déplacer les flocons vers le bas
            for i in range(self.num_leds - 1, 0, -1):
                self._snow[i] = self._snow[i - 1] * 0.9
            
            # Nouveau flocon aléatoire
            if random.random() < intensite:
                self._snow[0] = 1.0
            else:
                self._snow[0] = 0
            
            # Afficher
            for i in range(self.num_leds):
                val = int(255 * self._snow[i])
                self._strip.setPixelColor(i, self._color_object(val, val, val))
            
            self._strip.show()
        
        self.demarrer_animation(_update, vitesse)
    
    # ===============================================
    # EFFETS BLOQUANTS (SIMPLES)
    # ===============================================
    
    def wipe(
        self,
        couleur,
        delai: float = 0.05,
        inverse: bool = False
    ):
        """Effet wipe/balayage (bloquant)"""
        rgb = self._parse_couleur(couleur)
        indices = range(self.num_leds - 1, -1, -1) if inverse else range(self.num_leds)
        
        for i in indices:
            self._buffer[i] = rgb
            self._strip.setPixelColor(i, self._color_object(*rgb))
            self._strip.show()
            time.sleep(delai)
    
    def fondu_vers(
        self,
        couleur,
        duree: float = 1.0,
        steps: int = 50
    ):
        """Fondu vers une couleur (bloquant)"""
        target_rgb = self._parse_couleur(couleur)
        initial = self._buffer.copy()
        delay = duree / steps
        
        for step in range(steps + 1):
            ratio = step / steps
            for i in range(self.num_leds):
                r = int(initial[i][0] + (target_rgb[0] - initial[i][0]) * ratio)
                g = int(initial[i][1] + (target_rgb[1] - initial[i][1]) * ratio)
                b = int(initial[i][2] + (target_rgb[2] - initial[i][2]) * ratio)
                self._buffer[i] = (r, g, b)
                self._strip.setPixelColor(i, self._color_object(r, g, b))
            self._strip.show()
            time.sleep(delay)
    
    def flash(self, couleur='blanc', duree: float = 0.1, repetitions: int = 1):
        """Flash rapide (bloquant)"""
        rgb = self._parse_couleur(couleur)
        sauvegarde = self._buffer.copy()
        
        for _ in range(repetitions):
            # Flash ON
            for i in range(self.num_leds):
                self._strip.setPixelColor(i, self._color_object(*rgb))
            self._strip.show()
            time.sleep(duree)
            
            # Flash OFF
            for i in range(self.num_leds):
                self._strip.setPixelColor(i, self._color_object(0, 0, 0))
            self._strip.show()
            time.sleep(duree)
        
        # Restaurer
        for i, c in enumerate(sauvegarde):
            self._strip.setPixelColor(i, self._color_object(*c))
        self._strip.show()
    
    # ===============================================
    # SAUVEGARDE / RESTAURATION
    # ===============================================
    
    def sauvegarder_etat(self) -> List[Tuple[int, int, int]]:
        """Sauvegarde l'état actuel"""
        return self._buffer.copy()
    
    def restaurer_etat(self, etat: List[Tuple[int, int, int]]):
        """Restaure un état sauvegardé"""
        for i, rgb in enumerate(etat):
            if i < self.num_leds:
                self._buffer[i] = rgb
                self._strip.setPixelColor(i, self._color_object(*rgb))
        self._strip.show()
    
    # ===============================================
    # UTILITAIRES
    # ===============================================
    
    def inverser(self, auto_afficher: bool = True):
        """Inverse l'ordre des couleurs"""
        self._buffer = self._buffer[::-1]
        for i, rgb in enumerate(self._buffer):
            self._strip.setPixelColor(i, self._color_object(*rgb))
        if auto_afficher:
            self._strip.show()
    
    def rotation(self, positions: int = 1, auto_afficher: bool = True):
        """Effectue une rotation des couleurs"""
        positions = positions % self.num_leds
        self._buffer = self._buffer[-positions:] + self._buffer[:-positions]
        for i, rgb in enumerate(self._buffer):
            self._strip.setPixelColor(i, self._color_object(*rgb))
        if auto_afficher:
            self._strip.show()
    
    def miroir(self, auto_afficher: bool = True):
        """Applique un effet miroir (première moitié copiée sur la seconde)"""
        mid = self.num_leds // 2
        for i in range(mid):
            self._buffer[self.num_leds - 1 - i] = self._buffer[i]
            self._strip.setPixelColor(
                self.num_leds - 1 - i,
                self._color_object(*self._buffer[i])
            )
        if auto_afficher:
            self._strip.show()
    
    def cleanup(self):
        """Nettoie et éteint les LEDs"""
        self.arreter_animation()
        self.tout_eteindre()
    
    def __del__(self):
        """Destructeur"""
        try:
            self.cleanup()
        except:
            pass
    
    def __repr__(self):
        return f"BandeauLED(num_leds={self.num_leds}, pin={self.pin}, lum={self.luminosite})"
    
    def __len__(self):
        return self.num_leds
    
    def __getitem__(self, index):
        return self.get_pixel(index)
    
    def __setitem__(self, index, couleur):
        self.set_pixel(index, couleur)