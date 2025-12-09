#include <ESP8266WiFi.h>
#include <WebSocketsServer.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// --- CONFIGURATION ---
const char* ssid = "TON_SSID_WIFI";
const char* password = "TON_PASSWORD_WIFI";
const int ws_port = 81;

// Configuration du serveur distant (pour la fonction client)
const char* remote_host = "192.168.1.50"; // IP de l'autre serveur WS
const int remote_port = 9000;
const char* remote_path = "/";

class MyWSServer {
private:
    WebSocketsServer server; // L'objet serveur
    WebSocketsClient client; // L'objet client (pour contacter l'autre serveur)
    bool clientConnected = false;

public:
    // Constructeur : initialise le serveur sur le port donné
    MyWSServer(int port) : server(port) {}

    void begin() {
        // 1. Démarrage du serveur
        server.begin();
        // On lie l'événement (callback) à la méthode statique ou via lambda
        // Ici on utilise une lambda pour rester dans l'instance de classe proprement
        server.onEvent([this](uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
            this->serverEvent(num, type, payload, length);
        });

        Serial.printf("[WS] Serveur démarré sur le port %d\n", ws_port);

        // 2. Configuration du client (optionnel, pour l'appel sortant)
        client.begin(remote_host, remote_port, remote_path);
        client.onEvent([this](WStype_t type, uint8_t * payload, size_t length) {
            this->clientEvent(type, payload, length);
        });
        // Note: Le client tentera de se connecter en boucle dans loop()
        // Si tu veux juste envoyer un message ponctuel, la logique serait différente.
        // Ici on garde une connexion permanente pour la rapidité.
        client.setReconnectInterval(5000);
    }

    void loop() {
        server.loop();
        client.loop();
    }

    // --- Méthode pour appeler un autre serveur (en tant que client) ---
    void sendToRemoteServer(String jsonString) {
        if (clientConnected) {
            client.sendTXT(jsonString);
            Serial.println("[CLIENT] Données envoyées au serveur distant.");
        } else {
            Serial.println("[CLIENT] Erreur: Non connecté au serveur distant.");
        }
    }

private:
    // --- Gestionnaire d'événements du SERVEUR ---
    void serverEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
        switch(type) {
            case WStype_DISCONNECTED:
                Serial.printf("[%u] Déconnecté!\n", num);
                break;
            case WStype_CONNECTED:
                {
                    IPAddress ip = server.remoteIP(num);
                    Serial.printf("[%u] Connecté depuis %d.%d.%d.%d\n", num, ip[0], ip[1], ip[2], ip[3]);
                }
                break;
            case WStype_TEXT:
                // 1. Afficher le message brut
                Serial.printf("[%u] Message reçu: %s\n", num, payload);

                // Tentative de parsing JSON
                parseAndProcess(num, payload);
                break;
        }
    }

    // --- Gestionnaire d'événements du CLIENT ---
    void clientEvent(WStype_t type, uint8_t * payload, size_t length) {
        switch(type) {
            case WStype_CONNECTED:
                Serial.println("[CLIENT] Connecté au serveur distant !");
                clientConnected = true;
                break;
            case WStype_DISCONNECTED:
                clientConnected = false;
                break;
        }
    }

    void parseAndProcess(uint8_t clientNum, uint8_t * payload) {
        // Création du document JSON (taille à ajuster selon tes besoins)
        DynamicJsonDocument doc(1024);
        
        DeserializationError error = deserializeJson(doc, payload);

        if (error) {
            // Ce n'est pas du JSON valide, on ignore
            return;
        }

        // 2. Vérification de la condition spécifique
        // On vérifie si la clé "name" existe et vaut "global_data_transfer"
        if (doc["name"] == "global_data_transfer") {
            Serial.println(">>> JSON CIBLE DÉTECTÉ <<<");
            
            // Print le JSON complet (pretty print)
            serializeJsonPretty(doc, Serial);
            Serial.println(); // Saut de ligne

            // 3. Appel de la méthode process
            process(doc, clientNum);
        }
    }

    // --- Méthode PROCESS (Logique métier) ---
    void process(DynamicJsonDocument& doc, uint8_t clientNum) {
        Serial.println("[PROCESS] Traitement des données...");

        // Exemple d'action : Récupérer une valeur
        int value = doc["value"] | 0; // 0 par défaut

        // Action 1 : Répondre au client qui a envoyé le message
        String response = "{\"status\":\"ok\", \"msg\":\"Bien recu sur ESP8266\"}";
        server.sendTXT(clientNum, response);

        // Action 2 : Appeler le serveur distant si demandé dans le JSON
        if (doc["forward"] == true) {
            String dataToForward;
            serializeJson(doc, dataToForward); // On renvoie le même JSON
            sendToRemoteServer(dataToForward);
        }

        // Action 3 : Contrôle DMX (si tu ajoutes la lib DMX ici)
        // int dmxVal = doc["dmx_val"];
        // DMX.write(1, dmxVal);
    }
};

// --- INSTANCIATION ---
MyWSServer myServer(ws_port);

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Connexion WiFi
    Serial.println();
    Serial.print("Connexion à ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connecté");
    Serial.print("Adresse IP: ");
    Serial.println(WiFi.localIP());

    // Démarrage de notre classe Serveur
    myServer.begin();
}

void loop() {
    // La méthode loop de la classe doit être appelée en permanence
    myServer.loop();
}
