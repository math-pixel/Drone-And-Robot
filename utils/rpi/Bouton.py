import RPi.GPIO as GPIO
import time
import threading


class Bouton:
    """
    Classe pour gérer un bouton sur Raspberry Pi avec RPi.GPIO
    Supporte: appui simple, appui long, double-clic, callbacks
    """
    
    def __init__(self, pin, pull_up=True, bounce_time=200, long_press_time=1.0):
        """
        Initialise le bouton
        
        Args:
            pin: Numéro GPIO (mode BCM)
            pull_up: True pour pull-up, False pour pull-down
            bounce_time: Anti-rebond en millisecondes
            long_press_time: Durée appui long en secondes
        """
        self.pin = pin
        self.bounce_time = bounce_time
        self.long_press_time = long_press_time
        self.pull_up = pull_up
        
        # État interne
        self._pressed_time = 0
        self._last_press_time = 0
        self._press_count = 0
        self._is_held = False
        
        # Callbacks
        self._on_press = None
        self._on_release = None
        self._on_long_press = None
        self._on_double_click = None
        
        # Thread pour appui long
        self._hold_timer = None
        self._lock = threading.Lock()
        
        # Configuration GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)
        
        # Détection événements
        edge = GPIO.FALLING if pull_up else GPIO.RISING
        GPIO.add_event_detect(
            self.pin, 
            GPIO.BOTH, 
            callback=self._handle_event, 
            bouncetime=self.bounce_time
        )
    
    # =========== PROPRIÉTÉS ===========
    
    @property
    def is_pressed(self):
        """Retourne True si le bouton est actuellement appuyé"""
        state = GPIO.input(self.pin)
        return state == GPIO.LOW if self.pull_up else state == GPIO.HIGH
    
    @property
    def is_held(self):
        """Retourne True si le bouton est maintenu (appui long)"""
        return self._is_held
    
    @property
    def value(self):
        """Retourne 1 si appuyé, 0 sinon"""
        return 1 if self.is_pressed else 0
    
    # =========== CALLBACKS ===========
    
    @property
    def on_press(self):
        return self._on_press
    
    @on_press.setter
    def on_press(self, callback):
        """Définit le callback pour l'appui"""
        self._on_press = callback
    
    @property
    def on_release(self):
        return self._on_release
    
    @on_release.setter
    def on_release(self, callback):
        """Définit le callback pour le relâchement"""
        self._on_release = callback
    
    @property
    def on_long_press(self):
        return self._on_long_press
    
    @on_long_press.setter
    def on_long_press(self, callback):
        """Définit le callback pour l'appui long"""
        self._on_long_press = callback
    
    @property
    def on_double_click(self):
        return self._on_double_click
    
    @on_double_click.setter
    def on_double_click(self, callback):
        """Définit le callback pour le double-clic"""
        self._on_double_click = callback
    
    # =========== GESTION ÉVÉNEMENTS ===========
    
    def _handle_event(self, channel):
        """Gère les événements du bouton"""
        with self._lock:
            if self.is_pressed:
                self._handle_press()
            else:
                self._handle_release()
    
    def _handle_press(self):
        """Gère l'appui sur le bouton"""
        current_time = time.time()
        self._pressed_time = current_time
        
        # Détection double-clic
        if current_time - self._last_press_time < 0.4:
            self._press_count += 1
            if self._press_count >= 2 and self._on_double_click:
                self._on_double_click()
                self._press_count = 0
        else:
            self._press_count = 1
        
        self._last_press_time = current_time
        
        # Callback appui simple
        if self._on_press:
            self._on_press()
        
        # Timer pour appui long
        if self._on_long_press:
            self._cancel_hold_timer()
            self._hold_timer = threading.Timer(
                self.long_press_time, 
                self._handle_long_press
            )
            self._hold_timer.start()
    
    def _handle_release(self):
        """Gère le relâchement du bouton"""
        self._cancel_hold_timer()
        self._is_held = False
        
        # Calcul durée d'appui
        press_duration = time.time() - self._pressed_time
        
        if self._on_release:
            self._on_release(press_duration)
    
    def _handle_long_press(self):
        """Gère l'appui long"""
        if self.is_pressed:
            self._is_held = True
            if self._on_long_press:
                self._on_long_press()
    
    def _cancel_hold_timer(self):
        """Annule le timer d'appui long"""
        if self._hold_timer:
            self._hold_timer.cancel()
            self._hold_timer = None
    
    # =========== MÉTHODES UTILITAIRES ===========
    
    def wait_for_press(self, timeout=None):
        """
        Attend un appui sur le bouton
        
        Args:
            timeout: Délai max en secondes (None = infini)
        
        Returns:
            True si appuyé, False si timeout
        """
        start = time.time()
        while True:
            if self.is_pressed:
                return True
            if timeout and (time.time() - start) >= timeout:
                return False
            time.sleep(0.01)
    
    def wait_for_release(self, timeout=None):
        """
        Attend le relâchement du bouton
        
        Args:
            timeout: Délai max en secondes (None = infini)
        
        Returns:
            True si relâché, False si timeout
        """
        start = time.time()
        while True:
            if not self.is_pressed:
                return True
            if timeout and (time.time() - start) >= timeout:
                return False
            time.sleep(0.01)
    
    def cleanup(self):
        """Nettoie les ressources GPIO"""
        self._cancel_hold_timer()
        GPIO.remove_event_detect(self.pin)
        GPIO.cleanup(self.pin)
    
    def __del__(self):
        """Destructeur"""
        try:
            self.cleanup()
        except:
            pass
    
    def __repr__(self):
        state = "appuyé" if self.is_pressed else "relâché"
        return f"Bouton(pin={self.pin}, état={state})"