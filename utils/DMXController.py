from stupidArtnet import StupidArtnet

class DMXController:
    def __init__(self, target_ip="127.0.0.1", packet_rate=30):
        """
        target_ip: L'adresse IP du nœud DMX ou du logiciel de lumière (ex: Resolume, GrandMA, ou localhost).
        packet_rate: Nombre de paquets par seconde (Hz).
        """
        self.target_ip = target_ip
        self.packet_rate = packet_rate
        self.universes = {} # Dictionnaire pour stocker les objets ArtNet par univers

    def _get_or_create_universe(self, universe_id):
        """Initialise un nouvel univers s'il n'existe pas encore."""
        if universe_id not in self.universes:
            # Création de l'objet ArtNet pour cet univers (512 canaux)
            # StupidArtnet(ip, universe, packet_size, frame_rate, is_broadcast, enable_loop)
            artnet_node = StupidArtnet(self.target_ip, universe_id, 512, self.packet_rate, True, True)
            # artnet_node = StupidArtnet(self.target_ip, universe_id, 512, self.packet_rate, False, True)
            artnet_node.start() # Démarre le thread d'envoi continu
            self.universes[universe_id] = artnet_node
            print(f"[DMX] Univers {universe_id} initialisé vers {self.target_ip}")
        
        return self.universes[universe_id]

    def set(self, channel, value, universe=1):
        """
        Définit la valeur DMX pour un canal spécifique.
        
        :param channel: Canal DMX (1 à 512)
        :param value: Valeur DMX (0 à 255)
        :param universe: L'univers DMX (défaut 1)
        """
        # 1. Validation des entrées
        if not (1 <= channel <= 512):
            print(f"[ERREUR] Le canal {channel} est invalide (doit être entre 1 et 512).")
            return
        if not (0 <= value <= 255):
            print(f"[ERREUR] La valeur {value} est invalide (doit être entre 0 et 255).")
            return

        # 2. Récupération de l'univers
        node = self._get_or_create_universe(universe)

        # 3. Application de la valeur
        # Note: StupidArtnet utilise des index commençant à 1 pour set_single_value, 
        # donc ça correspond parfaitement à ta demande.
        try:
            node.set_single_value(channel, value)
            # Optionnel : log pour debug
            print(f"[DMX] U:{universe} | Ch:{channel} -> {value}")
        except Exception as e:
            print(f"[ERREUR DMX] {e}")

    def blackout(self, universe=1):
        """Met tout l'univers à 0."""
        if universe in self.universes:
            self.universes[universe].blackout()
            print(f"[DMX] Blackout sur univers {universe}")

    def stop(self):
        """Arrête proprement tous les threads d'envoi."""
        for u_id, node in self.universes.items():
            node.stop()
        print("[DMX] Contrôleur arrêté.")

# --- Exemple d'utilisation ---
if __name__ == "__main__":
    import time
    
    # Initialisation (target_ip="127.0.0.1" pour tester en local)
    dmx = DMXController(target_ip="127.0.0.1")

    try:
        print("Envoi de DMX...")
        
        # Allumer le canal 1 à fond sur l'univers 1
        dmx.set(channel=1, value=255, universe=0)
        
        # Mettre le canal 10 à 50% sur l'univers 2
        dmx.set(channel=10, value=127, universe=2)
        
        # Petit effet chenillard simple pour tester
        # for i in range(1, 10):
        #     dmx.set(i, 255)
        #     time.sleep(0.2)
        #     dmx.set(i, 0)

        print("Appuyez Ctrl+C pour arrêter...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    finally:
        dmx.stop()
