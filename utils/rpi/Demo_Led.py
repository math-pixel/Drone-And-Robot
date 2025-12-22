import time
import sys
# On importe la classe que tu as fournie (supposée être dans BandeauLED.py)
from BandeauLED import BandeauLED

# CONFIGURATION
NUM_LEDS = 30        # Nombre de LEDs sur ton ruban
PIN_GPIO = 18        # Pin GPIO (18 est standard pour PWM)
LUMINOSITE = 100     # 0-255 (Attention à la consommation électrique !)

def demo():
    print("=== DÉMARRAGE DU TEST BANDEAU LED ===")
    
    # 1. Initialisation
    # Note : Nécessite sudo pour accéder au PWM/DMA
    strip = BandeauLED(num_leds=NUM_LEDS, pin=PIN_GPIO, luminosite=LUMINOSITE)
    
    try:
        # ==========================================
        # PARTIE 1 : CONTRÔLE BASIQUE (STATIQUE)
        # ==========================================
        print("\n--- Test Couleurs Basiques ---")
        
        print("Rouge")
        strip.tout_allumer('rouge')
        time.sleep(1)
        
        print("Vert")
        strip.tout_allumer('vert')
        time.sleep(1)
        
        print("Bleu")
        strip.tout_allumer('bleu')
        time.sleep(1)
        
        print("Éteint")
        strip.tout_eteindre()
        time.sleep(0.5)

        # ==========================================
        # PARTIE 2 : EFFETS BLOQUANTS (TRANSITIONS)
        # ==========================================
        print("\n--- Test Effets Bloquants ---")
        # Ces effets arrêtent le programme tant qu'ils ne sont pas finis
        
        print("Wipe (Balayage) Orange")
        strip.wipe('orange', delai=0.02)
        
        print("Fondu vers Violet")
        strip.fondu_vers('violet', duree=1.5)
        
        print("Flash Blanc (Alert)")
        strip.flash('blanc', repetitions=3, duree=0.1)

        # ==========================================
        # PARTIE 3 : ANIMATIONS NON-BLOQUANTES
        # ==========================================
        print("\n--- Test Animations (Background) ---")
        # Ces animations tournent dans un thread séparé.
        # Le programme principal continue de s'exécuter !

        # --- EXEMPLE 1 : SCÉNARIO "ATTENTE / REFLEXION" ---
        print("1. Animation Arc-en-ciel (Mode Attente)")
        strip.arc_en_ciel(vitesse=0.01)
        
        # On simule un travail du programme principal pendant 3 secondes
        for i in range(3, 0, -1):
            print(f"   Le programme travaille... {i}")
            time.sleep(1)
            
        # --- EXEMPLE 2 : SCÉNARIO "ACTION / PAROLE" ---
        print("2. Animation Scanner (K2000/Cylon)")
        strip.scanner('rouge', largeur=3, vitesse=0.03)
        time.sleep(4) # Laisser tourner 4 secondes
        
        # --- EXEMPLE 3 : SCÉNARIO "AMBIANCE" ---
        print("3. Animation Feu (Ambiance)")
        strip.feu()
        time.sleep(5)

        # --- EXEMPLE 4 : SCÉNARIO "RESPIRATION" ---
        print("4. Animation Respiration (Mode Veille)")
        strip.respiration('cyan', vitesse=0.05)
        time.sleep(5)

        # --- EXEMPLE 5 : CHANGEMENT DYNAMIQUE ---
        print("5. Test Chenillard rapide")
        strip.chenillard('magenta', couleur_fond='navy', vitesse=0.03)
        time.sleep(3)

    except KeyboardInterrupt:
        print("\nArrêt par l'utilisateur (Ctrl+C)")
    
    finally:
        print("\nNettoyage et extinction...")
        strip.cleanup() # Important pour éteindre proprement
        print("Terminé.")

if __name__ == "__main__":
    demo()