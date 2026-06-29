import os
import re
import pandas as pd
import pdfplumber


def formatar_valor_financeiro(valor) -> str:
    """Função global para limpar valores financeiros dos PDFs."""
    if valor is None:
        return "0,00"

    val_str = str(valor).strip()

    # Se estiver vazio, for um traço, ou não contiver dígitos, retorna 0,00
    if val_str in ["", "-", "nan", "None"] or not any(char.isdigit() for char in val_str):
        return "0,00"

    # Garante que o separador decimal seja vírgula
    return val_str.replace('.', ',')

# noinspection SpellCheckingInspection
def sanitizar_dataframe_atos(df):
    padrao_selo = r'^[A-Z]{3,4}\d{5}'
    df_limpo = df[df.iloc[:, 0].astype(str).str.contains(padrao_selo, na=False, regex=True)].copy()
    df_limpo.iloc[:, 0] = df_limpo.iloc[:, 0].str.split('|').str[0]
    return df_limpo


# noinspection SpellCheckingInspection
def extrair_atos_com_tabela(caminho_pdf: str, pasta_tmp: str, data_alvo: str) -> None:
    data = []
    colunas_finais = [
        "Selo", "TC", "Emol", "FETJ", "FUNDPERJ", "FUNPERJ", "FUNARPEN",
        "PMCMV", "FUNPGAL", "FUNPGT", "ISS", "SELO_V", "FUNDAC", "Distribuidor"
    ]

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if not tabela: continue
            for linha in tabela:
                linha = [str(c).strip() if c is not None else "" for c in linha]
                if len(linha) >= 19:
                    if "Nº OS" in linha[0] or "EMOLUMENTOS" in linha[3] or "Selo" in linha[17]: continue
                    try:
                        data.append([
                            linha[17], linha[18],
                            formatar_valor_financeiro(linha[3]), formatar_valor_financeiro(linha[4]),
                            formatar_valor_financeiro(linha[5]), formatar_valor_financeiro(linha[6]),
                            formatar_valor_financeiro(linha[7]), formatar_valor_financeiro(linha[8]),
                            formatar_valor_financeiro(linha[9]), formatar_valor_financeiro(linha[10]),
                            formatar_valor_financeiro(linha[11]), formatar_valor_financeiro(linha[12]),
                            formatar_valor_financeiro(linha[13]), formatar_valor_financeiro(linha[15])
                        ])
                    except (IndexError, ValueError):
                        continue

    df = pd.DataFrame(data, columns=colunas_finais)
    df = sanitizar_dataframe_atos(df)
    nome_arquivo = f"Atos_{data_alvo}.csv"
    df.to_csv(os.path.join(pasta_tmp, nome_arquivo), index=False, sep=';', encoding='utf-8-sig', decimal=',')


# noinspection SpellCheckingInspection
def sanitizar_dataframe_selos(df):
    padrao_selo = r'^[A-Z]{3,4}\d{5}'
    df_limpo = df[df.iloc[:, 0].astype(str).str.contains(padrao_selo, na=False, regex=True)].copy()
    df_limpo['TC'] = df_limpo['TC'].astype(str).str.strip()
    return df_limpo[(df_limpo['TC'] != '') & (df_limpo['TC'].str.lower() != 'nan')]


# noinspection SpellCheckingInspection
def extrair_selos_com_tabela(caminho_pdf: str, pasta_tmp: str, data_alvo: str) -> None:
    data = []
    colunas_finais = [
        "Selo", "TC", "Emol", "FETJ", "FUNDPERJ", "FUNPERJ", "FUNARPEN",
        "PMCMV", "FUNPGAL", "FUNPGT", "ISS", "SELO_V", "FUNDAC", "Distribuidor"
    ]

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if not tabela: continue
            for linha in tabela:
                linha = [str(c).strip() if c is not None else "" for c in linha]
                if len(linha) < 4: continue
                idx_numero = next((i for i, celula in enumerate(linha) if re.match(r'^\d{5}', celula)), -1)
                if idx_numero <= 0: continue
                try:
                    serie_limpa = re.sub(r'[^A-Z]', '', linha[idx_numero - 1])
                    match_num = re.search(r'^(\d{5})', linha[idx_numero])
                    if not match_num: continue
                    selo_id = serie_limpa + match_num.group(1)
                    tc_str = str(linha[-1]) + " " + str(linha[-2])
                    match_tc = re.search(r'\b(CC|JG|JH|SC)\b', tc_str)
                    tc = match_tc.group(1) if match_tc else ""

                    if tc in ["JG", "JH", "SC"]:
                        linha_dados = [selo_id, tc] + ["0,00"] * 12
                    else:
                        # Distribuidor também passa pela formatação global
                        distrib = formatar_valor_financeiro(linha[-3])
                        linha_dados = [
                            selo_id, tc,
                            formatar_valor_financeiro(linha[idx_numero + 2]),
                            formatar_valor_financeiro(linha[idx_numero + 3]),
                            formatar_valor_financeiro(linha[idx_numero + 4]),
                            formatar_valor_financeiro(linha[idx_numero + 5]),
                            formatar_valor_financeiro(linha[idx_numero + 6]),
                            formatar_valor_financeiro(linha[idx_numero + 7]),
                            formatar_valor_financeiro(linha[idx_numero + 8]),
                            formatar_valor_financeiro(linha[idx_numero + 9]),
                            formatar_valor_financeiro(linha[idx_numero + 10]),
                            formatar_valor_financeiro(linha[idx_numero + 11]),
                            formatar_valor_financeiro(linha[idx_numero + 12]),
                            distrib
                        ]
                    data.append(linha_dados)
                except (IndexError, AttributeError, ValueError):
                    continue
    df = pd.DataFrame(data, columns=colunas_finais)
    df = sanitizar_dataframe_selos(df)
    nome_arquivo = f"Selos_{data_alvo}.csv"
    df.to_csv(os.path.join(pasta_tmp, nome_arquivo), index=False, sep=';', encoding='utf-8-sig', decimal=',')