import sys
import os

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---

# 1. On prend le chemin du fichier actuel (server.py)
current_path = os.path.abspath(__file__)

# 2. On prend le dossier du fichier (serveur/)
current_dir = os.path.dirname(current_path)

# 3. On remonte d'un cran pour avoir le dossier racine (PROJET/)
parent_dir = os.path.dirname(current_dir)

# 4. On ajoute la racine aux chemins de Python
sys.path.append(parent_dir)

# ------------------------------------------

from utils.WSClient import *

import asyncio
import json
import os
import time
import requests
import RPi.GPIO as GPIO

# ============================================================
# 1. CONFIGURATION MATÉRIEL & API
# ============================================================

# GPIO Servo
SERVO_PIN = 18
SERVO_NEUTRAL = 7.5
SERVO_LEFT = 2.5     # Négatif
SERVO_RIGHT = 12.5   # Positif

# Audio
AUDIO_DEVICE = "plughw:1,0" # À adapter via 'arecord -l'
AUDIO_FILE = "/tmp/recording.wav"
RECORD_SECONDS = 5

# URLs (Adapter selon ton setup : Ollama local, OpenAI, etc.)
LLM_URL = "http://localhost:11434/api/generate"  # Ollama
LLM_MODEL = "llama3"
# Pour le STT (Whisper local ou API externe)
# Ici exemple simple avec SpeechRecognition (pip install SpeechRecognition)
USE_SPEECH_RECOGNITION_LIB = True 

# Dictionnaire de sentiments
SENTIMENT_DICT = {
    "je suis nul": "negative",
    "c'est pas grave, je ferai mieux la prochaine fois": "positive",
    "j'abandonne": "negative",
    "je vais y arriver": "positive",
    "je suis content": "positive",
    "c'est horrible": "negative"
}

# Configuration des Steps (tel que demandé)
STEPS = [
    {
        "id": 1, 
        "actions": [
            {
                "id": 101, 
                "type": "activity", 
                "name": "Analyse Vocale Sentiment",
                "finished": False
            }
        ], 
        "authorized": False, 
        "finished": False
    },
]

# ============================================================
# 2. FONCTIONS MATÉRIEL (SERVO & AUDIO)
# ============================================================

def setup_gpio():
    """Initialise le GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(SERVO_NEUTRAL)
    return pwm

def cleanup_gpio(pwm):
    """Nettoyage"""
    pwm.stop()
    GPIO.cleanup()

def move_servo(pwm, sentiment):
    """Bouge le servo selon le résultat"""
    print(f"⚙️  Servo Mouvement pour: {sentiment}")
    
    if sentiment == "positive":
        target = SERVO_RIGHT
    elif sentiment == "negative":
        target = SERVO_LEFT
    else:
        target = SERVO_NEUTRAL # Neutre si inconnu
        
    pwm.ChangeDutyCycle(target)
    time.sleep(1.0) # Laisser le temps au servo d'arriver
    
    # Retour au neutre
    pwm.ChangeDutyCycle(SERVO_NEUTRAL)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0) # Couper le signal pour éviter le bruit

def record_audio_sync():
    """Enregistrement bloquant (sera exécuté dans un thread)"""
    print(f"🎤 Enregistrement ({RECORD_SECONDS}s)...")
    cmd = f"arecord -D {AUDIO_DEVICE} -f S16_LE -r 16000 -c 1 -d {RECORD_SECONDS} {AUDIO_FILE} 2>/dev/null"
    os.system(cmd)
    print("✅ Enregistrement terminé.")
    return AUDIO_FILE

# ============================================================
# 3. INTELLIGENCE (STT & LLM)
# ============================================================

def transcribe_audio_sync(audio_path):
    """Transcription Audio -> Texte"""
    print("📝 Transcription en cours...")
    
    # Méthode simple avec SpeechRecognition (Google Free API)
    # Sinon faire une requête HTTP vers ton serveur Whisper ici
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="fr-FR")
        print(f"🗣️  Texte entendu : \"{text}\"")
        return text
    except Exception as e:
        print(f"❌ Erreur STT: {e}")
        return ""

def analyze_sentiment_sync(text):
    """Requête LLM pour analyser le sentiment"""
    print(f"🤖 Analyse LLM pour : \"{text}\"")
    
    dict_str = json.dumps(SENTIMENT_DICT, ensure_ascii=False)
    prompt = f"""Analyse le sentiment de cette phrase prononcée : "{text}".
    Utilise ce dictionnaire comme référence de ton : {dict_str}.
    Si la phrase ressemble à du positif, réponds juste "positive".
    Si c'est négatif, réponds juste "negative".
    Si tu ne sais pas, réponds "unknown".
    Réponds UNIQUEMENT par le mot clé."""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        # Adapter l'URL et le format selon ton serveur LLM (Ollama, OpenAI, etc)
        response = requests.post(LLM_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json().get('response', '').strip().lower()
            # Nettoyage basique
            if "positive" in result: return "positive"
            if "negative" in result: return "negative"
            return "unknown"
    except Exception as e:
        print(f"❌ Erreur LLM: {e}")
        
    return "unknown"

# ============================================================
# 4. LOGIQUE MÉTIER "ACTIVITY"
# ============================================================

def run_activity_logic(pwm):
    """
    Exécute toute la logique de manière synchrone.
    Sera appelée via to_thread pour ne pas bloquer le WebSocket.
    """
    # 1. Enregistrer
    path = record_audio_sync()
    
    # 2. Transcrire
    text = transcribe_audio_sync(path)
    
    if not text:
        print("⚠️ Pas de voix détectée.")
        return "no_voice"
        
    # 3. Analyser
    sentiment = analyze_sentiment_sync(text)
    print(f"💡 Sentiment détecté : {sentiment}")
    
    # 4. Actionner
    move_servo(pwm, sentiment)
    
    return sentiment

# ============================================================
# 5. WEBSOCKET HANDLER
# ============================================================

# Variable globale pour le PWM (pour y accéder dans le handler)
pwm_global = None

async def my_action_handler(action: dict, client: WSClient, step_id: int):
    """
    Delegate appelé par le WSClient quand une action arrive
    """
    global pwm_global
    
    action_id = action.get("id")
    action_type = action.get("type")
    
    print(f"\n📥 Action Reçue : {action_type} (ID: {action_id})")

    if action_type == "activity":
        print("▶️ Démarrage de l'activité Vocale...")
        
        # Exécuter la logique lourde dans un thread séparé pour ne pas couper le WS
        # run_activity_logic contient (Record -> STT -> LLM -> Servo)
        result_sentiment = await asyncio.to_thread(run_activity_logic, pwm_global)
        
        print(f"✅ Activité terminée. Résultat : {result_sentiment}")
        
        # Mettre à jour l'action locale (optionnel)
        action["finished"] = True
        action["result"] = result_sentiment
        
        # Renvoyer au serveur que c'est fini
        # On adapte selon la méthode disponible dans ta classe WSClient
        # Si tu as une méthode générique 'send_action_update' ou similaire :
        if hasattr(client, 'send_choice_result'):
            # On détourne send_choice_result pour renvoyer le résultat, 
            # ou tu crées une méthode send_action_finished(step_id, action_id, data)
            await client.send_choice_result(step_id, action_id, result_sentiment)
        else:
            print("⚠️ Aucune méthode d'envoi trouvée sur le client (ex: send_choice_result)")

    elif action_type == "choice":
        # Ta logique bouton existante...
        pass
        
    else:
        print(f"⚠️ Type d'action inconnu : {action_type}")

# ============================================================
# 6. MAIN
# ============================================================

async def main():
    global pwm_global
    
    # 1. Init Hardware
    print("🔌 Initialisation GPIO...")
    pwm_global = setup_gpio()
    
    # 2. Init Client WS
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="voice_activity_client",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    
    try:
        # 3. Lancer le client
        await client.run()
    except Exception as e:
        print(f"🔥 Crash Main: {e}")
    finally:
        # 4. Cleanup
        print("👋 Arrêt et nettoyage GPIO")
        cleanup_gpio(pwm_global)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass