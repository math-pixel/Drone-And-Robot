import RPi.GPIO as GPIO
import time

class Servo:
    def __init__(self, pin):
        """Initialise le servo sur le pin GPIO spécifié."""
        self.pin = pin
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pin, 50)  # 50Hz pour servo standard
        self.pwm.start(0)
    
    def set_angle(self, angle):
        """Déplace le servo à l'angle spécifié (0-180 degrés)."""
        angle = max(0, min(180, angle))  # Limite entre 0 et 180
        duty = 2.5 + (angle / 18)  # Conversion angle → duty cycle
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.3)  # Laisse le temps au servo de bouger
        self.pwm.ChangeDutyCycle(0)  # Stop le signal pour éviter les tremblements
    
    def stop(self):
        """Arrête le PWM et nettoie le GPIO."""
        self.pwm.stop()
        GPIO.cleanup(self.pin)

if __name__ == "__main__":
    servo = Servo(pin=17)  # Exemple sur le pin GPIO 17
    try:
        while True:
            angle = float(input("Entrez l'angle (0-180) ou 'q' pour quitter: "))
            servo.set_angle(angle)
    except KeyboardInterrupt:
        pass
    except ValueError:
        print("Sortie du programme.")
    finally:
        servo.stop()