/*
//  MoT LoRa | WissTek IoT
//  Versão MQTT com QoS1: comunicação Python N2_N3 ↔ Gateway PKLoRa via broker.hivemq.com
//  - Mantém toda a camada de rádio LoRa (RFM95) do Framework Basic
//  - Substitui USB/Serial por Wi-Fi + MQTT
//  - Usa a biblioteca MQTT by Joel Gaehwiler Vs. 2.5.3 (MQTT.h) para suportar QoS1 (MQTT com ACK)
//
//  Tópicos Publicados no Broker MQTT - broker.hivemq.com
//
//  - DL: assina "mot_lora_SEU_NOME/gateway/downlink"  
//    Gateway LoRa ← realiza leitura via Broker MQTT da publicação do Tópico de Downlink do Python
//
//  - UL: publica em "mot_lora_SEU_NOME/gateway/uplink"
//    Gateway → publica Tópico de Uplink ao Broker MQTT - Python N2_N3 realiza a leitura
//
//
//  Última Modificação: Branquinho / Felipe / Luís Felipe / Anderson - 10/07/2026
//
// Vs.1 - Modificado Broker MQTT de Hivemq para Broker Mosquitto
*/

// =====================================================================
//                     1 - Bibliotecas
// =====================================================================
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <WiFiMulti.h>
#include <MQTT.h>   // 256dpi/arduino-mqtt -- instalar via Library Manager: "MQTT" by 256dpi


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


// =====================================================================
//                     4 - Pinagem RFM95 (Kit PKLORa)
// =====================================================================
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26

// =====================================================================
//                     5 - Parâmetros LoRa
// =====================================================================
#define FREQUENCY_IN_HZ       903E6
#define txPower               17
#define spreadingFactor       7
#define signalBandwidth       500E3
#define codingRateDenominator 5

// =====================================================================
//                     6 - Pinos de LED
// =====================================================================
#define LED_VERMELHO_PIN 15
#define LED_VERDE_PIN     4

// =====================================================================
//                     7 - Variáveis do Gateway
// =====================================================================
#define Tamanho_pacote 20

byte  PacoteDL[Tamanho_pacote];
byte  PacoteUL[Tamanho_pacote];
int   ID_gateway;

int       RSSI_dBm_UL;
int       RSSI_UL;
float     SNR_UL;
uint8_t   SNR_UL_inteiro;
int       Conta_Pacote_DL = 0;
// =====================================================================
//                     8 - Variáveis MQTT
// =====================================================================

// --- Buffer e flag para o pacote DL recebido via MQTT ---
volatile bool mqtt_dl_disponivel = false;
byte          mqtt_dl_payload[Tamanho_pacote];

// =====================================================================
//                    9 - Setup
// =====================================================================
void setup() {
  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

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

  // Declara os pinos dos LEDs como saídas digitais
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN,    OUTPUT);
  // Inicia os LEDs apagados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN,    LOW);

  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");


  // ---------- Inicia MQTT ----------
  mqttClient.begin(MQTT_BROKER, MQTT_PORT, wifiClient);
  mqttClient.onMessageAdvanced(mqtt_callback);
  conectar_mqtt();

  // ---------- Inicia módulo LoRa RFM95 ----------
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("[LoRa] Erro ao iniciar modulo!");
    while (true) { delay(1000); }
  }

  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);

  Serial.println("[LoRa] Gateway inicializado com sucesso!");
  Serial.println("[INFO] Aguardando pacotes DL via MQTT (QoS1)...");

  // Pisca verde 1x → tudo OK
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

// =====================================================================
//                    10 - Loop principal
// =====================================================================
void loop() {

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

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
}
