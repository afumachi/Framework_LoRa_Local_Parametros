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

for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0
   PacoteUL[i]  = 0

Grava_log = 1

os.makedirs(caminho_dados, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)
caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")
caminho_txt_parametros = os.path.join(caminho_parametros, "PARAMETROS.txt")
caminho_mqtt_txt = os.path.join(caminho_parametros, "MQTT.txt")

Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'

# Variáveis globais para controle MQTT
estado_mqtt = 0
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)
mqtt_client = None
TOPIC_DL = ""
TOPIC_UL = ""
MQTT_QOS = 0

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
        return "broker.hivemq.com", 1883, "mot_lora_mqtt_AAF/gateway/downlink", "mot_lora_mqtt_AAF/gateway/uplink", 0
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
    return "broker.hivemq.com", 1883, "mot_lora_mqtt_AAF/gateway/downlink", "mot_lora_mqtt_AAF/gateway/uplink", 0

print("\n========== Aguardando Configuração Inicial via Painel (PARAMETROS.txt) ==========")

config = None
while config is None:
   config = ler_parametros_arquivo()
   if config is None:
      time.sleep(1)

Comando_LED_amarelo = 0  
Contador_pkt_DL = 0
perda_PK_RX     = 0
ID_sensor = 1
ID_gateway = 0

print("\n========== Gateway LoRa - Execução Exclusiva MQTT ==========")

mqtt_client = None
conexao_ativa = False

try:
    j = 1
    Log_dados = None
    filename1 = None
    estado_anterior = 0
    rodada_concluida = False

    while True:
        config_atual = ler_parametros_arquivo()
        if config_atual:
            comando, num_medidas_total, Tempo_entre_pacotes = config_atual
        else:
            comando = 0

        # Gerenciamento dinâmico da conexão MQTT ao iniciar/atualizar
        if comando == 1:
            if not conexao_ativa or mqtt_client is None:
                BROKER, PORTA_MQTT, TOPIC_DL, TOPIC_UL, MQTT_QOS = ler_config_mqtt()
                print(f"[Config] Conectando ao Broker MQTT: {BROKER}:{PORTA_MQTT} | DL: {TOPIC_DL} | UL: {TOPIC_UL}")
                
                if mqtt_client:
                    try:
                        mqtt_client.loop_stop()
                        mqtt_client.disconnect()
                    except:
                        pass

                estado_mqtt = 0
                mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2)
                mqtt_client.on_connect    = on_connect
                mqtt_client.on_message    = on_message
                mqtt_client.on_disconnect = on_disconnect
                try:
                    mqtt_client.connect(BROKER, PORTA_MQTT, keepalive=60)
                    mqtt_client.loop_start()
                except Exception as e:
                    print(f"[Erro MQTT] Falha ao conectar ao broker: {e}")

                # Aguarda confirmação real de conexão (estado_mqtt == 1) antes de prosseguir
                print("[MQTT] Aguardando autenticação e inscrição nos tópicos...")
                t_ini_conn = time.time()
                while estado_mqtt != 1 and (time.time() - t_ini_conn) < 10:
                    time.sleep(0.5)

                if estado_mqtt == 1:
                    conexao_ativa = True
                else:
                    print("[MQTT Erro] Tempo esgotado aguardando conexão com o broker.")

        if comando == 1 and rodada_concluida:
            rodada_concluida = False
            estado_anterior = 0

        if comando == 0:
            if Log_dados and not Log_dados.closed:
                Log_dados.close()
                print(f'[LoRa] Teste PARADO. Arquivo de log fechado.')
            Log_dados = None
            j = 1
            Contador_pkt_DL = 0
            perda_PK_RX = 0
            rodada_concluida = False
            
            if mqtt_client:
                try:
                    mqtt_client.loop_stop()
                    mqtt_client.disconnect()
                    print("[MQTT] Desconectado do broker.")
                except:
                    pass
                mqtt_client = None
            conexao_ativa = False
            estado_mqtt = 0

            time.sleep(0.5)
            estado_anterior = 0
            continue

        if comando == 2:
            if estado_anterior != 2 and not rodada_concluida:
                print('[LoRa] Teste PAUSADO pelo operador.')
                estado_anterior = 2
            time.sleep(0.5)
            continue

        if comando == 1 and not rodada_concluida:
            # Trava de segurança: se o broker desconectou, pausa/aguarda reconexão antes de disparar DL
            if estado_mqtt != 1:
                print("[MQTT] Conexão perdida ou não estabelecida. Tentando reconectar...")
                t_rec = time.time()
                while estado_mqtt != 1 and (time.time() - t_rec) < 5:
                    try:
                        mqtt_client.reconnect()
                    except:
                        pass
                    time.sleep(0.5)

                if estado_mqtt != 1:
                    print("[MQTT Erro] Sem conexão com o broker. Aguardando próximo ciclo...")
                    time.sleep(1)
                    continue

            if Log_dados is None or Log_dados.closed:
               filename1 = strftime(os.path.join(caminho_dados, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
               Log_dados = open(filename1, 'w')
               print("Novo arquivo de log criado: %s" % filename1)
               print(Cabecalho, file=Log_dados)
               j = 1
               perda_PK_RX = 0

            if estado_anterior != 1:
               print('[LoRa] Teste INICIADO / RETOMADO.')
               estado_anterior = 1

            if j > num_medidas_total:
               print(f'[LoRa] Final das medidas ({num_medidas_total}).')
               if Log_dados and not Log_dados.closed:
                  Log_dados.close()
                  print('[LoRa] Arquivo de log salvo e fechado com sucesso.')
               Log_dados = None
               
               try:
                  with open(caminho_txt_parametros, "w") as pf:
                     pf.write("0\n")
                     pf.write(f"{num_medidas_total}\n")
                     pf.write(f"{Tempo_entre_pacotes}\n")
               except Exception as e:
                  print(f"[Erro] Falha ao atualizar PARAMETROS.txt para 0: {e}")

               rodada_concluida = True
               time.sleep(1)
               continue

            Tempo_inicio_pacote = time.time()

            try:
               with open(caminho_led, "r") as f:
                  linha = f.readline().strip()
                  Comando_LED_amarelo = 1 if linha == "1" else 0
            except:
                  Comando_LED_amarelo = 0

            Pacote_DL[16] = Comando_LED_amarelo
            Contador_pkt_DL = Contador_pkt_DL + 1
            if Contador_pkt_DL == 256:
               Contador_pkt_DL = 0
            Pacote_DL[12] = int(Contador_pkt_DL)
            Pacote_DL[8] = ID_sensor
            Pacote_DL[9] = ID_gateway
            Pacote_DL[4] = int(Tempo_entre_pacotes)

            # Publicação MQTT (DL) e Espera de Resposta (UL)
            Pacote_UL_status.clear()
            mqtt_client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS)

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

            j += 1
            Tempo_gasto = time.time() - Tempo_inicio_pacote
            if Tempo_gasto < Tempo_entre_pacotes:
               time.sleep(Tempo_entre_pacotes - Tempo_gasto)
        else:
            time.sleep(0.5)

except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   try:
      if Grava_log == 1 and 'Log_dados' in locals() and Log_dados and not Log_dados.closed:
         Log_dados.close()
   except:
      pass
   print('[LoRa] Fim da Execução')
finally:
   try:
      if mqtt_client:
         mqtt_client.loop_stop()
         mqtt_client.disconnect()
         print("[MQTT] Desconectado do broker.")
   except:
      pass
