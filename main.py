# -*- coding: utf-8 -*-
import os
import sys
import logging
import traceback
import win32api
import win32con
from dotenv import load_dotenv
from datetime import datetime

# Módulos do Sistema
import modulos.iniciar as iniciar
import modulos.relatorios as relatorios
import modulos.auditoria as auditoria
from modulos.contexto import context
from modulos import gerador_xml
from modulos import validador_xsd
from modulos import relatorio_final
from modulos import ui

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
USUARIO = os.getenv("DOC_USER", "")
SENHA = os.getenv("DOC_PASS", "")
DOC_PATH = os.getenv("DOC_PATH", "")


# ==========================================
# 3. Exibe alertas do sistema
# ==========================================
def exibir_alerta_erro(mensagem_erro: str = "") -> None:
    mensagem = (
        "A automação foi interrompida!\n\n"
        f"{mensagem_erro if mensagem_erro else 'Verifique o arquivo de log para mais detalhes.'}"
    )
    estilo = win32con.MB_ICONERROR | win32con.MB_SYSTEMMODAL
    win32api.MessageBox(0, mensagem, "Erro na Automação", estilo)


# ==========================================
# 4. Orquestração principal
# ==========================================
def main():
    logging.info("==================================================")
    logging.info("INÍCIO DA AUTOMAÇÃO TJRJ")
    logging.info("==================================================")

    primeira_execucao = True
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    pasta_tmp = os.path.join(diretorio_atual, "tmp")

    while True:
        try:
            # 1 - Entrar no sistema ou solicitar nova data usando o padrão original
            if primeira_execucao:
                logging.info("-→ Executando Passo 1: Login")
                # Aqui o iniciar.executar chama internamente a sua função obter_data_interface
                data_alvo = iniciar.executar(USUARIO, SENHA, DOC_PATH)
                primeira_execucao = False
            else:
                logging.info("-→ Solicitando nova data ao usuário...")
                data_alvo = ui.obter_data_interface()  # Usa o módulo novo
                if not data_alvo or data_alvo.strip() == "":
                    break

                if not data_alvo or data_alvo.strip() == "":
                    logging.info("Usuário cancelou a inserção de nova data. Encerrando.")
                    break

            # 2 - Emissão de Relatórios
            logging.info(f"-→ Executando Passo 2: Emissão de Relatórios para {data_alvo}")
            relatorios.executar(data_alvo, DOC_PATH)

            # 3 - Auditoria (Estruturada e Determinística)

            logging.info("--> Passo 3: Auditoria Estrita de Relatórios")
            auditoria.executar(data_alvo, pasta_tmp)

            # Validação do contexto de auditoria
            resultado = context.resultado_auditoria
            if resultado and resultado.get("status") == "divergencias":
                raise RuntimeError(f"Divergências encontradas: {resultado.get('detalhes')}")

            # 4 e 5 - XML e XSD
            gerador_xml.executar(data_alvo)
            validador_xsd.executar(data_alvo)

            # 6 - Finalização
            relatorio_final.executar(data_alvo)

            # Pergunta de continuidade (Padrão Windows)
            estilo = win32con.MB_YESNO | win32con.MB_ICONQUESTION | win32con.MB_SYSTEMMODAL
            resposta = win32api.MessageBox(0, "Processamento concluído com sucesso!\n\nDeseja processar outra data?",
                                           "Sucesso", estilo)

            if resposta != win32con.IDYES:
                logging.info("Usuário escolheu encerrar.")
                break

        except Exception as e:
            logging.critical(f"ERRO FATAL: {e}")
            logging.critical(traceback.format_exc())
            exibir_alerta_erro(str(e))
            break

    logging.info("==================================================")
    logging.info("FIM DA EXECUÇÃO")
    logging.info("==================================================")


if __name__ == "__main__":
    main()