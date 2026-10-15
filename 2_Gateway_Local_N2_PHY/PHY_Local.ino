//======================= PACOTE DOWN LINK - PACOTE VINDO DO PYTHON PARA SER ENVIADO AO NÓ SENSOR ===========================

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

//========================= ENVIA PACOTE DL PARA NÓ SENSOR ATRAVÉS DO RF95
//O pacote DL recebido pela serial proveniente do Nível 3 é enviado para o RF95
void Phy_radio_send_DL() {

  LoRa.beginPacket();                   // start packet
  for (int i = 0; i < Tamanho_pacote; i++) {
    LoRa.write(PacoteDL[i]);            // add data to packet
    digitalWrite(LED_VERMELHO_PIN, HIGH);  
  }
  LoRa.endPacket();                     // finish packet and send it
 
  // Pisca LED Vermelho do Kit PKLORa indicando Transmissão de Pacote DL (TX) para o Nó Sensor LoRa
  
  delay(20);                            
  digitalWrite(LED_VERMELHO_PIN, LOW);   
 // }
}

//======================= RECEBE PACOTE UL LINK - PACODE VINDO NÓ SENSOR para o gateway===========================
// Recebe o pacote UL que chegou no RFM95
void Phy_radio_receive_UL() {
  uint8_t packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    if (packetSize >= Tamanho_pacote) {
      for (int i = 0; i < Tamanho_pacote; i++) {
        PacoteUL[i] = LoRa.read();
      }
      
      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL = LoRa.packetSnr();
      
      // CHAMA CAMADA FÍSICA DE UL
      Phy_serial_send_UL();  //Chama a função de envio da Camada Física 
    }
  }
}

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
    // Pisca LED Verde do Kit PKLORa indicando Recepção de Pacote UL (RX) - se permitido
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(50);
  digitalWrite(LED_VERDE_PIN, LOW);
}