# -*- coding: utf-8 -*-
import os
import time
import glob
import ctypes
import logging
import warnings

from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from modulos.contexto import context

# ==========================================
# IGNORAR AVISOS NÃO CRÍTICOS (Zero Alerta)
# ==========================================
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.application")

# ==========================================
# MAPEAMENTO DE DLLS DO WINDOWS (Zero Alertas)
# ==========================================
_user32 = ctypes.windll.user32
FindWindowW = getattr(_user32, "FindWindowW")
SetForegroundWindow = getattr(_user32, "SetForegroundWindow")


# ==========================================
# 1. FUNÇÃO DE GERAÇÃO NO DOC-WINDOWS
# ==========================================
def gerar_xml_docwindows(data_alvo: str) -> None:
    """Acessa o DOC-Windows, preenche os dados e aguarda a confirmação de sucesso."""
    logging.info("Conectando ao DOC-Windows aberto...")

    app = Application(backend="uia").connect(path=r"C:\DeMaria\DOC-Windows\Doc-Windows.exe")
    janela_principal = app.top_window()
    janela_principal.set_focus()
    time.sleep(1)

    logging.info("Navegando pelos menus via teclado com pausas de segurança...")
    send_keys('%')
    time.sleep(0.3)
    send_keys('{RIGHT 5}')
    time.sleep(0.3)
    send_keys('{DOWN 6}')
    time.sleep(0.3)
    send_keys('{RIGHT 1}')
    time.sleep(0.3)
    send_keys('{DOWN 1}')
    time.sleep(0.3)
    send_keys('{ENTER}')

    logging.info("Aguardando a janela de geração de XML abrir...")
    time.sleep(2)
    janela_xml = app.top_window()

    logging.info("Preenchendo o período...")
    campo_data = janela_xml.child_window(auto_id="txtPeriodoUtilizacao", control_type="Edit")
    campo_data.wait('visible', timeout=10)

    campo_data.click_input()
    send_keys('^a{BACKSPACE}')
    time.sleep(0.3)
    campo_data.type_keys(data_alvo, with_spaces=True)
    time.sleep(1)

    logging.info("Acionando o botão 'Gerar'...")
    btn_gerar = janela_xml.child_window(title="Gerar", auto_id="button1", control_type="Button")
    btn_gerar.click_input()

    # --- VALIDAÇÃO VIA API DO WINDOWS ---
    logging.info("Aguardando o processamento do XML...")
    data_formatada = f"{data_alvo[0:2]}/{data_alvo[2:4]}/{data_alvo[4:8]}"
    mensagem_esperada = f"O XML com os atos realizados no dia {data_formatada} gerados com sucesso!"

    timeout_xml = 40
    inicio_espera = time.time()
    hwnd_popup = 0

    while (time.time() - inicio_espera) < timeout_xml:
        hwnd_popup = FindWindowW(None, "Informar atos ao TJRJ")
        if hwnd_popup != 0:
            break
        time.sleep(1)

    if hwnd_popup != 0:
        logging.info("Popup detectado! Lendo o conteúdo interno...")
        time.sleep(0.5)

        app_popup = Application(backend="win32").connect(handle=hwnd_popup)
        janela_popup = app_popup.window(handle=hwnd_popup)

        textos_na_tela = [janela_popup.window_text()]
        for elemento in janela_popup.children():
            texto_elemento = elemento.window_text()
            if texto_elemento:
                textos_na_tela.append(texto_elemento)

        texto_junto = " ".join(textos_na_tela).replace('\n', ' ')

        if mensagem_esperada in texto_junto:
            logging.info(f"✓ Mensagem validada perfeitamente: '{mensagem_esperada}'")

            # Confirma o popup
            SetForegroundWindow(hwnd_popup)
            time.sleep(0.5)
            send_keys('{ENTER}')

            logging.info("Aguardando o fechamento do popup...")
            time.sleep(2)

            logging.info("Fechando a janela de geração de XML...")
            janela_xml.set_focus()
            time.sleep(0.5)

            btn_fechar = janela_xml.child_window(title="Fechar", auto_id="btFechar", control_type="Button")
            btn_fechar.click_input()

            logging.info("✓ TELA DO DOC-WINDOWS FECHADA COM SUCESSO!")
            time.sleep(1)
        else:
            # Em vez de chamar o alerta diretamente, repassamos o erro para o main.py
            raise RuntimeError(
                "FALHA NA GERAÇÃO DO XML!\n\n"
                "Mensagem do sistema:\n'ERRO AO GERAR O XML'\n\n"
                "A automação foi interrompida. Verifique o Doc-Windows."
            )
    else:
        raise RuntimeError("O tempo limite esgotou e o Windows não registrou o popup de confirmação.")


# ==========================================
# 2. AUDITORIA DA CAIXA DE SAÍDA
# ==========================================
def auditar_caixa_de_saida(data_alvo: str) -> None:
    """Verifica a integridade dos arquivos gerados e apaga o arquivo de Notas."""
    logging.info("--- INICIANDO AUDITORIA DE ARQUIVOS (M.A.S) ---")

    dir_caixa_saida = r"C:\CGJ-RJ\MAS\Caixa de Saída"
    data_xml = f"{data_alvo[4:8]}{data_alvo[2:4]}{data_alvo[0:2]}"

    # Verifica arquivos de erro (.txt)
    arquivos_txt = glob.glob(os.path.join(dir_caixa_saida, "*.txt"))
    if arquivos_txt:
        raise RuntimeError(
            "FALHA CRÍTICA NA GERAÇÃO DOS ARQUIVOS!\n\n"
            "O Doc-Windows gerou um arquivo de erro (.txt) na Caixa de Saída do M.A.S.\n\n"
            f"Por favor, abra a pasta:\n{dir_caixa_saida}\n\n"
            "Verifique o arquivo TXT gerado para corrigir o problema."
        )

    # Verifica arquivos XML padronizados
    logging.info(f"Buscando os 4 XMLs padronizados com a data {data_xml}...")
    padroes_esperados = {
        "1766_RCPN": f"1766_{data_xml}_RCPN_I_*.xml",
        "1766_RIT": f"1766_{data_xml}_RIT_I_*.xml",
        "1766_Notas": f"1766_{data_xml}_Notas_I_*.xml",
        "7515_RCPN": f"7515_{data_xml}_RCPN_I_*.xml"
    }

    arquivos_encontrados = {}
    arquivos_faltantes = []

    for chave, padrao in padroes_esperados.items():
        busca = glob.glob(os.path.join(dir_caixa_saida, padrao))
        if busca:
            arquivos_encontrados[chave] = busca[0]
            logging.info(f" ✓ Encontrado: {os.path.basename(busca[0])}")
        else:
            arquivos_faltantes.append(padrao.replace('*.xml', '[HORA_GERACAO].xml'))

    if arquivos_faltantes:
        lista_falhas = "\n".join([f"- {os.path.basename(arq)}" for arq in arquivos_faltantes])
        raise RuntimeError(
            "ARQUIVOS XML INCOMPLETOS!\n\n"
            "Os seguintes arquivos não foram encontrados na Caixa de Saída:\n"
            f"{lista_falhas}\n\n"
            "A automação não pode prosseguir para a transmissão."
        )

    # Exclusão de arquivo não aplicável
    logging.info("Removendo arquivo de Notas (não aplicável para transmissão)...")
    try:
        caminho_notas = arquivos_encontrados["1766_Notas"]
        os.remove(caminho_notas)
        logging.info(f" ✓ Arquivo {os.path.basename(caminho_notas)} excluído com sucesso!")
    except Exception as e:
        logging.warning(f"Falha ao excluir arquivo de Notas: {e}")

    logging.info("✓ Validação Concluída! Todos os arquivos estão corretos para a transmissão.")


# ==========================================
# 3. FUNÇÃO PRINCIPAL DO MÓDULO
# ==========================================
def executar(data_alvo: str) -> None:
    try:
        logging.info(f"--- PASSO 5: GERAÇÃO DO XML (Data: {data_alvo}) ---")

        # 1. Gera o arquivo no sistema
        gerar_xml_docwindows(data_alvo)

        # 2. Verifica se a pasta de saída está com os dados corretos
        auditar_caixa_de_saida(data_alvo)

        # Registra sucesso no contexto global
        context.status_xml = "sucesso"

    except Exception as e:
        # Se for um RuntimeError (nossas validações), repassa limpo para o main.py
        if isinstance(e, RuntimeError):
            raise e
        # Se for erro da biblioteca (ex: quebrou no pywinauto), encapsula para ficar legível
        else:
            raise RuntimeError(f"FALHA INESPERADA NA INTERFACE DO DOC-WINDOWS:\n{e}")