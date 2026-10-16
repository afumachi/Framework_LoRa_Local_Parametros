/*
  MoT LoRa | Gateway | WissTek IoT | Framework LoRa Local
  Última versão: Branquinho, Felipe e Guilherme (Adaptado para ESP32 - Kit PK-LORa) - 31/08/2026
*/

//=======================================================================
//                     0 - Módulo PKLoRa ESP32 / ESP12E - NodeMCU
//=======================================================================

// Escolha qual o modelo do módulo de processamento de sua PKLoRa
// Deixe sem comentário "//" a linha de sua PKLoRa e comente a outra "//"
#define PKLoRa_ESP32      // Módulo PKLoRa com ESP32
//#define PKLoRa_ESP12E   // Módulo PKLoRa com ESP12E - NodeMCU

// Escolha o modo de conexão do seu Gateway com a Borda N3 S-IoT
// Deixe sem comentário "//" a linha de conexão do Gateway e comente a outra "//"
//#define Gateway_Serial
#define Gateway_MQTT

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================
#include <SPI.h> // A SPI é usada para conectar o ESP32 com o RFM95
#include <LoRa.h> // Biblioteca do RFM95

#if defined(Gateway_MQTT)
  #include <WiFi.h>
  #include <WiFiMulti.h>
  #include <MQTT.h>   // 256dpi/arduino-mqtt -- instalar via Library Manager: "MQTT" by 256dpi
#endif

//=======================================================================
//                     2 - Variáveis e Mapeamento
//=======================================================================

// ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o ESP32
#if defined(PKLoRa_ESP32)

#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26

// Pinos de Saída Digitais (Opcional, mas útil para debug no Gateway)
#define LED_VERMELHO_PIN 15
#define LED_VERDE_PIN     4

#elif defined(PKLoRa_ESP12E)

  // ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o Node-MCU
  #define SCK_PIN   14    // PIN D5
  #define MISO_PIN  12    // PIN D6
  #define MOSI_PIN  13    // PIN D7
  #define NSS_PIN   15    // PIN D8
  #define RST_PIN   0     // PIN D3
  #define DIO0_PIN  5     // PIN D1

  // ============= CAMADA DE APLICAÇÃO
  // Pinos dos LEDs
  #define LED_VERMELHO_PIN  2    // PINO D4
  #define LED_VERDE_PIN     4    // PINO D2
  #define LDR_PIN A0   // ADC1_CH0 — sensor LDR - PIN VP

#endif

// ============= CAMADA FÍSICA
// Parâmetros do LoRa
#define FREQUENCY_IN_HZ       903E6     // Frequência de operação
#define txPower               17        // Potência de transmissão 17 dBm
#define spreadingFactor       7        // Configuração SRC = 7     |  LRC=12
#define signalBandwidth       500E3    // Configuração SRC = 500E3  |  LRC=125E3
#define codingRateDenominator 5         // Configuração SRC = 5     |  LRC=8 


// ============== Variáveis usadas no código do gateway
int RSSI_dBm_UL; // Variável com a potência rádio recebida (RSSI) no UL em dBm medida pelo RFM95
int RSSI_UL; // Variável de mapeamento da RSSI medida em um valor de 0 a 255 para colocar no pacote UL
float SNR_UL; // Variável com a relação sinal ruído de DL
uint8_t SNR_UL_inteiro; // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python
// ============== CAMADA MAC

#define Tamanho_pacote 20

byte PacoteDL[Tamanho_pacote];
byte PacoteUL[Tamanho_pacote];

int ID_gateway;    // Variável com o ID_gateway que estará no pacote de DL byte 10

#if defined(Gateway_MQTT)
// =====================================================================
//                     8 - Variáveis MQTT
// =====================================================================

// =====================================================================
//                     2 - Configurações Wi-Fi
// =====================================================================
// Instancia o objeto WiFiMulti
WiFiMulti wifiMulti;
// --- Objeto Wi-Fi ---
WiFiClient wifiClient;

// =====================================================================
//                     3 - Configurações MQTT
// =====================================================================

// Configurações do Broker Mosquitto (Usando o broker público oficial)
//const char* MQTT_BROKER = "test.mosquitto.org";

// Configurações do Broker HiveMQ (Usando o broker público oficial)
const char* MQTT_BROKER   = "broker.hivemq.com";

const int   MQTT_PORT     = 1883;
const char* TOPIC_DL      = "mot_mqtt_AAF/gateway/downlink";  // Python → ESP32
const char* TOPIC_UL      = "mot_mqtt_AAF/gateway/uplink";    // ESP32  → Python
String CLIENT_ID ;         // ID único no broker através do Endereço MAC do ESP32

// QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
// confirma o recebimento (PUBACK) e a biblioteca retransmite se necessário.
// Importante para o dado do cliente (luminosidade).
const int MQTT_QOS = 1;

// --- Objeto MQTT ---
MQTTClient mqttClient(256);   // buffer de 256 bytes (read/write)

// --- Buffer e flag para o pacote DL recebido via MQTT ---
volatile bool mqtt_dl_disponivel = false;
byte          mqtt_dl_payload[Tamanho_pacote];
#endif

//=======================================================================
//                     3 - Setup de inicialização
//=======================================================================
void setup() {

  //================= INICIALIZA SERIAL
  Serial.begin(115200);

   // Define as funções como OUTPUT dos pinos dos LEDs
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN, OUTPUT);
  
  // Garante que os LEDs iniciem desligados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN, LOW);

#if defined(Gateway_MQTT)
  // Cadastre quantas redes você quiser (SSID, Senha)
  wifiMulti.addAP("COLETTI_ADV_CRIS", "45384609");
  wifiMulti.addAP("MJCA_FUNDOS", "21092429MJC@");
	wifiMulti.addAP("aafwifi", "aaf12345678");
	wifiMulti.addAP("CHACARA BBC", "Ailton1960#");
	wifiMulti.addAP("Claro-EB66", "54b80a7deb66");

  // O wifiMulti.run() tenta conectar a uma das redes cadastradas
  // Ele retorna WL_CONNECTED quando consegue se conectar com sucesso
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Conectado na rede: ");
  Serial.println(WiFi.SSID());
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
#endif

  //-------------------- INICIALIZAÇÃO MÓDULO RF95
  #if defined(PKLoRa_ESP32)
    // --- Inicialização Módulo RF95 (LoRa) ---
     // Inicialização da Comunicação SPI entre o ESP32 e o Módulo LoRa RFM95
     SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  #endif

  // 2. Informa à biblioteca LoRa os pinos de controle
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
  Serial.println("Erro ao iniciar LoRa");
  }
  
  Serial.println("Módulo LoRa iniciado normalmente");
  LoRa.setTxPower(txPower); 
  LoRa.setSpreadingFactor(spreadingFactor); 
  LoRa.setSignalBandwidth(signalBandwidth); 
  LoRa.setCodingRate4(codingRateDenominator); 

  Serial.println("Gateway LoRa Inicializado com Sucesso!");
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

//=======================================================================
//                     4 - Loop de repetição
//=======================================================================
void loop() {

#if defined(Gateway_MQTT)  
  // Mantém conexões ativas
  // No loop, você pode monitorar a conexão.
  // Se a rede cair, o wifiMulti.run() tenta reconectar automaticamente à melhor rede disponível.
  if (wifiMulti.run() != WL_CONNECTED) {
    Serial.println("Conexão perdida! Tentando reconectar...");
    delay(1000);
  }

  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  mqttClient.loop();   // processa envio/recebimento e handshakes de QoS1/2

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();

#elif defined(Gateway_Serial) 

  Phy_serial_receive_DL();

#endif

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker ou na Serial
  Phy_radio_receive_UL();
}