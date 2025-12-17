pip install pylibfreenect2
pip install numpy opencv-python

use python 3.8.6

# Créer l'environnement
C:\Python38-32\python.exe -m venv C:\kinect_env

# Activer
C:\kinect_env\Scripts\activate

# Installer
pip install pykinect2 numpy opencv-python comtypes==1.1.7

# Patcher pykinect2 pour time.clock
python -c "import os; import pykinect2; p=os.path.join(pykinect2.__path__[0],'PyKinectRuntime.py'); f=open(p,'r'); c=f.read(); f.close(); c=c.replace('time.clock','time.perf_counter'); f=open(p,'w'); f.write(c); f.close(); print('Patch OK!')"

# Lancer
python kinect.py

C:\Python38-32\python.exe kinect.py

Bleu foncé  → Proche  (~500 mm = 0.5 m)
Cyan        → ~1500 mm (1.5 m)
Vert        → ~2500 mm (2.5 m)  
Jaune       → ~3500 mm (3.5 m)
Rouge       → Loin    (~4500 mm = 4.5 m)
Noir        → Invalide (0)

🎹 Contrôles
Touche	Action
Flèches ou ZQSD	Déplacer la grille
+ / -	Ajouter/retirer colonnes
***** / /	Ajouter/retirer lignes
I / K	Augmenter/diminuer largeur cellule
L / J	Augmenter/diminuer hauteur cellule
ESPACE	Sauvegarder config JSON
C	Sauvegarder capture PNG + CSV
R	Reset aux valeurs par défaut
Q ou Echap	Quitter

Touche	Action
T	Activer/Désactiver la détection
[ / ]	Diminuer/Augmenter le seuil (±10mm)
{ / }	Diminuer/Augmenter la durée d'alerte (±0.1s)

grid_config.json
{
    "start_x": 100,
    "start_y": 80,
    "cols": 6,
    "rows": 5,
    "cell_w": 70,
    "cell_h": 60,
    "grid_color": [0, 255, 0],
    "text_color": [255, 255, 255],
    "bg_color": [0, 0, 0]
}