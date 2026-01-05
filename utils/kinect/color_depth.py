from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2

kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)

print("Analyse des valeurs de profondeur")
print("Appuyez sur 'q' pour quitter\n")

while True:
    if kinect.has_new_depth_frame():
        # Récupérer les données brutes
        depth_frame = kinect.get_last_depth_frame()
        depth_array = depth_frame.reshape((424, 512)).astype(np.uint16)
        
        # === STATISTIQUES ===
        valid_mask = (depth_array > 0) & (depth_array < 8000)
        valid_depths = depth_array[valid_mask]
        
        if len(valid_depths) > 0:
            min_dist = np.min(valid_depths)
            max_dist = np.max(valid_depths)
            mean_dist = np.mean(valid_depths)
            center_dist = depth_array[212, 256]
            
            print(f"Min: {min_dist:5d} mm | "
                  f"Max: {max_dist:5d} mm | "
                  f"Moyenne: {mean_dist:7.1f} mm | "
                  f"Centre: {center_dist:5d} mm", end='\r')
        
        # === AFFICHAGE ===
        # Normaliser entre 500-4500mm pour affichage optimal
        depth_display = np.clip(depth_array, 500, 4500)
        depth_display = ((depth_display - 500) / 4000 * 255).astype(np.uint8)
        depth_color = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
        
        # Marquer les zones invalides en noir
        depth_color[depth_array == 0] = [0, 0, 0]
        
        # Point central
        cv2.circle(depth_color, (256, 212), 5, (255, 255, 255), 2)
        
        cv2.imshow('Profondeur', depth_color)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()