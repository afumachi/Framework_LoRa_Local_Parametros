# Controle de Parâmetros e Execução | N6 | WissTek-IoT | Framework LoRa
import tkinter as tk
from tkinter import messagebox
import serial.tools.list_ports
import os

# Caminho para salvamento dos parâmetros
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
CAMINHO_PARAMETROS = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
os.makedirs(CAMINHO_PARAMETROS, exist_ok=True)
ARQUIVO_PARAMETROS = os.path.join(CAMINHO_PARAMETROS, "PARAMETROS.txt")
ARQUIVO_MQTT = os.path.join(CAMINHO_PARAMETROS, "MQTT.txt")

def listar_portas_seriais():
    portas = serial.tools.list_ports.comports()
    lista = []
    for p in portas:
        lista.append(p.device)
    return lista if lista else ["Nenhuma COM encontrada"]

def alternar_modo_conexao():
    modo = var_modo.get()
    if modo == "Serial":
        # Habilita serial, desabilita MQTT
        menu_serial.config(state="normal")
        btn_atualizar_portas.config(state="normal")
        entry_broker.config(state="disabled")
        entry_porta_mqtt.config(state="disabled")
        entry_topico_dl.config(state="disabled")
        entry_topico_ul.config(state="disabled")
        chk_qos.config(state="disabled")
        btn_config_mqtt.config(state="disabled")
    else:
        # Desabilita serial, habilita MQTT
        menu_serial.config(state="disabled")
        btn_atualizar_portas.config(state="disabled")
        entry_broker.config(state="normal")
        entry_porta_mqtt.config(state="normal")
        entry_topico_dl.config(state="normal")
        entry_topico_ul.config(state="normal")
        chk_qos.config(state="normal")
        btn_config_mqtt.config(state="normal")

def configurar_mqtt():
    broker = entry_broker.get().strip()
    porta_mqtt = entry_porta_mqtt.get().strip()
    topico_dl = entry_topico_dl.get().strip()
    topico_ul = entry_topico_ul.get().strip()
    qos = 1 if var_qos.get() else 0

    if not broker or not porta_mqtt or not topico_dl or not topico_ul:
        messagebox.showerror("Erro", "Todos os campos do MQTT devem ser preenchidos!")
        return

    try:
        int(porta_mqtt)
    except ValueError:
        messagebox.showerror("Erro", "A Porta MQTT deve ser um número inteiro válido!")
        return

    try:
        with open(ARQUIVO_MQTT, "w") as f:
            f.write(f"{broker}\n")
            f.write(f"{porta_mqtt}\n")
            f.write(f"{topico_dl}\n")
            f.write(f"{topico_ul}\n")
            f.write(f"{qos}\n")
        messagebox.showinfo("Sucesso", "Configurações do MQTT salvas em MQTT.txt com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível salvar o arquivo MQTT.txt: {e}")

def escrever_parametros(comando):
    tempo_str = entry_tempo.get().strip().replace(",", ".")
    medidas_str = entry_medidas.get().strip()
    modo = var_modo.get()

    try:
        tempo = float(tempo_str)
    except ValueError:
        messagebox.showerror("Erro", "O tempo entre pacotes deve ser um número válido!")
        return

    try:
        medidas = int(medidas_str)
        if medidas <= 0:
            raise ValueError()
    except ValueError:
        messagebox.showerror("Erro", "O número de medidas deve ser um inteiro maior que zero!")
        return

    if modo == "Serial":
        porta_selecionada = combo_serial.get().strip()
        if not porta_selecionada or "Nenhuma" in porta_selecionada:
            messagebox.showerror("Erro", "Selecione uma porta serial válida para o Gateway!")
            return
        if porta_selecionada.upper().startswith("COM"):
            num_serial = porta_selecionada.upper().replace("COM", "")
        else:
            num_serial = porta_selecionada
        quinta_linha = num_serial
    else:
        # Modo MQTT habilitado (indica 1 na quinta linha)
        # Garante que salva o MQTT.txt antes de iniciar se necessário
        configurar_mqtt()
        quinta_linha = "1"

    try:
        with open(ARQUIVO_PARAMETROS, "w") as f:
            f.write(f"{comando}\n")
            f.write(f"{medidas}\n")
            f.write(f"{tempo}\n")
            f.write(f"0\n")  # Linha 4 reservada/compatibilidade
            f.write(f"{quinta_linha}\n") # Quinta linha: 0 para Serial ou 1 para MQTT
        
        status_txt = {0: "PARADO", 1: "INICIADO / ATUALIZADO", 2: "PAUSADO"}
        lbl_status_val.config(text=status_txt[comando], fg="blue" if comando == 1 else ("orange" if comando == 2 else "red"))
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível gravar o arquivo de parâmetros: {e}")

def btn_iniciar():
    escrever_parametros(1)

def btn_pausar():
    escrever_parametros(2)

def btn_parar():
    escrever_parametros(0)

def btn_atualizar():
    escrever_parametros(1)
    messagebox.showinfo("Atualização", "Parâmetros atualizados com sucesso para o teste em andamento!")

def set_short_distance():
    entry_tempo.delete(0, tk.END)
    entry_tempo.insert(0, "1")

def set_long_distance():
    entry_tempo.delete(0, tk.END)
    entry_tempo.insert(0, "6")

# ================= INTERFACE GRÁFICA =================
root = tk.Tk()
root.title("FEE247 - LoRa - Parâmetros de Medidas")
root.geometry("480x680")
root.resizable(False, False)

tk.Label(root, text="Painel de Parâmetros de Medidas com LoRa", font=("Arial", 12, "bold")).pack(pady=10)

# Seleção do Tipo de Conexão (Serial vs MQTT)
frame_conexao = tk.LabelFrame(root, text=" 0. Seleção de Conexão do Gateway LoRa ", font=("Arial", 10, "bold"))
frame_conexao.pack(fill="x", padx=15, pady=5)

var_modo = tk.StringVar(value="Serial")
tk.Radiobutton(frame_conexao, text="Serial", variable=var_modo, value="Serial", command=alternar_modo_conexao, font=("Arial", 9, "bold")).pack(side="left", padx=20, pady=5)
tk.Radiobutton(frame_conexao, text="MQTT", variable=var_modo, value="MQTT", command=alternar_modo_conexao, font=("Arial", 9, "bold")).pack(side="left", padx=20, pady=5)

# 1. Seleção da Porta Serial
frame_serial = tk.LabelFrame(root, text=" 1. Porta Serial do Gateway ", font=("Arial", 10, "bold"))
frame_serial.pack(fill="x", padx=15, pady=5)

portas_disponiveis = listar_portas_seriais()
combo_serial = tk.StringVar(root)
combo_serial.set(portas_disponiveis[0])

menu_serial = tk.OptionMenu(frame_serial, combo_serial, *portas_disponiveis)
menu_serial.config(width=20)
menu_serial.pack(side="left", padx=10, pady=8)

btn_atualizar_portas = tk.Button(frame_serial, text="Atualizar Portas", command=lambda: [
    menu_serial['menu'].delete(0, 'end'),
    *[menu_serial['menu'].add_command(label=p, command=lambda val=p: combo_serial.set(val)) for p in listar_portas_seriais()]
])
btn_atualizar_portas.pack(side="right", padx=10)

# Configurações do Broker MQTT
frame_mqtt = tk.LabelFrame(root, text=" Configurações do Broker MQTT ", font=("Arial", 10, "bold"))
frame_mqtt.pack(fill="x", padx=15, pady=5)

tk.Label(frame_mqtt, text="URL do Broker:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
entry_broker = tk.Entry(frame_mqtt, width=30)
entry_broker.insert(0, "broker.hivemq.com")
entry_broker.grid(row=0, column=1, padx=5, pady=2)

tk.Label(frame_mqtt, text="Porta MQTT:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
entry_porta_mqtt = tk.Entry(frame_mqtt, width=10)
entry_porta_mqtt.insert(0, "1883")
entry_porta_mqtt.grid(row=1, column=1, sticky="w", padx=5, pady=2)

tk.Label(frame_mqtt, text="Tópico DL:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
entry_topico_dl = tk.Entry(frame_mqtt, width=30)
entry_topico_dl.insert(0, "mot_lora_mqtt_AAF/gateway/downlink")
entry_topico_dl.grid(row=2, column=1, padx=5, pady=2)

tk.Label(frame_mqtt, text="Tópico UL:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
entry_topico_ul = tk.Entry(frame_mqtt, width=30)
entry_topico_ul.insert(0, "mot_lora_mqtt_AAF/gateway/uplink")
entry_topico_ul.grid(row=3, column=1, padx=5, pady=2)

var_qos = tk.BooleanVar(value=False)
chk_qos = tk.Checkbutton(frame_mqtt, text="Habilitar QoS 1", variable=var_qos)
chk_qos.grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=2)

btn_config_mqtt = tk.Button(frame_mqtt, text="Configurar MQTT", bg="#e1d0fd", font=("Arial", 9, "bold"), command=configurar_mqtt)
btn_config_mqtt.grid(row=5, column=0, columnspan=2, pady=5)

# 2. Tempo entre pacotes
frame_tempo = tk.LabelFrame(root, text=" 2. Tempo entre Pacotes ", font=("Arial", 10, "bold"))
frame_tempo.pack(fill="x", padx=15, pady=5)

entry_tempo = tk.Entry(frame_tempo, font=("Arial", 10), width=10)
entry_tempo.insert(0, "1")
entry_tempo.pack(side="left", padx=10, pady=8)
tk.Label(frame_tempo, text="segundos").pack(side="left")

tk.Button(frame_tempo, text="Long Distance (6s)", bg="#d9fdd3", command=set_long_distance).pack(side="right", padx=5)
tk.Button(frame_tempo, text="Short Distance (1s)", bg="#d0e1fd", command=set_short_distance).pack(side="right", padx=5)

# 3. Número de medidas
frame_medidas = tk.LabelFrame(root, text=" 3. Número de Medidas ", font=("Arial", 10, "bold"))
frame_medidas.pack(fill="x", padx=15, pady=5)

entry_medidas = tk.Entry(frame_medidas, font=("Arial", 10), width=15)
entry_medidas.insert(0, "100")
entry_medidas.pack(side="left", padx=10, pady=8)

# 4. Botões de Controle de Execução
frame_botoes = tk.LabelFrame(root, text=" 4. Comandos de Execução ", font=("Arial", 10, "bold"))
frame_botoes.pack(fill="x", padx=15, pady=10)

btn_i = tk.Button(frame_botoes, text="INICIAR", bg="green", fg="white", font=("Arial", 9, "bold"), width=8, command=btn_iniciar)
btn_i.grid(row=0, column=0, padx=5, pady=8)

btn_p = tk.Button(frame_botoes, text="PAUSAR", bg="orange", fg="white", font=("Arial", 9, "bold"), width=8, command=btn_pausar)
btn_p.grid(row=0, column=1, padx=5, pady=8)

btn_s = tk.Button(frame_botoes, text="PARAR", bg="red", fg="white", font=("Arial", 9, "bold"), width=8, command=btn_parar)
btn_s.grid(row=0, column=2, padx=5, pady=8)

btn_att = tk.Button(frame_botoes, text="ATUALIZAR", bg="blue", fg="white", font=("Arial", 9, "bold"), width=9, command=btn_atualizar)
btn_att.grid(row=0, column=3, padx=5, pady=8)

# Status Atual na Tela
frame_status = tk.Frame(root)
frame_status.pack(fill="x", padx=15, pady=5)
tk.Label(frame_status, text="Status enviado: ", font=("Arial", 9)).pack(side="left")
lbl_status_val = tk.Label(frame_status, text="AGUARDANDO COMANDO", font=("Arial", 9, "bold"), fg="gray")
lbl_status_val.pack(side="left", padx=5)

# Inicializa o estado visual correto dos campos
alternar_modo_conexao()

root.mainloop()
