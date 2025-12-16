pip install pylibfreenect2
pip install numpy opencv-python

use python 3.10.6

# Créer l'environnement
C:\Python38-32\python.exe -m venv C:\kinect_env

# Activer
C:\kinect_env\Scripts\activate

# Installer
pip install pykinect2 numpy opencv-python comtypes==1.1.7

# Lancer
python kinect.py

C:\Python38-32\python.exe kinect.py

Bleu foncé  → Proche  (~500 mm = 0.5 m)
Cyan        → ~1500 mm (1.5 m)
Vert        → ~2500 mm (2.5 m)  
Jaune       → ~3500 mm (3.5 m)
Rouge       → Loin    (~4500 mm = 4.5 m)
Noir        → Invalide (0)