# -*- coding: utf-8 -*-
import os
import re
import logging
from typing import Any
from fpdf import FPDF
import pdfplumber
from .contexto import context
import win32api
import win32print


def imprimir_pdf(caminho_pdf: str):
    """Envia um arquivo PDF para a impressora padrão do Windows."""
    try:
        impressora = win32print.GetDefaultPrinter()
        logging.info(f"Imprimindo {os.path.basename(caminho_pdf)} na impressora: {impressora}")

        # O comando imprimir envia o arquivo para a impressora associada ao leitor de PDF padrão
        win32api.ShellExecute(0, "print", caminho_pdf, "", ".", 0)
        return True
    except Exception as e:
        logging.error(f"Falha ao imprimir {caminho_pdf}: {e}")
        return False


def extrair_depositos_previos_dinheiro(caminho_pdf: str) -> bool:
    """Varre o PDF em busca do valor de Depósitos Prévios (Dinheiro)."""

    # GARANTIA: Sempre reseta para 0.0 antes de tentar ler o novo PDF
    context.depositos_previos_dinheiro = 0.0

    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for i, pagina in enumerate(pdf.pages):
                texto = pagina.extract_text() or ""
                match = re.search(r"Dinheiro.*?Depósitos Prévios\s+([\d.,]+)", texto, re.DOTALL)

                if match:
                    valor_str = match.group(1)
                    valor_float = float(valor_str.replace('.', '').replace(',', '.'))

                    context.depositos_previos_dinheiro = valor_float
                    logging.info(f"Valor extraído na página {i + 1}: R$ {valor_float:.2f}")
                    return True

        logging.warning("O valor de 'Depósitos Prévios (Dinheiro)' não foi localizado no PDF. Valor definido como 0.0.")
        return False  # O contexto já foi limpo no início da função

    except Exception as e:
        logging.error(f"Erro ao extrair depósitos prévios: {e}")
        return False

def salvar_relatorio_pdf(data_alvo: str):
    """Gera o arquivo PDF final de forma robusta e limpa."""

    def to_float(valor: Any) -> float:
        if isinstance(valor, (int, float)): return float(valor)
        if isinstance(valor, str):
            return float(valor.replace('.', '').replace(',', '.'))
        return 0.0

    # Acessa os dados do contexto
    fin = getattr(context, 'valores_financeiros', {})
    quantidades = getattr(context, 'quantidades_cobranca', {})

    # Converte os valores financeiros
    e = to_float(fin.get('Emolumentos', 0.0))
    p = to_float(fin.get('PMCMV', 0.0))
    s = to_float(fin.get('SELO', 0.0))
    iss = to_float(fin.get('ISS', 0.0))
    dp = to_float(getattr(context, 'depositos_previos_dinheiro', 0.0))

    # Cálculos
    sub1 = e + p + s
    sub2 = sub1 - dp
    sub3 = sub2 + iss

    # Caminho da pasta tmp
    diretorio_base = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    caminho_tmp = os.path.join(diretorio_base, "tmp")
    if not os.path.exists(caminho_tmp):
        os.makedirs(caminho_tmp)

    # Formatação de data
    data_formatada1 = f"{data_alvo[0:2]}/{data_alvo[2:4]}/{data_alvo[4:8]}"
    data_formatada2 = f"{data_alvo[0:2]}-{data_alvo[2:4]}-{data_alvo[4:8]}"
    nome_pdf = f"Relatorio_Fechamento_{data_formatada2}.pdf"
    caminho_completo = os.path.join(caminho_tmp, nome_pdf)

    # Criar PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"ATOS PRATICADOS EM {data_formatada1}", align='C')
    pdf.ln(20)

    # Função interna para adicionar linhas (SEM ARGUMENTO ln=1 dentro da célula)
    def add_linha(desc: str, valor: float, negrito: bool = False):
        pdf.set_font("Arial", 'B' if negrito else '', 12)
        pdf.cell(120, 10, desc, border=1)
        pdf.cell(60, 10, f"R$ {valor:,.2f}", border=1, align='R')
        pdf.ln(10) # Quebra de linha externa, evita erro de tipo

    add_linha("EMOLUMENTOS", e)
    add_linha("PMCMV", p)
    add_linha("SELOS", s)
    add_linha("SUBTOTAL 1", sub1, True)
    add_linha("(-) Depósito Prévio em Espécie", dp)
    add_linha("SUBTOTAL 2 (Valor do Oficial)", sub2, True)
    add_linha("(+) Retenção ISS", iss)
    add_linha("SUBTOTAL 3 (Valor transferência Oficial)", sub3, True)

    # Bloco de Quantidades
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Quantidades de atos praticados por tipo de cobrança", align='L')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    texto_quantidades = " | ".join([f"{tipo}: {qtd}" for tipo, qtd in quantidades.items()])
    pdf.cell(0, 10, texto_quantidades, border=1, align='C')

    # Salva o arquivo
    pdf.output(caminho_completo)
    logging.info(f"Relatório PDF gerado com sucesso: {caminho_completo}")


def executar(data_alvo: str):
    """Orquestra a leitura do PDF de caixa, a geração do relatório final e a impressão da fila."""

    # 1. Preparação de caminhos e nomes de arquivos
    diretorio_atual = str(os.path.abspath(__file__))
    diretorio_base = str(os.path.dirname(os.path.dirname(diretorio_atual)))

    data_formatada = f"{data_alvo[0:2]}-{data_alvo[2:4]}-{data_alvo[4:8]}"
    nome_caixa = f"Caixa-{data_formatada}.pdf"

    # Garante que o caminho da pasta seja uma string válida
    caminho_tmp = os.path.join(diretorio_base, "tmp")
    caminho_caixa = os.path.join(caminho_tmp, nome_caixa)

    logging.info(f"--> Executando Passo 6: Finalização, Relatórios e Impressão")

    # 2. Leitura do PDF de Conferência de Caixa
    if os.path.exists(caminho_caixa):
        extrair_depositos_previos_dinheiro(caminho_caixa)
    else:
        logging.warning(f"PDF de conferência não encontrado: {nome_caixa}")

    # 3. Geração do Relatório de Fechamento PDF
    salvar_relatorio_pdf(data_alvo)

    # 4. Impressão da fila de relatórios
    arquivos_para_imprimir = [
        f"SELO-{data_formatada}.pdf",
        f"Atos-{data_formatada}.pdf",
        f"Relatorio_Fechamento_{data_formatada}.pdf"
    ]

    logging.info("--> Iniciando fila de impressão automática.")

    for nome_arq in arquivos_para_imprimir:
        caminho_completo = os.path.join(caminho_tmp, nome_arq)
        if os.path.exists(caminho_completo):
            # Chama a função de impressão que utiliza win32api
            if imprimir_pdf(caminho_completo):
                logging.info(f"Impressão enviada: {nome_arq}")
            else:
                logging.error(f"Erro ao imprimir: {nome_arq}")
        else:
            logging.warning(f"Arquivo não encontrado para impressão: {nome_arq}")

    logging.info("--> Fluxo de finalização concluído.")