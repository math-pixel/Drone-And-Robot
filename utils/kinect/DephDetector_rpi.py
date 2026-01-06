#!/usr/bin/env python3
import numpy as np

try:
    from pylibfreenect2 import Freenect2, SyncMultiFrameListener
    from pylibfreenect2 import FrameType, CpuPacketPipeline
    FREENECT2_AVAILABLE = True
except ImportError:
    FREENECT2_AVAILABLE = False
    print("⚠️ pylibfreenect2 non installé")


class DepthDetector:
    
    def __init__(self, delegate=None, grid_rows=3, grid_cols=3):
        self.delegate = delegate
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.running = False
        
        # Kinect v2
        self.fn = None
        self.device = None
        self.listener = None
        
    def _init_kinect(self):
        """Initialise la Kinect v2 avec pipeline CPU"""
        if not FREENECT2_AVAILABLE:
            raise RuntimeError("pylibfreenect2 requis : pip3 install pylibfreenect2")
        
        self.fn = Freenect2()
        
        num_devices = self.fn.enumerateDevices()
        if num_devices == 0:
            raise RuntimeError("Aucune Kinect v2 détectée")
        
        serial = self.fn.getDeviceSerialNumber(0)
        print(f"📷 Kinect v2 trouvée : {serial}")
        
        # Pipeline CPU (le plus compatible sur Pi)
        pipeline = CpuPacketPipeline()
        self.device = self.fn.openDevice(serial, pipeline=pipeline)
        
        # Écouter uniquement la profondeur (optimisation)
        self.listener = SyncMultiFrameListener(FrameType.Depth)
        self.device.setIrAndDepthFrameListener(self.listener)
        
        # Démarrer SANS RGB (rgb=False, depth=True)
        self.device.start(False, True)
        print("✅ Kinect v2 démarrée (profondeur uniquement)")
        
    def _compute_grid(self, depth_array):
        """Divise l'image de profondeur en grille et calcule les moyennes"""
        h, w = depth_array.shape
        cell_h = h // self.grid_rows
        cell_w = w // self.grid_cols
        
        grid_values = np.zeros((self.grid_rows, self.grid_cols))
        
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w
                
                cell = depth_array[y1:y2, x1:x2]
                # Filtrer les valeurs invalides (0 = pas de données)
                valid = cell[cell > 0]
                
                if len(valid) > 0:
                    grid_values[i, j] = np.mean(valid)
                else:
                    grid_values[i, j] = 0
                    
        return grid_values
    
    def run(self):
        """Boucle principale - bloquante"""
        print("🚀 Démarrage DepthDetector...")
        
        try:
            self._init_kinect()
        except Exception as e:
            print(f"❌ Erreur init Kinect : {e}")
            return
        
        self.running = True
        
        try:
            while self.running:
                # Attendre une nouvelle frame (timeout 1 seconde)
                frames = self.listener.waitForNewFrame(timeout=1000)
                
                if frames is None:
                    print("⚠️ Timeout frame")
                    continue
                
                try:
                    # Récupérer la frame de profondeur
                    depth_frame = frames[FrameType.Depth]
                    depth_array = depth_frame.asarray(np.float32)
                    
                    # Calculer la grille
                    grid_values = self._compute_grid(depth_array)
                    
                    # Envoyer au delegate
                    if self.delegate is not None:
                        self.delegate.process(grid_values)
                        
                finally:
                    # Toujours libérer les frames
                    self.listener.release(frames)
                    
        except KeyboardInterrupt:
            print("\n⏹️ Arrêt demandé")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête proprement la Kinect"""
        self.running = False
        
        if self.device is not None:
            print("🛑 Arrêt Kinect...")
            self.device.stop()
            self.device.close()
            self.device = None
            print("✅ Kinect arrêtée")