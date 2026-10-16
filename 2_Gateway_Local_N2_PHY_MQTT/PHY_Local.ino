//======================= PACOTE DOWN LINK - PACOTE VINDO DO PYTHON PARA SER ENVIADO AO NÓ SENSOR ===========================
#if defined(Gateway_Serial) 
// =========== CAMADA FÍSICA (PHY) GATEWAY - recebe pacote pela USB
void Phy_serial_receive_DL() {
  
  if (Serial.available() >= Tamanho_pacote) {  // Testa se tem 52 bytes na serial

    for (byte i = 0; i < Tamanho_pacote; i++)  // PacoteUL[#] é preenchido com zero e PacoteDL[#] recebe os bytes do buffer
    {
      PacoteDL[i] = Serial.read();  // Recebe os bytes do buffer para o pacote de transmissão
    }
  ID_gateway = PacoteDL[10]; // Identifica que gateway que está enviando o pacote de DL

// ==== CHAMA CAMADA FÍSICA PARA TRANSMITIR PACOTE PELO RFM95
    Phy_radio_send_DL();  // chama a funcao de envio da camada física
  }
}

#elif defined(Gateway_MQTT) 
// ========================= PACOTE DOWNLINK ==========================
// Recebe pacote DL do broker MQTT (publicado pelo Python)
void Phy_mqtt_receive_DL() {

  if (mqtt_dl_disponivel) {          // Flag setada no callback MQTT
    mqtt_dl_disponivel = false;

    // Copia payload recebido para PacoteDL
    for (int i = 0; i < Tamanho_pacote; i++) {
      PacoteDL[i] = mqtt_dl_payload[i];
    }
    ID_gateway = PacoteDL[10];       // Identifica o gateway

    Serial.println("[PHY] Pacote DL recebido via MQTT.");

    // Chama camada física para transmitir pelo rádio RFM95
    Phy_radio_send_DL();
  }
}
#endif

//========================= ENVIA PACOTE DL PARA NÓ SENSOR ATRAVÉS DO RF95
//O pacote DL recebido pela serial proveniente do Nível 3 é enviado para o RF95
void Phy_radio_send_DL() {

  digitalWrite(LED_VERMELHO_PIN, HIGH);  
  LoRa.beginPacket();                   // start packet
  for (int i = 0; i < Tamanho_pacote; i++) {
    LoRa.write(PacoteDL[i]);            // add data to packet

  }
  LoRa.endPacket();                     // finish packet and send it
 
  // Pisca LED Vermelho do Kit PKLORa indicando Transmissão de Pacote DL (TX) para o Nó Sensor LoRa
  
  delay(20);                            
  digitalWrite(LED_VERMELHO_PIN, LOW);   

}

//======================= RECEBE PACOTE UL LINK - PACODE VINDO NÓ SENSOR para o gateway===========================
// Recebe o pacote UL que chegou no RFM95
void Phy_radio_receive_UL() {

  uint8_t packetSize = LoRa.parsePacket();

  if (packetSize > 0) {
    if (packetSize >= Tamanho_pacote) {
      // Liga LED Verde indicando Recepção
      digitalWrite(LED_VERDE_PIN, HIGH);

      for (int i = 0; i < Tamanho_pacote; i++) {
        PacoteUL[i] = LoRa.read();
      }
      
      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL = LoRa.packetSnr();

      // Pisca LED Verde do Kit PKLORa indicando Recepção de Pacote UL (RX) - se permitido
      delay(50);
      digitalWrite(LED_VERDE_PIN, LOW);

      #if defined(Gateway_Serial)
        // CHAMA CAMADA FÍSICA DE UL
        Phy_serial_send_UL();  //Chama a função de envio da Camada Física 
      #elif defined(Gateway_MQTT)
        Phy_mqtt_send_UL();
      #endif
    }
  }
}

#if defined(Gateway_Serial)
//===================== PACOTE UL
void Phy_serial_send_UL() { // Funcao de envio de pacote de UL para o computador via buffer TX da serial do ESP32
//--- Bloco que faz adequação da leitura de RSSI para um byte ---
  if(RSSI_dBm_UL > -10.5) {  // Caso a RSSI medida esteja acima do valor superior -10,5 dBm
   RSSI_UL = 127; // equivalente a -10,5 dBm 
  }

  if(RSSI_dBm_UL <= -10.5 && RSSI_dBm_UL >= -74) {// Caso a RSSI medida esteja no intervalo [-10,5 dBm e -74 dBm]
   RSSI_UL = ((RSSI_dBm_UL +74)*2) ;
  }

  if(RSSI_dBm_UL < -74) {// Caso a RSSI medida esteja no intervalo ]-74 dBm e -138 dBm]
   RSSI_UL = (((RSSI_dBm_UL +74)*2)+256) ;
  }

  // Manter o valor entre -30 e +30
   if (SNR_UL < -30.0) SNR_UL = -30.0;
   if (SNR_UL > 30.0) SNR_UL = 30.0;

  SNR_UL_inteiro = (uint8_t)round((SNR_UL + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)
  // =================Informações de gerência do pacote
  PacoteUL[2] = RSSI_UL;  // aloca RSSI_UL
  PacoteUL[3] = (byte)SNR_UL_inteiro;
  
  // Transmissão do pacote pela serial do ESP32 para o script em Python
  for (int i = 0; i < Tamanho_pacote; i++) {
    Serial.write(PacoteUL[i]);
  }

}

#elif defined(Gateway_MQTT) 
// ==================== PUBLICA PACOTE UL NO BROKER MQTT ==============
// Substitui Phy_serial_send_UL(): envia o pacote UL ao Python via MQTT
void Phy_mqtt_send_UL() {

  // --- Mapeia RSSI_UL para 1 byte (mesma lógica da versão serial) ---
  if (RSSI_dBm_UL > -10.5) {
    RSSI_UL = 127;
  } else if (RSSI_dBm_UL <= -10.5 && RSSI_dBm_UL >= -74) {
    RSSI_UL = (int)((RSSI_dBm_UL + 74) * 2);
  } else {
    RSSI_UL = (int)(((RSSI_dBm_UL + 74) * 2) + 256);
  }

  // 1. Trava o valor entre -30 e +30 para evitar que o byte estoure
  if (SNR_UL < -30.0) SNR_UL = -30.0;
  if (SNR_UL > 30.0) SNR_UL = 30.0;

  // Usamos uint8_t (byte) para ocupar apenas 1 byte na memória.
  // Usamos a função round() para garantir que o número float seja 
  // arredondado corretamente antes de virar inteiro.
  SNR_UL_inteiro = (uint8_t)round((SNR_UL + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)

  // --- Armazena informações de gerência no pacote UL ---
  PacoteUL[2] = RSSI_UL;

  PacoteUL[3] = (byte)SNR_UL_inteiro;

  // --- Publica os 20 bytes no tópico UL, com QoS1 (at least once) ---
  // Importante para o dado de luminosidade, que é a peça central do framework:
  // o broker confirma (PUBACK) e a biblioteca retransmite se necessário.
  if (mqttClient.connected()) {
    bool ok = mqttClient.publish(TOPIC_UL, (char*)PacoteUL, Tamanho_pacote, false, MQTT_QOS);
    if (ok) {
      Serial.println("[PHY] Pacote UL publicado via MQTT (QoS1).");
    } else {
      Serial.println("[PHY] Falha ao publicar pacote UL via MQTT.");
    }
  } else {
    Serial.println("[PHY] MQTT desconectado – pacote UL descartado.");
  }

}


// =====================================================================
//                     Callback MQTT (recepção de mensagens)
// =====================================================================
// Callback "advanced" -- necessário para acessar o payload como bytes
// binários (o callback simples da lib entrega String, que corrompe
// bytes nulos/binários). Nunca chamar publish/subscribe aqui dentro
// (recomendação da própria biblioteca) -- só seta a flag.
void mqtt_callback(MQTTClient *client, char topic[], char bytes[], int length) {
  if (strcmp(topic, TOPIC_DL) == 0) {
    if (length >= Tamanho_pacote) {
      for (int i = 0; i < Tamanho_pacote; i++) {
        mqtt_dl_payload[i] = (byte)bytes[i];
      }
      mqtt_dl_disponivel = true;   // sinaliza para o loop principal
    }
  }
}


// =====================================================================
//                    Funções de conexão MQTT
// =====================================================================

void conectar_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Conectando ao broker...");
    if (mqttClient.connect(CLIENT_ID.c_str())) {
      Serial.println(" conectado!");
      mqttClient.subscribe(TOPIC_DL, MQTT_QOS);
      Serial.print("[MQTT] Inscrito (QoS");
      Serial.print(MQTT_QOS);
      Serial.print(") em: ");
      Serial.println(TOPIC_DL);
    } else {
      Serial.print(" falhou (erro=");
      Serial.print((int)mqttClient.lastError());
      Serial.println("). Tentando em 3s...");
      delay(3000);
    }
  }
}

#endif