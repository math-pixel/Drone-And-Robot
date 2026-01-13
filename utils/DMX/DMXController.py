from stupidArtnet import StupidArtnet

class DMXController:
    def __init__(self, target_ip="127.0.0.1", packet_rate=30, universe=0):
        self.target_ip = target_ip
        self.packet_rate = packet_rate
        self.default_universe = universe
        self.node = None
        self._init_artnet()
        self.universes = universe

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


    def set(self, channel, value):
        """Définit la valeur d'un canal (1-512) en forçant les types en entier"""
        try:
            # Conversion explicite en entier pour éviter tout problème de type
            c = int(channel)
            v = int(value)

            # Vérification de sécurité
            if 1 <= c <= 512:
                # set_single_value attend (adresse, valeur)
                self.node.set_single_value(c, v)
            else:
                print(f"⚠️ Canal hors limite: {c}")
        except Exception as e:
            print(f"❌ ERREUR dans set: {e}")


    def set_rgb(self, start_channel, color_tuple):
        """Helper pour définir R, G, B de manière sécurisée"""
        # Vérification de sécurité
        if not isinstance(color_tuple, (list, tuple)):
            print(f"❌ ERREUR: color_tuple n'est pas une liste/tuple mais {type(color_tuple)} -> {color_tuple}")
            return

        try:
            r, g, b = color_tuple
            self.set(start_channel + 1, r)
            self.set(start_channel + 2, g)
            self.set(start_channel + 3, b)
        except Exception as e:
            print(f"❌ ERREUR dans set_rgb: {e}")

    def _init_artnet(self):
        # On s'assure que tout est du bon type
        target = str(self.target_ip)
        universe = int(self.default_universe)
        
        # StupidArtnet(ip, universe, packet_size, frame_rate, is_broadcast, enable_loop)
        self.node = StupidArtnet(target, universe, 512, 30, True, True)
        self.node.start()
        print(f"[DMX] Univers {universe} démarré vers {target}")

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
        dmx.set(channel=2, value=127, universe=0)
        
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
        dmx.blackout(universe=1) 
        
        # Petit délai pour être sûr que QLC+ reçoive bien le 0
        time.sleep(0.1) 
        
        # 2. Ensuite on coupe le thread
        dmx.stop()
