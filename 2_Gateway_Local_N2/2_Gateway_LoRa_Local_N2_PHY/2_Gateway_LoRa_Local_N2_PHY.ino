/*
  MoT LoRa | Gateway | WissTek IoT | Framework LoRa Local
  Última versão: Branquinho, Felipe e Guilherme (Adaptado para ESP32 - Kit PK-LORa) - 31/08/2026
*/

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================
#include <SPI.h> // A SPI é usada para conectar o ESP32 com o RFM95
#include <LoRa.h> // Biblioteca do RFM95

//=======================================================================
//                     2 - Variáveis e Mapeamento
//=======================================================================

#define PKLoRa_ESP32

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

#endif

#if defined(PKLoRa_ESP12E)

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
  Phy_serial_receive_DL();
  Phy_radio_receive_UL();
}