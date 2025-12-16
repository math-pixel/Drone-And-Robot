"""
Test Kinect v2 - Python 3.8 32-bit
"""
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2

def main():
    print("=" * 50)
    print("TEST KINECT V2")
    print("=" * 50)
    
    # Initialiser la Kinect
    print("\n[1/3] Initialisation de la Kinect...")
    
    try:
        kinect = PyKinectRuntime.PyKinectRuntime(
            PyKinectV2.FrameSourceTypes_Depth | 
            PyKinectV2.FrameSourceTypes_Color
        )
        print("✅ Kinect initialisée avec succès!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\nVérifiez que:")
        print("  - La Kinect est branchée en USB 3.0")
        print("  - Le SDK Kinect v2 est installé")
        print("  - Les drivers sont à jour")
        return
    
    print("\n[2/3] Démarrage du flux vidéo...")
    print("Appuyez sur 'q' pour quitter\n")
    
    frame_count = 0
    
    while True:
        # === PROFONDEUR ===
        if kinect.has_new_depth_frame():
            depth_frame = kinect.get_last_depth_frame()
            depth_array = depth_frame.reshape((424, 512)).astype(np.float32)
            
            # Distance au centre (en mm)
            center_dist = depth_array[212, 256]
            
            # Normaliser pour affichage
            depth_display = np.uint8(np.clip(depth_array / 4500 * 255, 0, 255))
            depth_color = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
            
            # Afficher la distance
            cv2.putText(depth_color, f"Distance: {int(center_dist)} mm", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Point central
            cv2.circle(depth_color, (256, 212), 5, (255, 255, 255), -1)
            
            cv2.imshow('Profondeur', depth_color)
            frame_count += 1
        
        # === COULEUR ===
        if kinect.has_new_color_frame():
            color_frame = kinect.get_last_color_frame()
            color_array = color_frame.reshape((1080, 1920, 4))
            
            # Redimensionner pour affichage
            color_small = cv2.resize(color_array, (960, 540))
            cv2.imshow('Couleur', color_small)
        
        # Afficher le compteur
        if frame_count % 30 == 0:
            print(f"Frames capturées: {frame_count}", end='\r')
        
        # Quitter
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    print(f"\n\n[3/3] Fermeture... ({frame_count} frames capturées)")
    cv2.destroyAllWindows()
    print("✅ Terminé!")

if __name__ == "__main__":
    main()