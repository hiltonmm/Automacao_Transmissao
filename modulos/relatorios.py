# -*- coding: utf-8 -*-
# noinspection SpellCheckingInspection,NonAsciiCharacters,GrammarInspection,PyDuplicationCode,PyTypeChecker,PyUnusedLocal,PyUnresolvedReferences
import time
import logging
from pathlib import Path
from typing import Any
import win32api
from pywinauto.application import Application
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from pywinauto import mouse
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.uia_defines import NoPatternInterfaceError

BTN_IMPRIMIR = "Pr" + "int"


# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def fechar_janelas_em_cadeia(app: Application, num_esc: int = 1) -> None:
    """
    Fecha janelas de forma sequencial.
    :param app: Instância da aplicação.
    :param num_esc: Quantidade de vezes que a tecla ESC será pressionada.
    """
    logging.info(f"Fechando janelas com {num_esc} tentativas de ESC")
    for _ in range(num_esc):
        # noinspection PyBroadException
        try:
            # Garante que sempre pegamos a janela do topo atual em cada iteração
            app.top_window().set_focus()
            send_keys('{ESC}')
            time.sleep(1)
        except Exception:
            # Caso a janela desapareça antes de dar todos os ESCs, encerramos o loop
            break


def aguardar_carregamento_relatorio(app: Application) -> Any:
    """Aguarda carregamento do relatório."""
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


def imprimir_e_salvar_pdf(janela: Any, nome_arquivo: str) -> None:
    """Executa salvamento assumindo que a janela já está focada."""
    janela.set_focus()
    pos = win32api.GetCursorPos()

    # Clica em imprimir
    janela.child_window(title=BTN_IMPRIMIR, control_type="Button").click_input()
    mouse.move(coords=pos)

    # Aguarda a janela de impressão do Windows
    area = Desktop(backend="uia")
    janela_impressao = area.window(title="DOC-Windows - Imprimir")
    janela_impressao.wait('ready', timeout=15)
    janela_impressao.set_focus()
    time.sleep(1)

    # Seleção da impressora de forma direta e segura
    caixa = janela_impressao.child_window(control_type="ComboBox", found_index=0)
    caixa.set_focus()
    # Abre o dropdown usando o método do Pywinauto
    caixa.expand()
    time.sleep(0.5)

    try:
        # Tenta selecionar diretamente da lista
        caixa.select("Microsoft Print to PDF")
    except (ElementNotFoundError, RuntimeError):
        # Se falhar, usa a busca pelo nome do item na lista
        caixa.child_window(title="Microsoft Print to PDF", control_type="ListItem").click_input()

    time.sleep(1)
    # Fecha o dropdown e segue para o imprimir
    send_keys('{ENTER}')
    time.sleep(1)
    send_keys('{TAB 7}{ENTER}')

    # --- AQUI ESTÁ A MUDANÇA: Foco direto sem procurar ---
    # Como a janela já abre focada, apenas esperamos ela estabilizar
    time.sleep(4)

    caminho = str(Path(__file__).resolve().parent.parent / "tmp")

    # 1. Digitar o nome do arquivo
    send_keys('%n')
    time.sleep(0.5)
    send_keys(nome_arquivo, with_spaces=True)
    time.sleep(0.3)

    # 2. tecla controle + L (Abre a barra de endereços para navegação)
    send_keys('^l')
    time.sleep(0.5)

    # 3. Digitar o endereço da pasta tmp
    send_keys(caminho, with_spaces=True)
    time.sleep(0.3)

    # 4. ENTER (Confirma a mudança de pasta)
    send_keys('{ENTER}')
    time.sleep(1)

    # 5. Alt + L (Este comando força o foco no botão salvar ou na lista de arquivos em alguns Windows)
    send_keys('%l')
    time.sleep(1)

    # Pequena pausa para o sistema processar o arquivo antes de fechar a janela do relatório
    time.sleep(2)


# ==========================================
# ROTINA DE RELATÓRIO
# ==========================================
# noinspection PyUnusedLocal,PyUnresolvedReferences,SpellCheckingInspection
def gerar_relatorio_selos(app: Application, data_alvo: str, dia: str, mes: str, ano: str) -> None:
    """Gera o relatório de selos forçando os estados dos filtros via teclado."""
    app.top_window().set_focus()

    # Navegação inicial nos menus
    send_keys('{VK_MENU}{RIGHT 5}{DOWN 5}{RIGHT}{DOWN 5}{ENTER}')
    time.sleep(2)

    janela_relatorio = app.top_window()

    # Preenchimento de datas
    janela_relatorio.child_window(auto_id="txtData1", control_type="Edit").type_keys(f"{{HOME}}{data_alvo}")
    janela_relatorio.child_window(auto_id="txtData2", control_type="Edit").type_keys(f"{{HOME}}{data_alvo}")

    # Gerar Relatório
    # O foco já está na área de filtros, navegamos até o botão Gerar
    # Se o botão não estiver acessível via TABs, use o auto_id
    btn_gerar = janela_relatorio.child_window(auto_id="btnGerar", control_type="Button")
    btn_gerar.set_focus()
    send_keys('{ENTER}')

    # Finalização
    janela_visualizacao = aguardar_carregamento_relatorio(app)
    imprimir_e_salvar_pdf(janela_visualizacao, f"SELO-{dia}-{mes}-{ano}.pdf")
    fechar_janelas_em_cadeia(app)


# noinspection PyUnusedLocal,PyUnresolvedReferences,SpellCheckingInspection
def gerar_relatorio_financeiro(app: Application, data: str, d: str, m: str, a: str) -> None:
    """Relatório Financeiro."""
    app.top_window().set_focus()
    send_keys('{VK_MENU}{RIGHT 7}{DOWN 3}{RIGHT}{DOWN 20}{ENTER}')
    time.sleep(2)

    # CORREÇÃO: Unificação do nome da variável para janela_relatorio
    janela_relatorio = app.top_window()
    janela_relatorio.child_window(auto_id="txtData1", control_type="Edit").type_keys(f"{{HOME}}{data}")
    janela_relatorio.child_window(auto_id="txtData2", control_type="Edit").type_keys(f"{{HOME}}{data}")

    # ==========================================
    # --- CHECKBOXES ---
    # ==========================================
    print("Configurando os CheckBoxes via teclado rápido...")

    checkboxes_marcar = [
        "chkEnquadramento", "chkIncluirRepasse", "chkExibirSelo",
        "chkImprimirEncargos", "chkTodasCobrancas", "chkTodasContas"
    ]
    checkboxes_desmarcar = ["chkAgrupaData"]

    # Marcação Instantânea
    for id_chk in checkboxes_marcar:
        try:
            caixa = janela_relatorio.child_window(auto_id=id_chk, control_type="CheckBox")
            if caixa.get_toggle_state() == 0:
                caixa.set_focus()
                send_keys('{SPACE}')
        except (ElementNotFoundError, RuntimeError, NoPatternInterfaceError):
            pass

    # Desmarcação Instantânea
    for id_chk in checkboxes_desmarcar:
        try:
            caixa = janela_relatorio.child_window(auto_id=id_chk, control_type="CheckBox")
            if caixa.get_toggle_state() == 1:
                caixa.set_focus()
                send_keys('{SPACE}')
        except (ElementNotFoundError, RuntimeError, NoPatternInterfaceError):
            pass

    # ==========================================
    # --- RADIO BUTTONS ---
    # ==========================================
    print("Selecionando o formato Analítico...")
    try:
        rdb_analitico = janela_relatorio.child_window(auto_id="rdbAnalitico", control_type="RadioButton")
        rdb_analitico.set_focus()
        send_keys('{SPACE}')
        time.sleep(0.2)
    except (ElementNotFoundError, RuntimeError):
        pass

    print("\nFiltros configurados com sucesso!")

    # ==========================================
    # FILTRO DE ATOS (Bypass de Tabela Virtualizada)
    # ==========================================
    print("\nAbrindo a janela de Filtro de Atos...")
    btn_filtro = janela_relatorio.child_window(auto_id="btnFiltro", control_type="Button")
    btn_filtro.click_input()
    time.sleep(1)

    janela_filtro = app.top_window()
    print("Marcando todos os itens...")
    btn_marcar_todos = janela_filtro.child_window(auto_id="btnMarcar", control_type="Button")
    btn_marcar_todos.click_input()
    time.sleep(0.5)

    print("Desmarcando os atos específicos via teclado...")

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
        print(f"Erro ao navegar na tabela. Detalhe: {e}")

    time.sleep(0.5)
    print("Fechando a janela de filtro...")
    btn_fechar = janela_filtro.child_window(auto_id="btFechar", control_type="Button")
    btn_fechar.click_input()
    time.sleep(1)

    # ==========================================
    # GERAR RELATÓRIO
    # ==========================================
    print("Gerando o relatório...")

    # Atribui a variável fora do try para garantir que ela exista
    btn_gerar = janela_relatorio.child_window(auto_id="btnGerar", control_type="Button")

    try:
        btn_gerar.set_focus()
        send_keys('{ENTER}')
    except (ElementNotFoundError, RuntimeError):
        # Fallback caso o send_keys falhe
        btn_gerar.click_input()

    # ==========================================
    # FINALIZAÇÃO
    # ==========================================
    vis = aguardar_carregamento_relatorio(app)
    imprimir_e_salvar_pdf(vis, f"Atos-{d}-{m}-{a}.pdf")
    fechar_janelas_em_cadeia(app)


def executar(data_alvo: str, caminho_exe: str) -> None:
    """Entrada do módulo."""
    app = Application(backend="uia").connect(path=caminho_exe)
    d, m, a = data_alvo[0:2], data_alvo[2:4], data_alvo[4:8]
    gerar_relatorio_selos(app, data_alvo, d, m, a)
    gerar_relatorio_financeiro(app, data_alvo, d, m, a)