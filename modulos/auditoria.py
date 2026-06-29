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
    """Extrai as quantidades do quadro de resumo restringindo a análise ao rodapé do PDF."""
    resultados = {}

    # Restringe a busca aos últimos 2000 caracteres para evitar falsos positivos do corpo
    rodape = texto[-2000:] if len(texto) > 2000 else texto

    for tipo in ['CC', 'NH', 'JG', 'JH', 'SC']:
        matches = re.findall(rf'\b{tipo}[\s:]*(\d+)', rodape)
        resultados[tipo] = int(matches[-1]) if matches else 0
    return resultados


# ==========================================
# FUNÇÕES NÍVEL 2: VALORES FINANCEIROS
# ==========================================
def normalizar_moeda(valor):
    """Garante que o formato seja X.XXX,XX corrigindo falhas de leitura do PDF"""
    if not valor: return "0,00"
    if len(valor) >= 3 and valor[-3] == '.':
        valor = valor[:-3] + ',' + valor[-2:]
    return valor


def extrair_fundos_selos(texto):
    """Extrai os valores da lista vertical do relatório de Selos isolando o bloco de totais"""
    idx = texto.rfind("Total Emolumentos")
    if idx != -1:
        texto = texto[idx:]

    chaves = [
        ("Emolumentos", r'Emolumentos[^\d]*([\d\.,]+)'),
        ("FETJ", r'FETJ[^\d]*([\d\.,]+)'),
        ("FUNDPERJ", r'FUNDPERJ[^\d]*([\d\.,]+)'),
        ("FUNPERJ", r'FUNPERJ[^\d]*([\d\.,]+)'),
        ("FUNARPEN", r'FUNARPEN[^\d]*([\d\.,]+)'),
        ("PMCMV", r'PMCMV[^\d]*([\d\.,]+)'),
        ("FUNPGALERJ", r'FUNPGALERJ[^\d]*([\d\.,]+)'),
        ("FUNPGT", r'FUNPGT[^\d]*([\d\.,]+)'),
        ("ISS", r'ISS[^\d]*([\d\.,]+)'),
        ("SELO", r'SELO[^\d]*([\d\.,]+)'),
        ("FUNDAC_PGUERJ", r'([\d\.,]+)\s*FUNDAC')
    ]

    fundos = {}
    for nome, regex in chaves:
        match = re.search(regex, texto)
        fundos[nome] = normalizar_moeda(match.group(1)) if match else "0,00"
    return fundos


def extrair_fundos_atos(texto):
    """Extrai os valores da linha horizontal contínua do relatório de Atos"""
    idx = texto.find("Total geral:")
    if idx == -1: return {}
    trecho = texto[idx:]

    valores = re.findall(r'\b\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\b', trecho)

    if len(valores) >= 11:
        return {
            "Emolumentos": normalizar_moeda(valores[0]),
            "FETJ": normalizar_moeda(valores[1]),
            "FUNDPERJ": normalizar_moeda(valores[2]),
            "FUNPERJ": normalizar_moeda(valores[3]),
            "FUNARPEN": normalizar_moeda(valores[4]),
            "PMCMV": normalizar_moeda(valores[5]),
            "FUNPGALERJ": normalizar_moeda(valores[6]),
            "FUNPGT": normalizar_moeda(valores[7]),
            "ISS": normalizar_moeda(valores[8]),
            "SELO": normalizar_moeda(valores[9]),
            "FUNDAC_PGUERJ": normalizar_moeda(valores[10])
        }
    return {}


# ==========================================
# AUDITORIA NÍVEL 3: LINHA A LINHA (CSV)
# ==========================================
def comparacao_linha_a_linha(pdf_atos, pdf_selos, pasta_tmp, data_alvo):
    """Gera CSVs e realiza o cruzamento completo e exato de todas as colunas estruturais."""
    conversor_csv.extrair_atos_com_tabela(pdf_atos, pasta_tmp, data_alvo)
    conversor_csv.extrair_selos_com_tabela(pdf_selos, pasta_tmp, data_alvo)

    df_atos = pd.read_csv(os.path.join(pasta_tmp, f"Atos_{data_alvo}.csv"), sep=';', dtype=str)
    df_selos = pd.read_csv(os.path.join(pasta_tmp, f"Selos_{data_alvo}.csv"), sep=';', dtype=str)

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
        discrepancias.append(f"Selo {selo} presente em ATOS, mas AUSENTE em SELOS.")
    for selo in selos_selos - selos_atos:
        discrepancias.append(f"Selo {selo} presente em SELOS, mas AUSENTE em ATOS.")

    def limpa_para_comparar(valor):
        v = str(valor).strip().lower()
        if v in ['nan', 'none', '', '-']:
            return '0,00'
        return v.replace('.', ',')

    for selo in selos_atos.intersection(selos_selos):
        for col in colunas:
            val_a = limpa_para_comparar(df_atos.loc[selo, col])
            val_s = limpa_para_comparar(df_selos.loc[selo, col])

            if val_a != val_s:
                discrepancias.append(f"Selo: {selo} | Coluna: {col} | Atos: {val_a} | Selos: {val_s}")

    return "\n".join(discrepancias) if discrepancies else "Nenhuma divergência linha a linha encontrada."


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
        fundos_atos = extrair_fundos_atos(texto_atos)
        fundos_selos = extrair_fundos_selos(texto_selos)

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
        context.valores_financeiros = fundos_selos  # Salva os valores em Reais
        context.quantidades_cobranca = cobrancas_selos  # Salva os totais de CC, JG, etc.

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