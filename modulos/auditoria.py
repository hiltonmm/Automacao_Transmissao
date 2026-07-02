# -*- coding: utf-8 -*-
import os
import re
import logging
import pdfplumber
import pandas as pd
from modulos import conversor_csv
from modulos.contexto import context


# ==========================================
# EXTRAÇÃO DE TEXTO DO PDF
# ==========================================
def extrair_texto_pdf(caminho_arquivo: str) -> str:
    texto = ""
    with pdfplumber.open(caminho_arquivo) as pdf:
        for pagina in pdf.pages:
            t_pag = pagina.extract_text()
            if t_pag:
                texto += t_pag + "\n"
    return texto


# ==========================================
# FUNÇÕES NÍVEL 1: TIPOS DE COBRANÇA
# ==========================================
def extrair_tipos_cobranca(texto):
    """Extrai as quantidades isolando o bloco de totais no final do documento."""
    resultados = {'CC': 0, 'NH': 0, 'JG': 0, 'JH': 0, 'SC': 0}

    # Isola a busca apenas na área correta para evitar contagens falsas do corpo do texto
    idx = texto.rfind("Total Tipo de Cobrança")
    if idx != -1:
        # Troca quebras de linha por espaço para criar um bloco de texto contínuo
        bloco = texto[idx:].replace('\n', ' ')
        for tipo in resultados.keys():
            # Procura a sigla, ignora tudo que não for dígito, e captura o número
            match = re.search(rf'\b{tipo}\D*(\d+)', bloco)
            if match:
                resultados[tipo] = int(match.group(1))

    return resultados


# ==========================================
# FUNÇÕES NÍVEL 2: VALORES FINANCEIROS
# ==========================================
def normalizar_moeda(valor):
    """Garante que o formato seja X.XXX,XX corrigindo falhas (ex: 4.287.13 para 4.287,13)"""
    if not valor: return "0,00"
    valor = valor.strip()
    if len(valor) >= 3 and valor[-3] == '.':
        valor = valor[:-3] + ',' + valor[-2:]
    return valor


def extrair_fundos_selos(texto):
    """Extrai os valores da lista vertical do relatório de Selos."""
    idx = texto.rfind("Total Emolumentos")
    if idx != -1:
        texto = texto[idx:]

    chaves = [
        ("Emolumentos", r'Total Emolumentos[^\d]*([\d\.,]+)'),
        ("FETJ", r'Total FETJ[^\d]*([\d\.,]+)'),
        ("FUNDPERJ", r'Total FUNDPERJ[^\d]*([\d\.,]+)'),
        ("FUNPERJ", r'Total FUNPERJ[^\d]*([\d\.,]+)'),
        ("FUNARPEN", r'Total FUNARPEN[^\d]*([\d\.,]+)'),
        ("PMCMV", r'Total PMCMV[^\d]*([\d\.,]+)'),
        ("FUNPGALERJ", r'Total FUNPGALERJ[^\d]*([\d\.,]+)'),
        ("FUNPGT", r'Total FUNPGT[^\d]*([\d\.,]+)'),
        ("ISS", r'Total ISS[^\d]*([\d\.,]+)'),
        ("SELO", r'Total SELO[^\d]*([\d\.,]+)'),
        # CORREÇÃO: Captura o número que aparece ANTES da palavra FUNDAC
        ("FUNDAC_PGUERJ", r'([\d\.,]+)\s*FUNDAC_PGUERJ')
    ]

    fundos = {}
    for nome, regex in chaves:
        match = re.search(regex, texto, re.IGNORECASE)
        fundos[nome] = normalizar_moeda(str(match.group(1))) if match else "0,00"
    return fundos


def extrair_fundos_atos(caminho_pdf):
    """
    Lê a estrutura física da tabela do PDF de Atos, preservando colunas vazias.
    Utiliza o mapeamento exato de índices fornecido para evitar 'efeito dominó'.
    """
    fundos_encontrados = {
        "Emolumentos": "0,00", "FETJ": "0,00", "FUNDPERJ": "0,00",
        "FUNPERJ": "0,00", "FUNARPEN": "0,00", "PMCMV": "0,00",
        "FUNPGALERJ": "0,00", "FUNPGT": "0,00", "ISS": "0,00",
        "SELO": "0,00", "FUNDAC_PGUERJ": "0,00"
    }

    def limpar_celula(valor):
        """Limpa a célula e pega apenas o valor final (caso haja quebras de linha)."""
        if not valor or str(valor).strip() == "":
            return "0,00"
        # Pega a última linha da célula (o total geral definitivo)
        str_valor = str(valor).strip().split('\n')[-1].strip()
        # Se na extração houver lixo não numérico, a regex limpa
        numero_puro = re.search(r'([\d.,]+)', str_valor)
        if numero_puro:
            return normalizar_moeda(numero_puro.group(1))
        return "0,00"

    with pdfplumber.open(caminho_pdf) as pdf:
        # A linha de totais geralmente está na última página
        for pagina in reversed(pdf.pages):
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Verifica se a linha atual contém o "Total geral" na Coluna 0
                    if linha and linha[0] and "Total geral" in str(linha[0]):
                        try:
                            # Mapeamento Determinístico (Exato)
                            fundos_encontrados["Emolumentos"] = limpar_celula(linha[3])
                            fundos_encontrados["FETJ"] = limpar_celula(linha[4])
                            fundos_encontrados["FUNDPERJ"] = limpar_celula(linha[5])
                            fundos_encontrados["FUNPERJ"] = limpar_celula(linha[6])
                            fundos_encontrados["FUNARPEN"] = limpar_celula(linha[7])
                            fundos_encontrados["PMCMV"] = limpar_celula(linha[8])
                            fundos_encontrados["FUNPGALERJ"] = limpar_celula(linha[9])
                            fundos_encontrados["FUNPGT"] = limpar_celula(linha[10])
                            fundos_encontrados["ISS"] = limpar_celula(linha[11])
                            fundos_encontrados["SELO"] = limpar_celula(linha[12])
                            fundos_encontrados["FUNDAC_PGUERJ"] = limpar_celula(linha[13])
                        except IndexError:
                            logging.warning("Colunas insuficientes na linha de Totais de Atos.")

                        return fundos_encontrados

    return fundos_encontrados


# ==========================================
# AUDITORIA NÍVEL 3: LINHA A LINHA (CSV)
# ==========================================
def comparacao_linha_a_linha(pdf_atos, pdf_selos, pasta_tmp, data_alvo):
    """Gera CSVs e realiza o cruzamento completo e exato de todas as colunas estruturais."""
    # NOTA: Se o módulo conversor_csv também quebrou com o novo PDF, será necessário ajustá-lo futuramente.
    conversor_csv.extrair_atos_com_tabela(pdf_atos, pasta_tmp, data_alvo)
    conversor_csv.extrair_selos_com_tabela(pdf_selos, pasta_tmp, data_alvo)

    try:
        df_atos = pd.read_csv(os.path.join(pasta_tmp, f"Atos_{data_alvo}.csv"), sep=';', dtype=str)
        df_selos = pd.read_csv(os.path.join(pasta_tmp, f"Selos_{data_alvo}.csv"), sep=';', dtype=str)
    except Exception as e:
        return f"Falha ao carregar CSV para Nível 3. O módulo conversor_csv pode precisar de adaptação ao novo PDF: {e}"

    df_atos.set_index('Selo', inplace=True)
    df_selos.set_index('Selo', inplace=True)

    discrepancias = []

    # Rastreabilidade de registros duplicados nos indexadores
    duplicados_a = df_atos.index[df_atos.index.duplicated()].unique().tolist()
    duplicados_s = df_selos.index[df_selos.index.duplicated()].unique().tolist()

    if duplicados_a:
        discrepancias.append(f"ERRO CRÍTICO: Selos DUPLICADOS no arquivo de ATOS: {', '.join(duplicados_a)}")
    if duplicados_s:
        discrepancias.append(f"ERRO CRÍTICO: Selos DUPLICADOS no arquivo de SELOS: {', '.join(duplicados_s)}")

    df_atos = df_atos[~df_atos.index.duplicated(keep='first')]
    df_selos = df_selos[~df_selos.index.duplicated(keep='first')]

    colunas = ["TC", "Emol", "FETJ", "FUNDPERJ", "FUNPERJ", "FUNARPEN", "PMCMV", "FUNPGAL", "FUNPGT", "ISS", "SELO_V",
               "FUNDAC", "Distribuidor"]

    selos_atos = set(df_atos.index)
    selos_selos = set(df_selos.index)

    for selo in selos_atos - selos_selos:
        discrepancias.append(f"Selo {selo} presente em ATOS, mas Ausente em SELOS.")
    for selo in selos_selos - selos_atos:
        discrepancias.append(f"Selo {selo} presente em SELOS, mas Ausente em ATOS.")

    def limpa_para_comparar(valor):
        v = str(valor).strip().lower()
        if v in ['nan', 'none', '', '-']:
            return '0,00'
        return v.replace('.', ',')

    for selo in selos_atos.intersection(selos_selos):
        for col in colunas:
            if col in df_atos.columns and col in df_selos.columns:
                val_a = limpa_para_comparar(df_atos.loc[selo, col])
                val_s = limpa_para_comparar(df_selos.loc[selo, col])

                if val_a != val_s:
                    discrepancias.append(f"Selo: {selo} | Coluna: {col} | Atos: {val_a} | Selos: {val_s}")

    return "\n".join(discrepancias) if discrepancias else "Nenhuma divergência linha a linha encontrada."


# ==========================================
# FUNÇÃO PRINCIPAL DO MÓDULO (MAESTRO)
# ==========================================
def executar(data_alvo: str, pasta_tmp: str) -> None:
    try:
        dia, mes, ano = data_alvo[0:2], data_alvo[2:4], data_alvo[4:8]
        arq_a = os.path.join(pasta_tmp, f"Atos-{dia}-{mes}-{ano}.pdf")
        arq_s = os.path.join(pasta_tmp, f"SELO-{dia}-{mes}-{ano}.pdf")

        texto_atos = extrair_texto_pdf(arq_a)
        texto_selos = extrair_texto_pdf(arq_s)

        # --- NÍVEL 1: QUANTIDADE E TIPOS DE COBRANÇA ---
        logging.info("[Auditando Nível 1] Verificando Tipos de Cobrança (CC, NH, JG, JH, SC)...")
        cobrancas_atos = extrair_tipos_cobranca(texto_atos)
        cobrancas_selos = extrair_tipos_cobranca(texto_selos)

        logging.info(f"Atos:  {cobrancas_atos}")
        logging.info(f"Selos: {cobrancas_selos}")

        if cobrancas_atos != cobrancas_selos:
            logging.error("X FALHA NO NÍVEL 1: Quantidades ou tipos de cobrança divergentes.")
            detalhes_erro = comparacao_linha_a_linha(arq_a, arq_s, pasta_tmp, data_alvo)
            raise RuntimeError(
                f"O ROBÔ ENCONTROU DIVERGÊNCIAS NAS QUANTIDADES OU TIPOS DE COBRANÇAS!\n\n"
                f"Totais no Relatório de ATOS: {cobrancas_atos}\n"
                f"Totais no Relatório de SELOS: {cobrancas_selos}\n"
                f"--------------------------------------------------\n"
                f"RESULTADO DA ANÁLISE LINHA A LINHA:\n"
                f"{detalhes_erro}\n\n"
                f"É NECESSÁRIA ANÁLISE HUMANA NESTE LOTE."
            )

        logging.info("✓ Nível 1 Aprovado: Quantidades e tipos de cobrança idênticos.")

        # --- NÍVEL 2: VALORES FINANCEIROS DETALHADOS ---
        logging.info("[Auditando Nível 2] Verificando todos os fundos e taxas (FETJ, FUNARPEN, etc)...")

        # 1. Extrai os selos usando o texto
        fundos_selos = extrair_fundos_selos(texto_selos)

        # 2. CORREÇÃO: Lê a tabela do PDF de Atos cirurgicamente pelos índices
        fundos_atos = extrair_fundos_atos(arq_a)

        erros_financeiros = []
        logging.info("-" * 50)
        for fundo, valor_selo in fundos_selos.items():
            valor_ato = fundos_atos.get(fundo, "0,00")

            status = "OK" if valor_ato == valor_selo else "ERRO"
            logging.info(f"[{status}] {fundo.ljust(15)} | Atos: R$ {valor_ato.ljust(10)} | Selos: R$ {valor_selo}")

            if valor_selo != valor_ato:
                erros_financeiros.append(f"{fundo}: ATOS (R$ {valor_ato}) vs SELOS (R$ {valor_selo})")
        logging.info("-" * 50)

        if erros_financeiros:
            logging.error("X FALHA NO NÍVEL 2: Valores consolidados divergentes.")
            detalhes_erro = comparacao_linha_a_linha(arq_a, arq_s, pasta_tmp, data_alvo)
            msg_fundos = "\n".join(erros_financeiros)

            raise RuntimeError(
                f"O ROBÔ ENCONTROU DIVERGÊNCIAS NAS TAXAS FINANCEIRAS!\n\n"
                f"Diferenças encontradas:\n{msg_fundos}\n"
                f"--------------------------------------------------\n"
                f"RESULTADO DA ANÁLISE LINHA A LINHA:\n"
                f"{detalhes_erro}\n\n"
                f"É NECESSÁRIA ANÁLISE HUMANA NESTE LOTE."
            )

        logging.info("✓ Nível 2 Aprovado: Todos os valores detalhados (FETJ, PMCMV, etc) estão idênticos.")
        logging.info("--- CONFERÊNCIA CONCLUÍDA COM SUCESSO! RELATÓRIOS AUDITADOS E VALIDADOS. ---")

        # ==========================================
        # SALVANDO DADOS NO CONTEXTO PARA USO FUTURO
        # ==========================================
        context.resultado_auditoria = {"status": "sucesso"}
        context.valores_financeiros = fundos_selos
        context.quantidades_cobranca = cobrancas_selos

    finally:
        # ==========================================
        # PERSISTÊNCIA COMPLETA DO CONTEXTO NO LOG
        # ==========================================
        logging.info("=" * 60)
        logging.info(" DADOS ATUAIS DO CONTEXTO DA AUTOMAÇÃO ".center(60, "#"))
        logging.info("=" * 60)
        try:
            dados_contexto = vars(context)
            for chave, valor in dados_contexto.items():
                logging.info(f" -> {chave}: {valor}")
        except TypeError:
            logging.info(f" -> {context}")
        logging.info("=" * 60)