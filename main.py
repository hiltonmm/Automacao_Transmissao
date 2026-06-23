# -*- coding: utf-8 -*-
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# noinspection SpellCheckingInspection
import modulos.m01_iniciar as iniciar
# noinspection SpellCheckingInspection
import modulos.m02_relatorios as relatorios

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
# 3. Orquestração principal
# ==========================================
def main():
    logging.info("==================================================")
    logging.info("INÍCIO DA AUTOMAÇÃO TJRJ")
    logging.info("==================================================")


    git
    try:
        logging.info("--> Executando Passo 1: Login")
        data_alvo = iniciar.executar(USUARIO, SENHA, os.getenv("DOC_PATH"))
        logging.info(f"O módulo de login devolveu a data: {data_alvo}. Pronto para o Passo 2.")

        logging.info("--> Executando Passo 2: Emissão de Relatórios")
        relatorios.executar(data_alvo, os.getenv("DOC_PATH") or "")

    except Exception as e:
        logging.critical(f"ERRO FATAL NA AUTOMAÇÃO: {e}", exc_info=True)
    finally:
        logging.info("==================================================")
        logging.info("FIM DA EXECUÇÃO")
        logging.info("==================================================")


if __name__ == "__main__":
    main()