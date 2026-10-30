# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# 29/10/2026
#====== Nível 5 - Gerência ======
# Extrai RSSI e SNR dos dados brutos e calcula a PSR
import time
import os

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"

# Arquivo CSV final unificado para o Excel
arquivo_excel_csv = f"{PASTA_N4}/Dados_Processados/dados_processados_gerencia.csv"

# Garante que a pasta de Dados_Processados existe
if not os.path.exists(f"{PASTA_N4}/Dados_Processados"):
    os.mkdir(f"{PASTA_N4}/Dados_Processados")

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    return str(valor).replace('.', ',')

while True:

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
    arquivos.sort()
    for nome in arquivos:
        if nome.endswith(".txt"):
            arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Abre o arquivo de dados brutos
    arquivo = open(arquivo_entrada,"r")
    linhas = arquivo.readlines()
    arquivo.close()

    # Listas que guardam os valores calculados
    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []
    psr = []

    # Contadores usados para calcular a PSR
    total_pacotes = 0
    pacotes_recebidos = 0
    
    # Inicializa variáveis para o print final caso o arquivo esteja vazio
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    # Começa em 1 para pular o cabeçalho do arquivo
    for i in range(1,len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes = total_pacotes + 1

        # Se todos os bytes do UL forem diferente de 9, considera pacote recebido
        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1

        if pacote_recebido == 1:
            pacotes_recebidos = pacotes_recebidos + 1

            # RSSI de downlink no byte UL_B0 (Posição 38)
            UL_B0 = int(partes[22]) 
            if UL_B0 == 127:
                RSSI_DL = -10.5
            elif UL_B0 > 128:
                RSSI_DL = ((UL_B0-256)/2.0)-74
            else:
                RSSI_DL = (UL_B0/2.0)-74

            # SNR de downlink no byte UL_B1 (Posição 39)
            UL_B1 = int(partes[23])
            SNR_DL = round(((UL_B1 / 4) - 30),2)

            # RSSI de uplink no byte UL_B2 (Posição 40)
            UL_B2 = int(partes[24])
            if UL_B2 == 127:
                RSSI_UL = -10.5 # Correção da variável (estava sobrescrevendo RSSI_DL no original)          
            elif UL_B2 > 128:
                RSSI_UL = ((UL_B2-256)/2.0)-74
            else:
                RSSI_UL = (UL_B2/2.0)-74

            # SNR de uplink no byte UL_B3 (Posição 41)
            UL_B3 = int(partes[25])
            SNR_UL = round(((UL_B3 / 4) - 30),2)

            rssi_down.append(RSSI_DL)
            rssi_up.append(RSSI_UL)
            snr_down.append(SNR_DL)
            snr_up.append(SNR_UL)
        else:
            # Mantém o alinhamento das listas caso o pacote não seja recebido
            # preenchendo com vazio ou mantendo a estrutura para a PSR bater por linha
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")

        # Calcula a PSR acumulada até este pacote
        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

    # Grava todos os dados unificados no CSV formatado para Excel PT-BR
    f_excel = open(arquivo_excel_csv, "w", encoding="utf-8")
    
    # Escreve o cabeçalho das colunas separado por ponto e vírgula
    print("RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada", file=f_excel)
    
    # Escreve as linhas convertendo os pontos decimais em vírgulas
    for i in range(len(psr)):
        r_down = formatar_pt_br(rssi_down[i]) if rssi_down[i] != "" else ""
        r_up = formatar_pt_br(rssi_up[i]) if rssi_up[i] != "" else ""
        s_down = formatar_pt_br(snr_down[i]) if snr_down[i] != "" else ""
        s_up = formatar_pt_br(snr_up[i]) if snr_up[i] != "" else ""
        p_str = formatar_pt_br(psr[i])
        
        print(f"{r_down};{r_up};{s_down};{s_up};{p_str}", file=f_excel)
        
    f_excel.close()

    print("Arquivo = ",arquivo_entrada," | Pacotes = ",total_pacotes," | Recebidos = ",pacotes_recebidos," | PSR = ",PSR, "| RSSI Downlink = ", RSSI_DL, "| RSSI Uplink = ", RSSI_UL, "| SNR Downlink = ", SNR_DL, "| SNR Uplink = ", SNR_UL)
    time.sleep(1)
