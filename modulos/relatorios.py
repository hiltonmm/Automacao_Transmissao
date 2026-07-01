# -*- coding: utf-8 -*-
# noinspection SpellCheckingInspection,NonAsciiCharacters,GrammarInspection,PyDuplicationCode,PyTypeChecker,PyUnusedLocal,PyUnresolvedReferences
import time
import logging
from pathlib import Path
from typing import Any
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.uia_defines import NoPatternInterfaceError

BTN_IMPRIMIR = "Pr" + "int"


# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def fechar_janelas_em_cadeia(app: Application) -> None:
    """
    Envia 1 único ESC para fechar o relatório e retornar à tela principal,
    conforme o comportamento exato do sistema.
    """
    logging.info("Fechando a janela de visualização do relatório com 1 ESC...")

    try:
        # Garante que a janela do relatório (que voltou ao foco) esteja ativa
        app.top_window().set_focus()
        time.sleep(0.5)

        # Envia a tecla ESC
        send_keys('{ESC}')

        # Dá um tempinho para o sistema voltar para a tela de fundo verde
        time.sleep(1.5)

    except Exception as e:
        logging.warning(f"Aviso ao enviar ESC: {e}")

def aguardar_carregamento_relatorio(app: Application) -> Any:
    """Aguarda carregamento do relatório procurando o botão de Print."""
    inicio = time.time()
    while (time.time() - inicio) < 180:
        # noinspection PyBroadException
        try:
            top_win = app.top_window()
            if top_win.child_window(title=BTN_IMPRIMIR, control_type="Button").exists():
                return top_win
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("Timeout carregando relatório.")

def salvar_pdf(janela: Any, nome_arquivo: str, digitar_caminho: bool = True) -> None:
    """Exporta o PDF e salva seguindo a sequência exata de atalhos do usuário."""
    janela.set_focus()
    time.sleep(1)

    # 1. Abre o menu e seleciona PDF
    toolbar = janela.child_window(auto_id="toolStrip1", control_type="ToolBar")
    toolbar.child_window(title="Export drop down menu", control_type="MenuItem").click_input()
    time.sleep(1)
    send_keys('{DOWN 2}{ENTER}')

    # Aguarda a janela "Salvar Como" abrir e focar no campo de Nome
    time.sleep(3)
    caminho_tmp = str(Path(__file__).resolve().parent.parent / "tmp")

    # 2. Digita o nome do arquivo
    send_keys('^a{BACKSPACE}')  # Limpa por segurança
    time.sleep(0.3)
    send_keys(nome_arquivo, with_spaces=True)
    time.sleep(0.5)

    # 3. Lógica do Caminho
    if digitar_caminho:
        # APENAS Alt+E para ir à barra de endereços
        send_keys('%e')
        time.sleep(1)

        # 4. Digita o caminho e dá ENTER para confirmar a pasta
        send_keys(caminho_tmp, with_spaces=True)
        time.sleep(0.5)
        send_keys('{ENTER}')
        time.sleep(1.5)

    # 5. Alt+L para Salvar
    send_keys('%l')

    # Aguarda o Windows salvar o arquivo e fechar a janela "Salvar Como" sozinho
    time.sleep(3)

# ==========================================
# FUNÇÃO BASE DE RELATÓRIOS
# ==========================================
def _gerar_relatorio_generico(app: Application, data_alvo: str, atalho_teclado: str, nome_arquivo: str, digitar_caminho: bool = True) -> None:
    """Função mestre que navega, preenche datas e salva qualquer relatório padronizado."""
    app.top_window().set_focus()

    # 1. Navegação inicial nos menus
    send_keys(atalho_teclado)
    time.sleep(2)

    # Coleta a nova janela que se abriu e ESPERA ela ficar pronta
    janela_relatorio = app.top_window()
    janela_relatorio.wait('ready', timeout=15)

    # 2. Preenchimento de datas (Com espera de visibilidade)
    campo_data1 = janela_relatorio.child_window(auto_id="txtData1", control_type="Edit")
    campo_data1.wait('visible', timeout=10)
    campo_data1.type_keys(f"{{HOME}}{data_alvo}")

    campo_data2 = janela_relatorio.child_window(auto_id="txtData2", control_type="Edit")
    campo_data2.type_keys(f"{{HOME}}{data_alvo}")

    # 3. Gerar Relatório
    btn_gerar = janela_relatorio.child_window(auto_id="btnGerar", control_type="Button")
    btn_gerar.wait('visible', timeout=10)
    btn_gerar.set_focus()
    send_keys('{ENTER}')

    # 4. Finalização
    janela_visualizacao = aguardar_carregamento_relatorio(app)
    salvar_pdf(janela_visualizacao, nome_arquivo, digitar_caminho)

    # Fechamento seguro unificado
    fechar_janelas_em_cadeia(app)

# ==========================================
# FUNÇÕES ESPECÍFICAS
# ==========================================
def gerar_relatorio_selos(app: Application, data_alvo: str, dia: str, mes: str, ano: str) -> None:
    """Gera o relatório de selos utilizando a função mestre."""
    _gerar_relatorio_generico(
        app,
        data_alvo,
        atalho_teclado='{VK_MENU}{RIGHT 5}{DOWN 5}{RIGHT}{DOWN 5}{ENTER}',
        nome_arquivo=f"SELO-{dia}-{mes}-{ano}.pdf",
        digitar_caminho=True

    )

def gerar_relatorio_caixa(app: Application, data_alvo: str, dia: str, mes: str, ano: str) -> None:
    """Gera o relatório de caixa utilizando a função mestre."""
    _gerar_relatorio_generico(
        app,
        data_alvo,
        atalho_teclado='{VK_MENU}{RIGHT 7}{DOWN 3}{RIGHT}{DOWN 2}{ENTER}',
        nome_arquivo=f"Caixa-{dia}-{mes}-{ano}.pdf",
        digitar_caminho=False
    )

def gerar_relatorio_financeiro(app: Application, data: str, d: str, m: str, a: str) -> None:
    """Relatório Financeiro (Atos Praticados)."""
    app.top_window().set_focus()
    send_keys('{VK_MENU}{RIGHT 7}{DOWN 3}{RIGHT}{DOWN 20}{ENTER}')
    time.sleep(2)

    janela_relatorio = app.top_window()
    janela_relatorio.child_window(auto_id="txtData1", control_type="Edit").type_keys(f"{{HOME}}{data}")
    janela_relatorio.child_window(auto_id="txtData2", control_type="Edit").type_keys(f"{{HOME}}{data}")

    # --- CHECKBOXES ---
    logging.info("Configurando os CheckBoxes via teclado rápido...")
    checkboxes_marcar = [
        "chkEnquadramento", "chkIncluirRepasse", "chkExibirSelo",
        "chkImprimirEncargos", "chkTodasCobrancas", "chkTodasContas"
    ]
    checkboxes_desmarcar = ["chkAgrupaData"]

    for id_chk in checkboxes_marcar:
        try:
            caixa = janela_relatorio.child_window(auto_id=id_chk, control_type="CheckBox")
            if caixa.get_toggle_state() == 0:
                caixa.set_focus()
                send_keys('{SPACE}')
        except (ElementNotFoundError, RuntimeError, NoPatternInterfaceError):
            pass

    for id_chk in checkboxes_desmarcar:
        try:
            caixa = janela_relatorio.child_window(auto_id=id_chk, control_type="CheckBox")
            if caixa.get_toggle_state() == 1:
                caixa.set_focus()
                send_keys('{SPACE}')
        except (ElementNotFoundError, RuntimeError, NoPatternInterfaceError):
            pass

    # --- RADIO BUTTONS ---
    logging.info("Selecionando o formato Analítico...")
    try:
        rdb_analitico = janela_relatorio.child_window(auto_id="rdbAnalitico", control_type="RadioButton")
        rdb_analitico.set_focus()
        send_keys('{SPACE}')
        time.sleep(0.2)
    except (ElementNotFoundError, RuntimeError):
        pass

    # --- FILTRO DE ATOS ---
    logging.info("Abrindo a janela de Filtro de Atos...")
    btn_filtro = janela_relatorio.child_window(auto_id="btnFiltro", control_type="Button")
    btn_filtro.click_input()
    time.sleep(1)

    janela_filtro = app.top_window()
    btn_marcar_todos = janela_filtro.child_window(auto_id="btnMarcar", control_type="Button")
    btn_marcar_todos.click_input()
    time.sleep(0.5)

    logging.info("Desmarcando os atos específicos via teclado...")
    indices_para_desmarcar = [
        0, 2, 3, 4, 26, 38, 39, 61, 62, 63, 64, 65, 66, 67, 68, 69,
        70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
        85, 86, 87, 88, 89, 90, 91, 92
    ]

    try:
        linha_zero = janela_filtro.child_window(title=" Linha 0", control_type="DataItem")
        linha_zero.set_focus()
        time.sleep(0.5)

        if 0 in indices_para_desmarcar:
            send_keys('{SPACE}')
            time.sleep(0.1)

        for linha_atual in range(1, 93):
            send_keys('{DOWN}')
            time.sleep(0.05)
            if linha_atual in indices_para_desmarcar:
                send_keys('{SPACE}')
                time.sleep(0.05)
    except (ElementNotFoundError, RuntimeError) as e:
        logging.warning(f"Erro ao navegar na tabela de atos. Detalhe: {e}")

    time.sleep(0.5)
    btn_fechar = janela_filtro.child_window(auto_id="btFechar", control_type="Button")
    btn_fechar.click_input()
    time.sleep(1)

    # --- GERAR RELATÓRIO ---
    logging.info("Gerando o relatório financeiro...")
    btn_gerar = janela_relatorio.child_window(auto_id="btnGerar", control_type="Button")
    try:
        btn_gerar.set_focus()
        send_keys('{ENTER}')
    except (ElementNotFoundError, RuntimeError):
        btn_gerar.click_input()

    # --- FINALIZAÇÃO ---
    vis = aguardar_carregamento_relatorio(app)
    salvar_pdf(vis, f"Atos-{d}-{m}-{a}.pdf", digitar_caminho=False)
    fechar_janelas_em_cadeia(app)

def executar(data_alvo: str, caminho_exe: str) -> None:
    """Entrada do módulo."""
    app = Application(backend="uia").connect(path=caminho_exe)
    d, m, a = data_alvo[0:2], data_alvo[2:4], data_alvo[4:8]
    gerar_relatorio_selos(app, data_alvo, d, m, a)
    gerar_relatorio_financeiro(app, data_alvo, d, m, a)
    gerar_relatorio_caixa(app, data_alvo, d, m, a)