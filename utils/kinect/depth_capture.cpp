#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <iostream>
#include <fstream>
#include <signal.h>
#include <unistd.h>
#include <cstring>

bool running = true;

void sigint_handler(int s) { running = false; }

int main(int argc, char** argv) {
    libfreenect2::Freenect2 freenect2;
    libfreenect2::PacketPipeline* pipeline = new libfreenect2::CpuPacketPipeline();
    
    if (freenect2.enumerateDevices() == 0) {
        std::cerr << "NO_DEVICE" << std::endl;
        return 1;
    }
    
    std::string serial = freenect2.getDefaultDeviceSerialNumber();
    libfreenect2::Freenect2Device* dev = freenect2.openDevice(serial, pipeline);
    
    if (dev == nullptr) {
        std::cerr << "OPEN_FAILED" << std::endl;
        return 1;
    }
    
    signal(SIGINT, sigint_handler);
    
    int types = libfreenect2::Frame::Depth;
    libfreenect2::SyncMultiFrameListener listener(types);
    dev->setIrAndDepthFrameListener(&listener);
    
    if (!dev->startStreams(false, true)) {
        std::cerr << "START_FAILED" << std::endl;
        return 1;
    }
    
    std::cerr << "READY" << std::endl;
    std::cerr << "SERIAL:" << serial << std::endl;
    
    libfreenect2::FrameMap frames;
    
    while (running) {
        if (!listener.waitForNewFrame(frames, 1000)) {
            continue;
        }
        
        libfreenect2::Frame* depth = frames[libfreenect2::Frame::Depth];
        float* data = (float*)depth->data;
        int w = depth->width;   // 512
        int h = depth->height;  // 424
        
        // Envoyer les dimensions une fois
        static bool sent_dims = false;
        if (!sent_dims) {
            std::cerr << "DIMS:" << w << "," << h << std::endl;
            sent_dims = true;
        }
        
        // Envoyer TOUTES les données de profondeur (format binaire serait mieux, 
        // mais pour compatibilité on envoie en texte compressé)
        // Format: RAW:val1,val2,val3,...
        
        std::cout << "FRAME:";
        for (int y = 0; y < h; y += 4) {  // Sous-échantillonnage pour performance
            for (int x = 0; x < w; x += 4) {
                float val = data[y * w + x];
                std::cout << (int)val;
                if (x < w - 4 || y < h - 4) std::cout << ",";
            }
        }
        std::cout << std::endl;
        std::cout.flush();
        
        listener.release(frames);
        
        // ~15 FPS
        usleep(66000);
    }
    
    dev->stop();
    dev->close();
    
    return 0;
}