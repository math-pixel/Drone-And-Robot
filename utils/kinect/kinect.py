import numpy as np
import cv2
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame

def main():
    # Initialisation
    fn = Freenect2()
    num_devices = fn.enumerateDevices()
    
    if num_devices == 0:
        print("Aucune Kinect détectée!")
        return
    
    serial = fn.getDeviceSerialNumber(0)
    device = fn.openDevice(serial)
    
    # Configurer le listener
    listener = SyncMultiFrameListener(
        FrameType.Color | FrameType.Depth | FrameType.Ir
    )
    
    device.setColorFrameListener(listener)
    device.setIrAndDepthFrameListener(listener)
    device.start()
    
    # Registration pour aligner couleur et profondeur
    registration = Registration(device.getIrCameraParams(),
                                device.getColorCameraParams())
    
    print("Kinect v2 démarrée. Appuyez sur 'q' pour quitter.")
    
    try:
        while True:
            frames = listener.waitForNewFrame()
            
            # Récupérer les frames
            color = frames["color"]
            depth = frames["depth"]
            ir = frames["ir"]
            
            # Convertir en arrays numpy
            depth_array = depth.asarray() / 4500.0  # Normaliser (max ~4.5m)
            color_array = color.asarray()
            ir_array = ir.asarray() / 65535.0
            
            # Affichage
            depth_display = np.uint8(depth_array * 255)
            depth_colormap = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
            
            cv2.imshow('Profondeur', depth_colormap)
            cv2.imshow('Couleur', color_array)
            cv2.imshow('Infrarouge', ir_array)
            
            listener.release(frames)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        device.stop()
        device.close()
        cv2.destroyAllWindows()

import numpy as np
from pyk4a import PyK4A

def get_point_cloud(k4a):
    """Génère un nuage de points 3D à partir de la profondeur"""
    capture = k4a.get_capture()
    
    if capture.depth is not None:
        # Obtenir le nuage de points (X, Y, Z pour chaque pixel)
        points = capture.transformed_depth_point_cloud
        
        # Reshape en liste de points (N, 3)
        points_3d = points.reshape(-1, 3)
        
        # Filtrer les points invalides (z = 0)
        valid_points = points_3d[points_3d[:, 2] > 0]
        
        return valid_points
    
    return None

# Sauvegarder en format PLY
def save_ply(points, filename):
    with open(filename, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("end_header\n")
        for p in points:
            f.write(f"{p[0]} {p[1]} {p[2]}\n")

if __name__ == "__main__":
    main()