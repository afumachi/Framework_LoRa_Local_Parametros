
# ===== Bibliotecas =====
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import math
import time
import struct
from time import localtime, strftime
import os
import threading

global comando, medidas, tempo, serial, medida_atual
global Contador_pkt_DL, tempo_entre_pacotes
global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL

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

# ===== Arquivo Log globais =====
lock_arquivo_log = threading.Lock()

# Variáveis de Controle
comando = 0
medidas = 0
medida_atual = 0
tempo = 2
executando = False
condicao_start = 0

# =============== Camada de aplicação DL
Comando_LED_amarelo = 0  # Inicia apagado

# ================ Camada de Transporte DL
Contador_pkt_DL = 0
perda_PK_RX = 0

# ================ Camada MAC
tempo_entre_pacotes = 2.0
pacote_recebido = False

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

Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'

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


def para_medidas():
    global comando, medidas, tempo
               
    # Escreve 0 automaticamente no PARAMETROS.txt para finalizar o ciclo
    try:
        # Salva valores atuais em PARAMETROS.txt
        comando = 0
        n_medidas = medidas
        t_medidas = tempo
        serial_val = "1"
        if os.path.exists(caminho_txt_parametros):
            with open(caminho_txt_parametros, "r") as pf:
                lns = [l.strip() for l in pf.readlines()]
                if len(lns) >= 4:
                        serial_val = lns[3]
            with open(caminho_txt_parametros, "w") as pf:
                pf.write("0\n")
                pf.write(f"{n_medidas}\n")
                pf.write(f"{t_medidas}\n")
                pf.write(f"{serial_val}\n")
    except Exception as e:
        print(f"[Erro] Falha ao atualizar PARAMETROS.txt para 0: {e}")


def ler_cmd_led_amarelo():
    """
    Lê o arquivo 'cmd_led_amarelo.txt' e retorna o valor inteiro (0 ou 1).
    Se o arquivo não existir ou estiver inválido, retorna 0 por segurança.
    """
    # Caminho da Pasta de armazenamento (Caminho Relativo)
    ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
    caminhoparametros = os.path.join(ARMAZENAMENTO, "Parametros")    
    caminho_led = os.path.join(caminhoparametros, "cmd_led_amarelo.txt")
    
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
   global ID_sensor, ID_gateway, Pacote_DL, medida_atual

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
   global Pacote_UL, medida_atual, pacote_recebido

   # ======== COLETA UPLINK NO BROKER ========
   Pacote_UL_novo = Pacote_UL_status.wait(timeout=tempo_entre_pacotes)
   
   if Pacote_UL_novo:
      Pacote_UL_status.clear()
      Pacote_UL = Pacote_UL_payload          
      if len(Pacote_UL) == Tamanho_pacote:
         pacote_recebido = True
         print('Pacote = ',medida_atual,' | Pacote UL recebido | STATUS LED = ',Comando_LED_amarelo)
      else:
         pacote_recebido = False
         


# ===== Loop principal: repete pedindo número de medidas =====
print("\n========== Gateway LoRa - Comunicação MQTT ==========")
print("\n Aguardando Comando de INICIAR")
try:
    while True:
         
      # Leitura constante do arquivo de parâmetros do Usuário Nível 6
      path_param = os.path.join(caminho_parametros, 'PARAMETROS.txt')
      if os.path.exists(path_param):
         Parametros = open(path_param, 'r')
         line = Parametros.readline()
         if len(line) > 0: condicao_start = int(line)
         line = Parametros.readline()
         if len(line) > 0: num_medidas = int(line)
         line = Parametros.readline()
         if len(line) > 0: tempo = float(line.replace(',', '.')) #tempo = float(line)
         line = Parametros.readline()
         if len(line) > 0: serial = int(line)
      
      tempo_entre_pacotes = tempo          
        
      # Caso MQTT desconectado - Reconectar
      if estado_mqtt != 1:
          client.reconnect()      

      if (condicao_start == 1):
          executando = True

          if (medida_atual == 0):
              
              # Caminho da Pasta de armazenamento (Caminho Relativo)
              PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")

              # Caminhos dos arquivos de armazenamento e leitura de parâmetros
              caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
              caminho_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

              os.makedirs(caminho_dados_brutos, exist_ok=True)
              os.makedirs(caminho_parametros, exist_ok=True)

              # Gera a string com a data e hora atual (ex: Rodada_Teste_2026_10_17_11-36-00.txt)
              nome_arquivo = time.strftime("Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt")

              # Combina o diretório com o nome do arquivo gerado
              filename1 = os.path.join(caminho_dados_brutos, nome_arquivo)
                  
              #filename1 = strftime(caminho_dados_brutos,"\Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt")
              Log_dados = open(filename1, 'w')
              print("Arquivo de log: %s" % filename1)
              Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'
              print(Cabecalho,file=Log_dados)
              print(f"[MQTT] Comando recebido = {comando} , Medidas = {num_medidas}, Tempo entre Pacotes = {tempo_entre_pacotes}...")
              time.sleep(1)

          # ================ Camada MAC DL
          #Tempo_entre_pacotes = input("Tempo entre pacotes (s) =")
          Tempo_gasto = 0
          Variavel_loop = int(num_medidas) + 1
          
          # ================ Envio de pacote de DL
          
          if (Tempo_gasto == 0):
          #try:
             if(medida_atual < num_medidas): #for j in range(1, int(Variavel_loop)):
                # ===================== LOOP DE ENVIO DE PACOTES =============

                medida_atual = medida_atual + 1
                print("### LSS - Medida: ",medida_atual, "de ",num_medidas)
                
                Tempo_inicio_pacote = time.time()

                downlink()

                # Aguarda tempo de Publicação no BROKER + Tempo Rádio LoRa
                time.sleep(tempo_entre_pacotes/2)
                
                uplink()

                if (pacote_recebido == True):    
                      
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

                elif(pacote_recebido == False):
                   perda_PK_RX += 1
                   print('Cont = ', medida_atual, ' PERDEU N PACOTES ', perda_PK_RX)
                   
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

             else:       
                 print('Pacotes enviados = ',medida_atual,' Pacotes perdidos = ',perda_PK_RX)
                 print('Tempo Entre Pacotes = ',Tempo_gasto)
                 medida_atual = 0
                 Contador_pkt_DL = 0

                 #Atualiza arquivo de Parâmetros
                 path_param = os.path.join(caminho_parametros, 'PARAMETROS.txt')
                 Parametros = open(path_param, 'w')
                 Parametros.write("0\n100\n2\n12\n")  
                 Parametros.close()
           
                 Log_dados.close()
                 print('[LoRa MQTT] Fim da Execução')
          
             #except:
             #executando = False
             #Log_dados.close()
             #Contador_pkt_DL = 0
             #para_medidas()
             #print('except [LoRa MQTT] Fim da Execução')

      elif(condicao_start == 2):
          executando = False
          print('[LoRa MQTT] Execução em pausa')
          time.sleep(1)
          
      elif((condicao_start == 0) and (medida_atual == condicao_start)):#((comando == 0) and (executando == True)):
          executando = False
          comando = 0
          medida_atual = 0
          Contador_pkt_DL = 0
          #para_medidas()

          #Atualiza arquivo de Parâmetros
          path_param = os.path.join(caminho_parametros, 'PARAMETROS.txt')
          Parametros = open(path_param, 'w')
          Parametros.write("0\n100\n2\n12\n") 
          Parametros.close()
          
          try:
              Log_dados.close()
          except (AttributeError, NameError):
              pass
              
          print('[LoRa MQTT] Execução Parada... comando = PARAR')
          time.sleep(1)
      else:
          print('[LoRa MQTT] Condição Start...', condicao_start)

# Interrompe a aplicação N2_N3 e a conexão com MQTT
except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   Log_dados.close()
   #Atualiza arquivo de Parâmetros
   path_param = os.path.join(caminho_parametros, 'PARAMETROS.txt')
   Parametros = open(path_param, 'w')
   Parametros.write("0\n100\n2\n12\n")  
   Parametros.close()
   print('[LoRa MQTT] Fim da Execução')
   client.loop_stop()
   client.disconnect()
   print("[LoRa MQTT] Desconectado do broker... except")
finally:
   client.loop_stop()
   client.disconnect()
   print("[LoRa MQTT] Desconectado do broker... finally")
