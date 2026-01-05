import sounddevice as sd
import numpy as np
import whisper
import threading
import queue
import time

class WhisperStreamSTT:
    """STT Streaming avec Whisper + détection de phrases"""
    
    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
        self.sample_rate = 16000
        self.chunk_duration = 2.0  # Whisper fonctionne mieux avec des chunks plus longs
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        # Buffer audio glissant
        self.audio_buffer = np.array([], dtype=np.float32)
        self.max_buffer_duration = 30  # secondes
        self.max_buffer_size = self.sample_rate * self.max_buffer_duration
        
        self.last_transcription = ""
        self.phrases = []
    
    def _audio_callback(self, indata, frames, time_info, status):
        self.audio_queue.put(indata.copy().flatten())
    
    def _detect_new_phrase(self, old_text: str, new_text: str) -> str | None:
        """Détecte si une nouvelle phrase est apparue"""
        if len(new_text) > len(old_text):
            # Chercher des fins de phrases
            endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
            
            for ending in endings:
                old_end = old_text.rfind(ending)
                new_end = new_text.rfind(ending)
                
                if new_end > old_end and new_end > -1:
                    # Nouvelle phrase complète
                    start = old_end + len(ending) if old_end > -1 else 0
                    phrase = new_text[start:new_end + 1].strip()
                    if phrase:
                        return phrase
        return None
    
    def _process_audio(self):
        """Thread de traitement"""
        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                
                # Ajouter au buffer
                self.audio_buffer = np.concatenate([self.audio_buffer, chunk])
                
                # Limiter la taille du buffer
                if len(self.audio_buffer) > self.max_buffer_size:
                    self.audio_buffer = self.audio_buffer[-self.max_buffer_size:]
                
                # Transcrire si assez d'audio
                if len(self.audio_buffer) >= self.chunk_size:
                    result = self.model.transcribe(
                        self.audio_buffer,
                        language="fr",
                        fp16=False
                    )
                    
                    new_text = result["text"].strip()
                    
                    # Afficher en temps réel
                    print(f"\r🎤 {new_text[-80:]}", end="", flush=True)
                    
                    # Détecter nouvelle phrase
                    phrase = self._detect_new_phrase(self.last_transcription, new_text)
                    if phrase:
                        self.phrases.append(phrase)
                        print(f"\n\n✅ PHRASE DÉTECTÉE: \"{phrase}\"\n")
                    
                    self.last_transcription = new_text
                    
            except queue.Empty:
                continue
    
    def start(self):
        """Démarre l'écoute"""
        self.is_running = True
        
        self.process_thread = threading.Thread(target=self._process_audio)
        self.process_thread.start()
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=int(self.sample_rate * 0.5),  # 500ms chunks
            callback=self._audio_callback
        )
        self.stream.start()
        
        print("🎤 Parlez maintenant... (Ctrl+C pour arrêter)\n")
    
    def stop(self):
        self.is_running = False
        self.stream.stop()
        self.stream.close()
        self.process_thread.join()
        return self.phrases


# Utilisation
if __name__ == "__main__":
    stt = WhisperStreamSTT(model_size="small")  # tiny, base, small, medium, large
    print("Initialisation du modèle Whisper...")
    try:
        stt.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        phrases = stt.stop()
        print(f"\n\n📝 {len(phrases)} phrases détectées:")
        for i, p in enumerate(phrases, 1):
            print(f"  {i}. {p}")