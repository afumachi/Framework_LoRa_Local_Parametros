# MoT LoRa + Borda | N2 e N3 | WissTek-IoT | Framework LoRa MQTT Exclusivo
# 15/10/2026 - Branquinho - Guilherme - Anderson

# ========================== 1 - Bibliotecas
import math
import time
import struct
from time import localtime, strftime
import os
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

Tamanho_pacote = 20

# ========================= 2 - Variáveis e arquivos
Pacote_DL = [0]*Tamanho_pacote
PacoteUL  = [0]*Tamanho_pacote

# Caminho da Pasta de armazenamento (Caminho Relativo)
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")

# Caminhos dos arquivos de armazenamento e leitura de parâmetros
caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
caminho_dados      = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")
os.makedirs(caminho_dados, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)
caminho_led = os.path.join(caminho_parametros, "APLICACAO.txt")
caminho_txt_parametros = os.path.join(caminho_parametros, "PARAMETROS.txt")
caminho_mqtt_txt = os.path.join(caminho_parametros, "MQTT.txt")

for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0
   PacoteUL[i]  = 0

Grava_log = 1

Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'

# Variáveis globais para controle MQTT
estado_mqtt = 0
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)
mqtt_client = None
TOPIC_DL = ""
TOPIC_UL = ""
MQTT_QOS = 1

def on_connect(client, userdata, flags, reason_code, properties):
    global estado_mqtt, TOPIC_UL, MQTT_QOS
    if reason_code == 0:
        print("[MQTT] Conectado ao Broker MQTT com sucesso.")
        client.subscribe(TOPIC_UL, qos=MQTT_QOS)
        print(f"[MQTT] Inscrito no tópico: {TOPIC_UL} (QoS{MQTT_QOS})")
        estado_mqtt = 1
    else:
        print(f"[MQTT] Falha na conexão. Código: {reason_code}")
        estado_mqtt = 0

def on_message(client, userdata, msg):
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= Tamanho_pacote:
        Pacote_UL_payload = bytearray(payload[:Tamanho_pacote])
        Pacote_UL_status.set()

def on_disconnect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code != 0:
        print(f"[MQTT] Desconectado inesperadamente (rc={reason_code}). Tentando reconectar...")      
        estado_mqtt = 0
        try:
            client.reconnect()
        except:
            pass

def ler_parametros_arquivo():
   if not os.path.exists(caminho_txt_parametros):
      return None
   try:
      with open(caminho_txt_parametros, "r") as f:
         linhas = [linha.strip() for linha in f.readlines()]
         if len(linhas) >= 3:
            comando = int(linhas[0])
            medidas = int(linhas[1])
            tempo = float(linhas[2].replace(",", "."))
            return comando, medidas, tempo
   except Exception:
      pass
   return None

def ler_config_mqtt():
    if not os.path.exists(caminho_mqtt_txt):
        return "broker.hivemq.com", 1883, "mot_lora_mqtt_AAF/gateway/downlink", "mot_lora_mqtt_AAF/gateway/uplink", 1
    try:
        with open(caminho_mqtt_txt, "r") as f:
            linhas = [l.strip() for l in f.readlines()]
            if len(linhas) >= 5:
                broker = linhas[0]
                porta = int(linhas[1])
                topic_dl = linhas[2]
                topic_ul = linhas[3]
                qos = int(linhas[4])
                return broker, porta, topic_dl, topic_ul, qos
    except:
        pass
    return "broker.hivemq.com", 1883, "mot_lora_mqtt_AAF/gateway/downlink", "mot_lora_mqtt_AAF/gateway/uplink", 1

print("\n========== Aguardando Configuração Inicial via Painel (PARAMETROS.txt) ==========")

config = None
while config is None:
   config = ler_parametros_arquivo()
   if config is None:
      time.sleep(1)

# Inicializa as configurações do Broker MQTT lidas do arquivo MQTT.txt
BROKER, PORTA_MQTT, TOPIC_DL, TOPIC_UL, MQTT_QOS = ler_config_mqtt()
print(f"[Config] Conectando ao Broker MQTT: {BROKER}:{PORTA_MQTT} | DL: {TOPIC_DL} | UL: {TOPIC_UL}")

mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2)
mqtt_client.on_connect    = on_connect
mqtt_client.on_message    = on_message
mqtt_client.on_disconnect = on_disconnect

try:
    mqtt_client.connect(BROKER, PORTA_MQTT, keepalive=60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"[Erro MQTT] Falha ao conectar ao broker: {e}")

# Aguarda conexão estabilizar
time.sleep(2)

print("\n========== Gateway LoRa - Execução Exclusiva MQTT ==========")

try:
    while True:
        config_atual = ler_parametros_arquivo()
        if config_atual:
            comando, num_medidas_total, Tempo_entre_pacotes = config_atual
        else:
            comando = 0
            time.sleep(1)
            continue

        # Se o comando for PARAR (0) ou PAUSAR (2)
        if comando == 0:
            time.sleep(0.5)
            continue
        elif comando == 2:
            print('[LoRa] Teste PAUSADO pelo operador.')
            time.sleep(0.5)
            continue

        # Se comando for INICIAR (1)
        if comando == 1:
            filename1 = strftime(os.path.join(caminho_dados, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
            Log_dados = open(filename1, 'w')
            print("Novo arquivo de log criado: %s" % filename1)
            print(Cabecalho, file=Log_dados)
            
            if estado_mqtt != 1:
                mqtt_client.reconnect()

            Comando_LED_amarelo = 0
            Contador_pkt_DL = 0
            perda_PK_RX = 0
            ID_sensor = 1
            ID_gateway = 0

            print('[LoRa] Teste INICIADO / RETOMADO.')

            try:
                for j in range(1, int(num_medidas_total) + 1):
                    # Verifica se o operador alterou o comando no painel durante a execução (ex: Parar ou Pausar)
                    cfg_check = ler_parametros_arquivo()
                    if cfg_check and cfg_check[0] != 1:
                        print("[LoRa] Execução interrompida ou pausada pelo painel de controle.")
                        break

                    Tempo_inicio_pacote = time.time()

                    # Lê o arquivo de comando do LED amarelo gerado pelo N5/Cliente
                    try:
                       with open(caminho_led, "r") as f:
                          linha = f.readline().strip()
                          Comando_LED_amarelo = 1 if linha == "1" else 0
                    except:
                          Comando_LED_amarelo = 0

                    Pacote_DL[16] = Comando_LED_amarelo
                    
                    # Incremento correto e limpo do contador de pacotes de Downlink
                    Contador_pkt_DL += 1
                    Pacote_DL[12] = (Contador_pkt_DL >> 8) & 0xFF  # MSB
                    Pacote_DL[13] = Contador_pkt_DL & 0xFF         # LSB         
                    
                    Pacote_DL[8] = ID_sensor
                    Pacote_DL[9] = ID_gateway
                    Pacote_DL[4] = int(Tempo_entre_pacotes)

                    # Publicação MQTT (DL) e Espera de Resposta (UL)
                    Pacote_UL_status.clear()
                    
                    pub_result = mqtt_client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS, retain=False)
                    
                    try:
                        pub_result.wait_for_publish(timeout=2.0)
                    except Exception as e:
                        print(f"[MQTT Aviso] Timeout ao confirmar publicação DL: {e}")

                    # Aguarda a chegada do Uplink correspondente enviado pelo ESP32
                    Pacote_UL_novo = Pacote_UL_status.wait(timeout=Tempo_entre_pacotes)
                    if Pacote_UL_novo:
                        Pacote_UL = Pacote_UL_payload
                        pacote_recebido_sucesso = (len(Pacote_UL) == Tamanho_pacote)
                    else:
                        pacote_recebido_sucesso = False

                    # Tratamento de Log e Impressão
                    if pacote_recebido_sucesso:
                       print('Pacote = ', j, ' | Pacote UL recebido | LED = ', Comando_LED_amarelo)
                       Dados_DL = ''
                       Dados_UL = ''
                       for i in range(Tamanho_pacote):
                          if i == 0:
                             Dados_DL = str(Pacote_DL[i])
                             Dados_UL = str(Pacote_UL[i])
                          else:
                             Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                             Dados_UL = Dados_UL + ', ' + str(Pacote_UL[i])
                       Tempo = time.asctime()
                       print(Tempo + ', ' + str(j) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)
                       
                       if Grava_log == 1 and Log_dados and not Log_dados.closed:
                          Dados_log = Tempo + ',' + str(j) + ',' + Dados_DL + ',' + Dados_UL
                          print(Dados_log, file=Log_dados)
                          Log_dados.flush()
                    else:
                       perda_PK_RX += 1
                       print('Cont = ', j, ' PERDEU PACOTE ')
                       Dados_DL = ''
                       Dados_UL = ''
                       for i in range(Tamanho_pacote):
                          if i == 0:
                             Dados_DL = str(Pacote_DL[i])
                             Dados_UL = '9'
                          else:
                             Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                             Dados_UL = Dados_UL + ', 9'
                       Tempo = time.asctime()
                       print(Tempo + ', ' + str(j) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                       if Grava_log == 1 and Log_dados and not Log_dados.closed:
                          Dados_log = Tempo + ',' + str(j) + ',' + Dados_DL + ',' + Dados_UL
                          print(Dados_log, file=Log_dados)
                          Log_dados.flush()

                    # Sincroniza o tempo restante do ciclo
                    Tempo_gasto = time.time() - Tempo_inicio_pacote
                    if Tempo_gasto < Tempo_entre_pacotes:
                       time.sleep(Tempo_entre_pacotes - Tempo_gasto)

                print('Pacotes enviados = ', num_medidas_total, ' | Pacotes perdidos = ', perda_PK_RX)
                Log_dados.close()
                print('[LoRa] Fim da Execução da Rodada')

                # Atualiza automaticamente o PARAMETROS.txt para 0 (Parado) ao concluir a rodada
                try:
                   with open(caminho_txt_parametros, "w") as pf:
                      pf.write("0\n")
                      pf.write(f"{num_medidas_total}\n")
                      pf.write(f"{Tempo_entre_pacotes}\n")
                except:
                   pass

            except Exception as e:
                if 'Log_dados' in locals() and Log_dados and not Log_dados.closed:
                   Log_dados.close()
                print(f'[LoRa] Erro na execução: {e}')

        else:
            time.sleep(0.5)

except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   print('[LoRa] Fim da Execução')
finally:
   try:
      if mqtt_client:
         mqtt_client.loop_stop()
         mqtt_client.disconnect()
         print("[MQTT] Desconectado do broker.")
   except:
      pass
