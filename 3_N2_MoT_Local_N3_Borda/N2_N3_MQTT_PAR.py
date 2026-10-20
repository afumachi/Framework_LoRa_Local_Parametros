
# ===== Bibliotecas =====
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import math
import time
import struct
from time import localtime, strftime
import os
import pandas as pd
import threading

global comando, medidas, tempo, medida_atual
global Contador_pkt_DL, tempo_entre_pacotes, estado_mqtt
global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, pacote_recebido
global Comando_LED_amarelo, St_LED_amarelo, Tamanho_pacote
global arquivo_log_dados
global BROKER, PORTA_MQTT, TOPIC_DL, TOPIC_UL

# ===== Configurações MQTT =====
BROKER        = "www.tpm.dev.br"
#BROKER        = "broker.hivemq.com"
#BROKER        = "test.mosquitto.org"
PORTA_MQTT    = 1883

# MODIFIQUE O TOPIC_DL E TOPIC_UL de acordo com SEU_NOME
TOPIC_DL      = "mot_mqtt_2904/gateway/downlink"   # Python publica → ESP32 assina
TOPIC_UL      = "mot_mqtt_2904/gateway/uplink"     # ESP32 publica  → Python assina

# QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
# confirma (PUBACK) e há retransmissão se a confirmação não chegar.
# Importante para o dado de luminosidade, que é a peça central do framework.
MQTT_QOS    = 1
estado_mqtt = 0
Pacote_UL_payload = None

# ===== Arquivo Log globais =====
lock_arquivo_log = threading.Lock()

# ===== Variáveis globais =====
Tamanho_pacote = 20

# Cria os pacotes de DL e UL
Pacote_DL =[0]*Tamanho_pacote
Pacote_UL =[0]*Tamanho_pacote

# Garante que os pacotes de DL e UL estão com valor 0
for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0

# Evento para sinalizar chegada de pacote UL via MQTT =====
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)

# Variáveis de Controle
comando = 0
medidas = 0
medida_atual = 0
tempo = 2
condicao_start = 0
arquivo_log_dados = 0

# =============== Camada de aplicação DL
Comando_LED_amarelo = 0  # Inicia apagado
St_LED_amarelo = 0

# ================ Camada de Transporte DL
Contador_pkt_DL = 0
perda_PK_RX = 0

# ================ Camada MAC
tempo_entre_pacotes = 2.0
pacote_recebido = 0

# ================ Camada de Rede DL
#ID_sensor = input("Identificação do sensor = ")
ID_sensor = 1
#ID_gateway = input ("Identificação do gateway =")
ID_gateway = 0

# Caminho da Pasta de armazenamento (Caminho Relativo)
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
caminho_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

# Caminho da Pasta de armazenamento (Caminho Relativo)
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../3_N4_Armazenamento/Parametros/')

os.makedirs(caminho_dados_brutos, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)

caminho_txt_parametros = os.path.join(caminho_parametros, "PARAMETROS.txt")
caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")

#Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'

# ===== Callbacks MQTT
def on_connect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code == 0:
        print("[MQTT] Conectado ao Broker MQTT com sucesso.")
        client.subscribe(TOPIC_UL, qos=MQTT_QOS)
        print(f"[MQTT] Inscrito no tópico: {TOPIC_UL} (QoS{MQTT_QOS})")
        estado_mqtt = 1
    else:
        print(f"[MQTT] Falha na conexão. Código: {reason_code}")
        estado_mqtt = 0

def on_publish(client, userdata, mid, reason_code, properties):
    """Confirmação de entrega (PUBACK) do pacote DL publicado em QoS1."""
    #print(f"[MQTT] PUBACK recebido para mid={mid} (pacote DL confirmado pelo broker).")

def on_message(client, userdata, msg):
    """Callback disparado ao receber pacote UL vindo do ESP32."""
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= Tamanho_pacote:
        Pacote_UL_payload = bytearray(payload[:Tamanho_pacote])
        Pacote_UL_status.set()   # Sinaliza que chegou um pacote válido

def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"[MQTT] Desconectado inesperadamente (rc={reason_code}). Tentando reconectar...")      
        # Utilizando loop_start() neste código, caso NÃO desmarque a linha abaixo:
        estado_mqtt = 0
        client.reconnect()


# ===== Inicialização do cliente MQTT =====
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect
client.on_publish    = on_publish

print("[MQTT] Conectando ao broker MQTT - porta 1883...")
client.connect(BROKER, PORTA_MQTT, keepalive=60)
client.loop_start()   # Thread de fundo para receber mensagens

# Aguarda conexão ser estabelecida com BROKER
print("[MQTT] Aguarda conexão ser estabelecida com BROKER ")
time.sleep(3)

def ler_cmd_led_amarelo():
    """
    Lê o arquivo 'cmd_led_amarelo.txt' e retorna o valor inteiro (0 ou 1).
    Se o arquivo não existir ou estiver inválido, retorna 0 por segurança.
    """
    # Caminho da Pasta de armazenamento (Caminho Relativo)
    #ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
    #caminhoparametros = os.path.join(ARMAZENAMENTO, "Parametros")    
    caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")
    
    try:
        # Abre o arquivo usando o gerenciador 'with' (fecha automaticamente)
        with open(caminho_led, "r", encoding="utf-8") as arquivo:
            # Lê o conteúdo, remove espaços/quebras de linha com .strip()
            conteudo = arquivo.read().strip()
            
            # Converte para inteiro e garante que seja 0 ou 1
            valor = int(conteudo)
            if valor in (0, 1):
                return valor
            else:
                return 0  # Retorna 0 se o valor no txt for diferente de 0 ou 1
                
    except (FileNotFoundError, ValueError):
        # Retorna 0 se o arquivo não existir ou se não for um número válido
        return 0

# ========== DONWLINK MQTT ==========
def downlink():
   global Contador_pkt_DL, tempo_entre_pacotes
   global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, medida_atual

   # Limpa o pacote para garantir que não tem lixo[cite: 8]
   for i in range(Tamanho_pacote):
       Pacote_DL[i] = 0

   # Camada de Aplicação
   Comando_LED_amarelo = int(ler_cmd_led_amarelo())
   Pacote_DL[16] = Comando_LED_amarelo

   # Camada de Transporte
   Pacote_DL[12] = (medida_atual >> 8) & 0xFF  # MSB
   Pacote_DL[13] = medida_atual & 0xFF         # LSB  
        
   # Camada de rede DL
   Pacote_DL[8] = ID_sensor
   Pacote_DL[9] = ID_gateway

   # ======== Camada MAC de DL
   Pacote_DL[4] = int(tempo_entre_pacotes)

   # ======== Camada PHY de DL
                
   # ======== Publica pacote DL no broker MQTT (QoS1) --------
   Pacote_UL_status.clear()
   result = client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS)
                
   # AGUARDA ACK DO BROKER - QoS1
   if client.is_connected():
      try:
         # Aguarda confirmação da publicação do Pacote DL pelo retorno do result client.publish(timeout = tempo entre pacotes)
         result.wait_for_publish(timeout=tempo_entre_pacotes)
         #print(f"Pacote [DL] {Contador_pkt_DL:03d} publicado no broker | LED={Comando_LED_amarelo}")
      except RuntimeError as e:
         print(f"[MQTT Erro] Falha ao aguardar publicação: {e} timeout > tempo entre os pacotes")
         # Aqui você pode tratar a queda: ex. salvar o pacote ou esperar reconectar
      except Exception as e:
                      
         print(f"[Erro] Outro erro ocorreu: {e}")
   else:
      print("[MQTT] Não foi possível publicar. Cliente desconectado.")
      # Inserir Lógica de contingência se o cliente já estiver deslogado
      client.disconnect()
      print("[MQTT] Reconectando ao broker...")
      client.reconnect()



# ========== UPLINK MQTT ==========
def uplink():
   global Pacote_UL, Pacote_DL, medida_atual, pacote_recebido, tempo_entre_pacotes

   # ======== COLETA UPLINK NO BROKER ========
   Pacote_UL_novo = Pacote_UL_status.wait(timeout=tempo_entre_pacotes)
   
   if Pacote_UL_novo:
      Pacote_UL_status.clear()
      Pacote_UL = Pacote_UL_payload          
      if len(Pacote_UL) == Tamanho_pacote:
         pacote_recebido = 1
         St_LED_amarelo = Pacote_UL[16]
         print('Pacote = ',medida_atual,' | Pacote UL recebido | STATUS LED = ',St_LED_amarelo)
   else:
      pacote_recebido = 0
         

# ===== Loop principal: repete pedindo número de medidas =====
print("\n========== Gateway LoRa - Comunicação MQTT ==========")
print("\n Aguardando Comando de INICIAR")
try:
    while True:
         
        # Leitura constante do arquivo de parâmetros do Usuário Nível 6
        path_param = os.path.join(caminho_parametros, 'MQTT.txt')
        if os.path.exists(path_param):
            Parametros_r = open(path_param, 'r')
            line = Parametros_r.readline()
            if len(line) > 0: condicao_start = int(line)
            line = Parametros_r.readline()
            if len(line) > 0: num_medidas = int(line)
            line = Parametros_r.readline()
            if len(line) > 0: tempo = float(line.replace(',', '.')) #tempo = float(line)
            line = Parametros_r.readline()
            if len(line) > 0: broker_mqtt = line
            line = Parametros_r.readline()
            if len(line) > 0: porta_broker = int(line)
            line = Parametros_r.readline()
            if len(line) > 0: topico_mqtt_dl = line
            line = Parametros_r.readline()
            if len(line) > 0: topico_mqtt_ul = line
            
      
            tempo_entre_pacotes = tempo          
        
        # Caso MQTT desconectado - Reconectar
        if estado_mqtt != 1:
            client.reconnect()      

        if (condicao_start == 1):

             if (medida_atual == 0):
                
                 if (arquivo_log_dados == 0):
                      
                     #Caminho da Pasta de armazenamento (Caminho Relativo)

                     print("################## LSS - Iniciando Medições LoRa #################")

                     #print(f"[MQTT] condicao_start: {condicao_start}, num_medidas: {num_medidas}, tempo: {tempo}, broker_mqtt: {broker_mqtt}, porta_broker: {porta_broker}, topico_mqtt_dl: {topico_mqtt_dl}, topico_mqtt_dl: {topico_mqtt_ul} ")
                     # Gera o nome do arquivo com o novo caminho
                     filename1 = strftime(os.path.join(caminho_dados_brutos, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
           
                     Log_dados = open(filename1, 'w')
                     print("Arquivo de log: %s" % filename1)
                     Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,DL_B20,DL_B21,DL_B22,DL_B23,DL_B24,DL_B25,DL_B26,DL_B27,DL_B28,DL_B29,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19,UL_B20,UL_B21,UL_B22,UL_B23,UL_B24,UL_B25,UL_B26,UL_B27,UL_B28,UL_B29'
                     print(Cabecalho,file=Log_dados)
                     arquivo_log_dados = 1
                     time.sleep(1)

             Tempo_gasto = 0
             Tempo_inicio_pacote = time.time()
              
             # ================ Envio de pacote de DL
          
             if(medida_atual < (num_medidas)): #for j in range(1, int(Variavel_loop)):
                # ===================== LOOP DE ENVIO DE PACOTES =============

                medida_atual = medida_atual + 1
                print("### LoRa MQTT -> Medida: ",medida_atual, "de ",num_medidas)
                
                downlink()

                # Aguarda tempo de Publicação no BROKER + Tempo Rádio LoRa
                time.sleep(tempo_entre_pacotes)
                pacote_recebido = 0
                uplink()
                print("Pacote Recebido: ", pacote_recebido)
                
                if (pacote_recebido == 1):    
                      
                   Dados_DL = ''
                   Dados_UL = ''
                   #Prepara os dados dos pacotes de Downlink e Uplink para serem impressos
                   for i in range(Tamanho_pacote):
                      if i == 0:
                         Dados_DL = str(Pacote_DL[i])
                         Dados_UL = str(Pacote_UL[i])
                      else:
                         Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                         Dados_UL = Dados_UL + ', ' + str(Pacote_UL[i])
                   Tempo = time.asctime()
                   print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                   # Grava Pacotes com a trava de segurança
                   with lock_arquivo_log:                      
                      Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                      print(Dados_log,file=Log_dados)
                      Log_dados.flush()

                elif(pacote_recebido == 0):
                    
                   perda_PK_RX = perda_PK_RX + 1
                   print('Cont = ', medida_atual, ' PERDEU N PACOTES ', perda_PK_RX)
                   #Prepara os dados dos pacotes de Downlink e Uplink para serem salvos
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
                   print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                   # Grava Pacotes
                   with lock_arquivo_log:
                      Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                      print(Dados_log,file=Log_dados)
                      Log_dados.flush()

                Tempo_gasto = time.time() - Tempo_inicio_pacote

             elif (medida_atual >= num_medidas):       
                 #Atualiza arquivo de Parâmetros
                 path_param = os.path.join(caminho_parametros, 'MQTT.txt')
                 Parametros = open(path_param, 'w')
                 Parametros.write("0\n100\n2\n")  
                 Parametros.close()
                 print('Pacotes enviados = ',medida_atual,' Pacotes perdidos = ',perda_PK_RX)
                 print('Tempo Entre Pacotes = ',Tempo_gasto)
                 medida_atual = 0
                 Contador_pkt_DL = 0
                 arquivo_log_dados = 0           
                 #Log_dados.close()
                 print('[LoRa MQTT] Fim da Execução')

        elif(condicao_start == 2):
            print('[LoRa MQTT] Execução em pausa')
            time.sleep(1)
          
        elif((condicao_start == 0) or (medida_atual == condicao_start)): #((comando == 0) and (executando == True)):
            comando = 0
            medida_atual = 0
            Contador_pkt_DL = 0
            perda_PK_RX = 0
            arquivo_log_dados = 0
            #Atualiza arquivo de Parâmetros
            path_param = os.path.join(caminho_parametros, 'MQTT.txt')
            Parametros = open(path_param, 'w')
            Parametros.write("0\n100\n2\n") 
            Parametros.close()
          
            try:
                Log_dados.close()
            except (AttributeError, NameError):
                pass
              
            print('[LoRa MQTT] Fim da Execução... comando = PARAR')
            time.sleep(1)

        else:
            print('[LoRa MQTT] Condição Start...', condicao_start)
            comando = 0
            medida_atual = medida_atual -1
            time.sleep(1)

# Interrompe a aplicação N2_N3 e a conexão com MQTT
except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   Log_dados.close()
   medida_atual = 0
   #Atualiza arquivo de Parâmetros
   arquivo_log_dados = 0
   path_param = os.path.join(caminho_parametros, 'MQTT.txt')
   Parametros = open(path_param, 'w')
   Parametros.write("0\n100\n2\n")  
   Parametros.close()
   print('[LoRa MQTT] Fim da Execução')
   client.loop_stop()
   client.disconnect()
   print("[LoRa MQTT] Desconectado do broker... except")
finally:
   client.loop_stop()
   client.disconnect()
   print("[LoRa MQTT] Desconectado do broker... finally")
