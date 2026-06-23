# -*- coding: utf-8 -*-
# noinspection SpellCheckingInspection,NonAsciiCharacters,GrammarInspection
import time
import logging
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
from pywinauto.application import Application


# ==========================================
# FUNÇÃO AUXILIAR
# ==========================================
def aguardar_mudanca_tela(aplicativo, titulo_ignorado, timeout=300):
    """
    Fica em loop até que uma janela com título diferente do ignorado apareça.
    """
    inicio = time.time()
    while (time.time() - inicio) < timeout:
        # noinspection PyBroadException
        try:
            janela_atual = aplicativo.top_window()
            titulo_atual = str(janela_atual.window_text())

            if titulo_atual and titulo_atual != titulo_ignorado:
                return janela_atual
        except Exception:
            pass
        time.sleep(1)

    logging.warning("O tempo limite esgotou. Capturando a janela atual...")
    return aplicativo.top_window()


# ==========================================
# 1. LIMPANDO O AMBIENTE DE TRABALHO
# ==========================================
def limpar_pasta_tmp():
    logging.info("Preparando o ambiente: Limpando a pasta 'tmp'...")

    diretorio_atual = Path(__file__).resolve().parent
    diretorio_raiz = diretorio_atual.parent
    caminho_pasta_tmp = diretorio_raiz / "tmp"

    if caminho_pasta_tmp.exists():
        for arquivo in caminho_pasta_tmp.iterdir():
            # noinspection PyBroadException
            try:
                if arquivo.is_file():
                    arquivo.unlink()
            except Exception as e:
                logging.warning(f"Não foi possível deletar o arquivo {arquivo.name}. Detalhe: {e}")
        logging.info("Pasta 'tmp' limpa perfeitamente!")
    else:
        caminho_pasta_tmp.mkdir(parents=True, exist_ok=True)
        logging.info("Pasta 'tmp' não existia e foi criada.")


# ==========================================
# 2. CAPTURA E VALIDAÇÃO DA DATA
# ==========================================
def obter_data_interface():
    logging.info("Aguardando inserção de data pelo usuário na interface...")
    resultado_data = []

    def formatar_data(event):
        if event.keysym == "BackSpace":
            return
        texto = entry_data.get().replace("/", "")[:8]
        novo_texto = ""
        for i, char in enumerate(texto):
            if char.isdigit():
                if i in [2, 4]: novo_texto += "/"
                novo_texto += char
        entry_data.delete(0, tk.END)
        entry_data.insert(0, novo_texto)

    # noinspection PyUnusedLocal
    def validar_e_salvar(event=None):
        data_digitada = entry_data.get()
        try:
            datetime.strptime(data_digitada, "%d/%m/%Y")
            resultado_data.append(data_digitada.replace("/", ""))
            root.destroy()
        except ValueError:
            messagebox.showerror("Data Inválida", "Por favor, digite uma data válida no formato DD/MM/AAAA.")
            entry_data.delete(0, tk.END)

    def cancelar_operacao():
        root.destroy()

    root = tk.Tk()
    root.title("Configuração do Robô")
    root.geometry("320x160")
    root.attributes("-topmost", True)
    root.protocol("WM_DELETE_WINDOW", cancelar_operacao)

    root.bind('<Return>', validar_e_salvar)

    label = tk.Label(root, text="Informe a data para gerar os relatórios:", font=("Arial", 10))
    label.pack(pady=15)

    entry_data = tk.Entry(root, font=("Arial", 14), justify="center", width=12)
    entry_data.pack(pady=5)
    entry_data.bind("<KeyRelease>", formatar_data)

    btn_iniciar = tk.Button(root, text="Iniciar Automação", command=validar_e_salvar, bg="#4CAF50", fg="white",
                            font=("Arial", 10, "bold"))
    btn_iniciar.pack(pady=10)

    entry_data.focus()
    root.mainloop()

    if not resultado_data:
        raise RuntimeError("Operação cancelada pelo usuário. O robô não será iniciado.")

    return resultado_data[0]


# ==========================================
# 3. FUNÇÃO PRINCIPAL DO MÓDULO
# ==========================================
def executar(usuario, senha, caminho_exe):
    limpar_pasta_tmp()
    data_alvo = obter_data_interface()
    logging.info(f"Data validada: {data_alvo}. Iniciando o sistema...")

    pasta_do_programa = str(Path(caminho_exe).parent)
    logging.info("Abrindo o aplicativo DOC-Windows...")

    aplicativo = Application(backend="uia").start(cmd_line=caminho_exe, work_dir=pasta_do_programa)
    time.sleep(2)

    janela_inicial = aplicativo.top_window()
    titulo_splash = str(janela_inicial.window_text())
    logging.info(f"Tela inicial detectada: '{titulo_splash}'. Aguardando o carregamento...")

    janela_login = aguardar_mudanca_tela(aplicativo, titulo_splash)

    if not janela_login:
        raise RuntimeError("A janela de login não pôde ser instanciada.")

    titulo_login = str(janela_login.window_text())
    logging.info(f"Tela de login detectada: '{titulo_login}'")

    logging.info("Injetando credenciais...")
    janela_login.child_window(auto_id="userName", control_type="Edit").type_keys(usuario)
    janela_login.child_window(auto_id="Password", control_type="Edit").type_keys(senha + "{ENTER}")

    logging.info("Aguardando a tela principal do sistema carregar...")
    janela_principal = aguardar_mudanca_tela(aplicativo, titulo_login)

    if not janela_principal:
        raise RuntimeError("Falha ao carregar a tela principal após o login.")

    logging.info(f"Tela principal detectada: '{janela_principal.window_text()}'")

    return data_alvo