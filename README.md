# Análise de Ocupação e Eficiência Hospitalar no Estado do Rio Grande do Sul

## Sobre o Projeto

Este projeto analisa os dados de ocupação hospitalar do estado do Rio Grande do Sul utilizando os dados públicos do **DATASUS**, mais especificamente o Sistema de Informações Hospitalares (**SIH-RD**). O período de análise compreende janeiro de 2024 a junho de 2026, o que totaliza aproximadamente 2 milhões de registros.

## Arquitetura e Desenvolvimento

### 1. Ingestão e Estruturação de Dados
- Extração automatizada de arquivos dos servidores governamentais para armazenamento local via script (`/src/ingestao.py`).
- Consumo dos dados de internações hospitalares do Rio Grande do Sul (Janeiro de 2024 a Junho de 2026) utilizando o [Pacote PySUS](https://pysus.readthedocs.io/en/latest/#).
- Integração da base demográfica de municípios e UFs brasileiras consumida via [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades#api-Municipios-municipiosGet).
- Processamento e estruturação dos dicionários de metadados extraídos do arquivo `TAB_SIH.zip` (servidor FTP do DATASUS), formatados para cruzar com as colunas de interesse.

### 2. Data Quality e Análise Exploratória (EDA)
- **Quality Check (DuckDB & Pandas):** Execução de testes de conformidade, tipagem de colunas e identificação de valores nulos ocultos nos microdados do SIH/SUS.
- **Sumarização Categórica:** Mapeamento dinâmico de especialidades e demografia através do cruzamento entre os arquivos parquet legados e as descrições da API.
- **Análise de Migração Hospitalar:** Avaliação do impacto de pacientes externos na rede de saúde, identificando as Cidades Polo do Rio Grande do Sul que mais recebem migrantes (2024-2026).
- **Mapa de Calor (Heatmap) de Pelotas:** Modelagem da matriz Origem-Destino no Seaborn para monitorar a evolução do fluxo de migração de pacientes da região sul em direção ao polo de Pelotas.


## Estrutura do Repo

O repositório está organizado da seguinte maneira:

```shell
.
├── docs
│   └── adr
│       └── 0001-fase-1-ingestao.md
├── notebooks
│   ├── 01_eda.ipynb
│   └── 99_extraction.ipynb
├── src
│   └── ingestao.py
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