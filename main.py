# -*- coding: utf-8 -*-
import os
import sys
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv
import win32api
import win32con

# noinspection SpellCheckingInspection
import modulos.iniciar as iniciar
# noinspection SpellCheckingInspection
import modulos.relatorios as relatorios

# ==========================================
# 1. Configuração do sistema de logs
# ==========================================
if not os.path.exists("logs"):
    os.makedirs("logs")

log_filename = f"logs/execucao_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ==========================================
# 2. Carregar variáveis seguras (.env)
# ==========================================
load_dotenv()
# noinspection SpellCheckingInspection
USUARIO = os.getenv("DOC_USER")
SENHA = os.getenv("DOC_PASS")

# ==========================================
# 3. Exibe alerta do sistema
# ==========================================
def exibir_alerta_erro() -> None:
    """Exibe uma caixa de alerta limpa orientando o usuário a checar o log."""
    mensagem = (
        "A automação foi interrompida devido a um erro inesperado.\n\n"
        "Por favor, verifique o arquivo de log de erros para mais detalhes."
    )
    estilo = win32con.MB_ICONERROR | win32con.MB_SYSTEMMODAL
    win32api.MessageBox(0, mensagem, "Erro na Automação", estilo)

def exibir_alerta_sucesso() -> None:
    """Exibe uma caixa de mensagem informando que a execução terminou com sucesso."""
    mensagem = "A automação foi finalizada com sucesso e sem erros!"
    # MB_ICONINFORMATION mostra o balão azul de informação e faz o som de sucesso do Windows
    estilo = win32con.MB_ICONINFORMATION | win32con.MB_SYSTEMMODAL
    win32api.MessageBox(0, mensagem, "Automação Concluída", estilo)

# ==========================================
# 4. Orquestração principal
# ==========================================
def main():
    logging.info("==================================================")
    logging.info("INÍCIO DA AUTOMAÇÃO TJRJ")
    logging.info("==================================================")


    try:
        #1 - Entrar no sistema
        logging.info("--> Executando Passo 1: Login")
        data_alvo = iniciar.executar(USUARIO, SENHA, os.getenv("DOC_PATH"))
        logging.info(f"O módulo de login devolveu a data: {data_alvo}. Pronto para o Passo 2.")

        #2 - Gerar Relatórios
        logging.info("--> Executando Passo 2: Emissão de Relatórios")
        relatorios.executar(data_alvo, os.getenv("DOC_PATH") or "")

        # --- SE CHEGAR AQUI, DEU TUDO CERTO ---
        exibir_alerta_sucesso()

    except Exception as e:
        # 1. Registra no arquivo de Log (Técnico e detalhado)
        logging.critical(f"ERRO FATAL NA AUTOMAÇÃO: {e}")
        logging.critical(traceback.format_exc())

        # 2. Exibe EXATAMENTE no terminal para você depurar
        print("\n" + "=" * 60, file=sys.stderr)
        print(" [CRITICAL] A AUTOMAÇÃO TRAVOU! VEJA O ERRO ABAIXO:", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        # 3. Dispara o alerta visual limpo para o usuário
        exibir_alerta_erro()
    finally:
        logging.info("==================================================")
        logging.info("FIM DA EXECUÇÃO")
        logging.info("==================================================")


if __name__ == "__main__":
    main()