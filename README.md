# Análise de Ocupação e Eficiência Hospitalar no Estado do Rio Grande do Sul

## Sobre o Projeto

Este projeto analisa os dados de ocupação hospitalar do estado do Rio Grande do Sul utilizando os dados públicos do **DATASUS**, mais especificamente o Sistema de Informações Hospitalares (**SIH-RD**). O período de análise compreende janeiro de 2024 a junho de 2026, o que totaliza aproximadamente 2 milhões de registros.

## Arquitetura e Desenvolvimento

O projeto adota os princípios da **Arquitetura em Medalhão** (Bronze, Silver e Gold) para garantir modularidade, reprodutibilidade e gestão eficiente de memória no processamento dos microdados de saúde pública:

### 1. Camada Bronze — Ingestão e Dados Brutos
- **Extração Automatizada:** Download e organização local de arquivos via script modular (`/src/ingestao.py`) e notebook dedicado (`notebooks/99_extraction.ipynb`).
- **Fontes Integradas:**
  - Microdados de internações hospitalares do Rio Grande do Sul (Janeiro/2024 a Julho/2026) via [PySUS](https://pysus.readthedocs.io/en/latest/#).
  - Malha demográfica e códigos dos municípios via [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades#api-Municipios-municipiosGet).
  - Metadados e dicionários legados de conversão (`.CNV`) extraídos do arquivo `TAB_SIH.zip` via FTP do DATASUS.

### 2. Camada Silver — Data Quality e Sanitização (`notebooks/01_data_quality.ipynb`)
- **Auditoria & Quality Check:** Sanitização de strings para remoção de espaços em branco ocultos (`TRIM`), tratamento de nulos (`NULLIF`) e conversão segura de valores decimais monetários (`TRY_CAST`).
- **Explosão de Dimensão (ETL de CIDs):** Parser customizado em Python para desmembrar faixas alfanuméricas legadas em chaves individuais, viabilizando cruzamentos relacionais de alta performance no DuckDB.
- **Gestão de Memória RAM:** Implementação da classe `MonitorMemoria` para rastreamento de DataFrames Pandas e disparo forçado do Garbage Collector (`gc.collect()`).

### 3. Camada Gold — Análise Exploratória e Insights (`notebooks/02_eda.ipynb`)
- **Migração Hospitalar Estadual:** Mapeamento e ranqueamento temporal das Cidades Polo do Rio Grande do Sul com maior absorção de pacientes externos (2024–2026).
- **Divergência Volume vs. Custo:** Análise comparativa que isola o impacto do Ticket Médio por internação em municípios estratégicos como Pelotas e Caxias do Sul.
- **Matriz Origem-Destino (Pelotas):** Visualização da evolução do fluxo migratório regional direcionado ao polo hospitalar de Pelotas através de mapas de calor (*Heatmaps*) no Seaborn.

## Estrutura do Repo

O repositório está organizado da seguinte maneira:

```shell
.
├── docs
│   └── adr
│       └── 0001-fase-1-ingestao.md
├── notebooks
│   ├── 01_data_quality.ipynb   # silver
│   ├── 02_eda.ipynb            # gold
│   └── 99_extraction.ipynb     # testes de conexão
├── src
│   └── ingestao.py             # bronze
├── environment.yml
├── README.md
└── setup.sh
```

Para montar uma árvore que mostra os diretórios e arquivos do repo, eu utilizei o pacote `tree`. Siga o passo a passo a seguir dentro do repositório para instalar e exibir a estrutura de diretórios em árvore.

```shell
# para instalar o pacote
sudo apt update && sudo apt install tree

# para exibir os arquivos respeitando o .gitignore
tree -I '.git' --gitignore --dirsfirst
```

## Como Reproduzir Este Projeto

Para garantir a reprodutibilidade, este projeto utiliza o gerenciador de ambientes Conda.

1. **Clone este repo**:

```shell
git clone https://github.com/rodrigoraupp/rs-health-analytics
cd rs-health-analytics
```

2. **Crie e ative o ambiente virtual**:

```shell
conda env create -f environment.yml
conda activate projeto_sih
```

3. **Autorize a execução do shell script e rode**:

```shell
chmod +x setup.sh
./setup.sh
```

## Como Citar Este Projeto

No formato ABNT:

> RAUPP, Rodrigo de Laforet Padilha. **Análise de Ocupação e Eficiência Hospitalar no Estado do Rio Grande do Sul**. Versão 1.0. Pelotas, 2026. Disponível em: <<https://github.com/rodrigoraupp/rs-health-analytics>>. Acesso em: 31 out. 2026.

No formato BibLaTeX:

```bibtex
@software{raupp2026rshealth,
  author       = {Raupp, Rodrigo de Laforet Padilha},
  title        = {Análise de Ocupação e Eficiência Hospitalar no Estado do Rio Grande do Sul},
  year         = {2026},
  version      = {1.0},
  url          = {[https://github.com/rodrigoraupp/rs-health-analytics](https://github.com/rodrigoraupp/rs-health-analytics)},
  urldate      = {2026-10-31},
  address      = {Pelotas}
}
```