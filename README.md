# Robô de Automação TJRJ - Registro Civil

Este é um software de automação de alto desempenho desenvolvido para gerenciar o fluxo operacional do sistema **DOC-Windows** em cartórios de Registro Civil (RCPN). O robô automatiza o ciclo de vida completo de fechamento de caixa, auditoria financeira, geração de arquivos de transmissão e finalização de relatórios.

## 🚀 Principais Recursos

* **Orquestração Inteligente:** Fluxo automatizado via `pywinauto` que simula interações humanas no sistema, com tratamento de erros em tempo real.
* **Auditoria de Precisão (M.A.S):** Auditoria em três níveis, incluindo conferência cega entre Atos e Selos e validação financeira detalhada (FETJ, FUNARPEN, ISS, etc).
* **Conformidade Técnica:** Geração automática de arquivos XML com validação estrutural via esquemas **XSD** rigorosos, garantindo que a transmissão ao TJRJ ocorra sem rejeições.
* **Interface do Usuário (UI):** Interface gráfica amigável com centralização automática e máscara de digitação, minimizando erros operacionais no início de cada lote.
* **Contexto de Memória Segura:** Sistema de gerenciamento de estado (`Contexto`) com limpeza automática (`reset`) entre cada lote, prevenindo contaminação de dados financeiros entre datas diferentes.
* **Relatórios e Impressão:** Geração de PDFs consolidados de fechamento com cálculo automático de transferências bancárias e fila de impressão automática.

## 📂 Estrutura do Projeto

```text
├── logs/
├── tmp/
├── xsd/
│   ├── rcpn.xsd           # Xsd de validação do xml de atos do Registro Civil das Pessoas Naturais 
│   └── rit.xsd             # Xsd de validação do xml de atos de Interdições e Tutelas
├── modulos/
│   ├── iniciar.py         # Orquestração de login e ambiente
│   ├── relatorios.py      # Extração automatizada via interface
│   ├── auditoria.py       # Conferência financeira e de selos
│   ├── conversor_csv.py   # Processamento de dados tabulares (Pandas)
│   ├── gerador_xml.py     # Automação de exportação XML
│   ├── validador_xsd.py   # Auditoria técnica de normas TJRJ
│   ├── relatorio_final.py # Geração de PDF e fila de impressão
│   ├── ui.py              # Interface gráfica (captura de data)
│   ├── contexto.py        # Gestão de estado do robô
│   └── requirements.txt   # Dependências 
├── main.py                # Loop principal de execução
└── executar.bat           # Atalho de inicialização rápida
```

## 📋 Como Baixar, Instalar e Executar

### 1. Pré-requisitos

* **Python 3.10+** instalado.
* **Dependências:** Certifique-se de ter instalado as bibliotecas necessárias:
`pywinauto`, `pdfplumber`, `pandas`, `fpdf`, `lxml`, `python-dotenv`.
* **Ambiente:** Windows, com o DOC-Windows instalado no caminho configurado via `.env`.

### 2. Instalação

Após clonar o repositório, execute os comandos abaixo no terminal dentro da pasta do projeto:

```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

```

### 3. Configuração de Variáveis

Crie um arquivo `.env` na raiz do projeto contendo as credenciais e caminhos do sistema:

```text
DOC_USER=seu_usuario
DOC_PASS=sua_senha
DOC_PATH=C:\Caminho\Para\Doc-Windows.exe

```

### 4. Execução

Para iniciar o robô de forma profissional e automatizada, utilize o script de execução rápida fornecido:

```bash
executar.bat

```

## 🛡 Segurança e Confiabilidade

* **Isolamento de Dados:** Cada data processada inicia com um contexto limpo, garantindo que valores (como 'Depósitos Prévios') não sejam carregados de dias anteriores.
* **Tratamento de Erros:** O sistema utiliza `logging` completo para auditoria de cada passo e janelas de alerta nativas do Windows (`win32api`) em caso de paradas críticas.
* **Resiliência:** O robô utiliza *timeouts* inteligentes e verificações de existência de arquivos para garantir que nenhuma operação seja finalizada sem a devida validação.

---

*Este projeto foi desenvolvido para otimizar rotinas cartorárias, trazendo segurança jurídica e eficiência operacional.*