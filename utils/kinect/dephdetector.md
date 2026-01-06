# 1. Créer le fichier C++
nano ~/PROJET/utils/kinect/depth_capture.cpp

# 2. Compiler
g++ -std=c++11 \
    ~/PROJET/utils/kinect/depth_capture.cpp \
    -o ~/PROJET/utils/kinect/depth_capture \
    -I/usr/local/include \
    -L/usr/local/lib \
    -lfreenect2 \
    -lpthread

# 3. Remplacer DephDetector.py
nano ~/PROJET/utils/kinect/DephDetector.py

# 4. Tester avec affichage
python3 ~/PROJET/utils/kinect/DephDetector.py

# 5. Ou lancer ton serveur (mode headless)
python3 ~/PROJET/serveur/server.py


# Avant
depth_detector.run()

# Après (pour mode sans affichage)
depth_detector.run_headless()