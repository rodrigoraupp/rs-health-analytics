# Análise de Ocupação e Eficiência Hospitalar no Estado do Rio Grande do Sul

## Sobre o Projeto

Este projeto analisa os dados de ocupação hospitalar do estado do Rio Grande do Sul utilizando os dados públicos do **DATASUS**, mais especificamente o Sistema de Informações Hospitalares (**SIH-RD**). O período de análise compreende janeiro de 2024 a junho de 2026, o que totaliza aproximadamente 2 milhões de registros.

## Desenvolvimento

- Extração de arquivos dos servidores (script `/src/ingestao.py`) e download no disco.
    - Dados de internações no estado do Rio Grande do Sul de janeiro de 2024 a junho de 2026 ([Pacote PySUS](https://pysus.readthedocs.io/en/latest/#));
    - Dados de municípios do Brasil e suas UFs ([API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades#api-Municipios-municipiosGet)).
    - Dicionário de dados para colunas de interesse, extraídos do arquivo `TAB_SIH.zip` localizado no servidor FTP do governo federal.


## Estrutura do Repo

O repositório está organizado da seguinte maneira:

```
.
├── docs
│   └── adr
│       └── 0001-fase-1-ingestao.md
├── notebooks
│   ├── 00_extraction.ipynb
│   └── 01_pre_process.ipynb
├── src
│   └── ingestao.py
├── environment.yml
├── README.md
└── setup.sh
```

Para montar uma árvore que mostra os diretórios e arquivos do repo, eu utilizei o pacote `tree`. Siga o passo a passo a seguir dentro do repositório para instalar e exibir a estrutura de diretórios em árvore.

```
# para instalar o pacote
sudo apt update && sudo apt install tree

# para exibir os arquivos respeitando o .gitignore
tree -I '.git' --gitignore --dirsfirst
```

## Como Reproduzir Este Projeto

Para garantir a reprodutibilidade, este projeto utiliza o gerenciador de ambientes Conda.

1. **Clone este repo**:

```
git clone https://github.com/rodrigoraupp/rs-health-analytics
cd rs-health-analytics
```

2. **Crie e ative o ambiente virtual**:

```
conda env create -f environment.yml
conda activate projeto_sih
```

3. **Autorize a execução das configurações iniciais rode**:

```
chmod +x setup.sh
./setup.sh
```