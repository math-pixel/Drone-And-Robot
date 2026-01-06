#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <iostream>
#include <fstream>
#include <signal.h>
#include <unistd.h>

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
    
    // Profondeur uniquement
    int types = libfreenect2::Frame::Depth;
    libfreenect2::SyncMultiFrameListener listener(types);
    dev->setIrAndDepthFrameListener(&listener);
    
    // Démarrer sans RGB
    if (!dev->startStreams(false, true)) {
        std::cerr << "START_FAILED" << std::endl;
        return 1;
    }
    
    std::cerr << "READY" << std::endl;
    
    libfreenect2::FrameMap frames;
    
    while (running) {
        if (!listener.waitForNewFrame(frames, 1000)) {
            continue;
        }
        
        libfreenect2::Frame* depth = frames[libfreenect2::Frame::Depth];
        float* data = (float*)depth->data;
        
        // Grille 3x3 - calcul des moyennes
        int w = depth->width;   // 512
        int h = depth->height;  // 424
        int cell_w = w / 3;
        int cell_h = h / 3;
        
        for (int row = 0; row < 3; row++) {
            for (int col = 0; col < 3; col++) {
                float sum = 0;
                int count = 0;
                
                int y1 = row * cell_h;
                int y2 = (row + 1) * cell_h;
                int x1 = col * cell_w;
                int x2 = (col + 1) * cell_w;
                
                for (int y = y1; y < y2; y++) {
                    for (int x = x1; x < x2; x++) {
                        float val = data[y * w + x];
                        if (val > 0) {
                            sum += val;
                            count++;
                        }
                    }
                }
                
                float avg = (count > 0) ? (sum / count) : 0;
                std::cout << avg;
                if (col < 2) std::cout << ",";
            }
            std::cout << ";";
        }
        std::cout << std::endl;
        std::cout.flush();
        
        listener.release(frames);
        
        // ~10 FPS
        usleep(100000);
    }
    
    dev->stop();
    dev->close();
    
    return 0;
}