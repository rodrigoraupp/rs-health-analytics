#!usr/bin/env python3
"""
Pipeline de ingestão de dados SIH-RD e dados auxiliares.
Script responsável por executar o download dos microdados
a lista de municípios do IBGE e extrair os dicionários de
especialidades do DATASUS.
"""

# bibliotecas
import logging
import os
from pathlib import Path
import re
import zipfile

import pysus
import pandas as pd

# CONFIGURAÇÕES GERAIS
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s", 
    datefmt="%H:%M:%S"
)

# parâmetros do local e faixa de tempo da análise
ESTADO = 'RS'
ANOS = [2024, 2025, 2026]
MESES = list(range(1,13))

# urls para download
URL_TAB_SIH = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Auxiliar/TAB_SIH.zip"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

# resolução de diretórios
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / 'data' / 'raw'
DATA_PYSUS_CACHE = DATA_RAW / 'pysus_cache'
DATA_TAB_SIH = DATA_RAW / 'tab_sih'
DATA_PROCESSED = BASE_DIR / 'data' / 'processed'

# regex para arquivos de dicionários
PATTERN_CNV = re.compile(r'^\s*\d+\s+(?:(?P<prefixo>\d+)-)?(?P<descricao>.+?)\s{2,}(?P<codigo>\d+)\s*$')

# FUNÇÕES DO PIPELINE
def preparar_diretorios():
    """
    Configuração da estrutura de diretórios para
    acomodação dos dados.
    """
    # criando diretórios
    for pasta in [DATA_RAW, DATA_TAB_SIH, DATA_PROCESSED, DATA_PYSUS_CACHE]:
        pasta.mkdir(parents=True, exist_ok=True)

    # configurando diretório do cache do PySUS
    #os.environ["PYSUS_CACHEPATH"] = str(DATA_PYSUS_CACHE)

    # forçando cache
    pysus.set_cache(str(DATA_PYSUS_CACHE))

    logging.info("Diretórios e variáveis de ambiente configurados.")

def checar_cache():
    """
    Realiza checagem de número de arquivos do SIH
    e última data de modificação.
    """
    logging.info("Checando status do cache.")

    status = pysus.api.cache_utils.cache_status()

    logging.info(f"Diretório de cache: {status.path}")
    logging.info(f"Número de arquivos .parquet em disco: {status.parquet_files}")
    if status.last_modified != None:
        logging.info(f"Última modificação em: {status.last_modified}")

def sincronizar_sih_rd():
    """
    Executar download dos microdados do SIH para data/raw
    de forma idempotente.
    """
    logging.info(f"Sincronizando FileBag SIH-RD\n{ESTADO}\n{ANOS}\n{MESES}")

    # filebag com download ativado
    bag = pysus.ftp.sih(
        state=ESTADO,
        year=ANOS,
        month = MESES,
        group='RD',
        download=True
    )

    logging.info("Sincronização SIH-RD concluída.")

def processar_municipios_ibge():
    """
    Consome a API do IBGE, adapta o código de município para
    o conjunto SIH-RD e salva em Parquet.
    """
    
    caminho_saida = DATA_PROCESSED / 'ibge_municipios.parquet'

    # checando se o arquivo já foi baixado e processado
    if caminho_saida.exists():
        logging.info("Dimensão IBGE já existe. Pulando etapa...")
        return

    logging.info("Download e processamento do conjunto de dados de municípios do IBGE...")

    # dataframe cru em JSON
    df_ibge_raw = pd.read_json(URL_IBGE)

    logging.info("Transformando dados de municípios...")
    # transformando em um dataframe para fazer joins com o datasus
    df_municipios = pd.DataFrame({
        'code_ibge_7': df_ibge_raw['id'].astype(str),
        # remoção do dígito verificador, pois DATASUS usa 6 dígitos
        'code_ibge_6': df_ibge_raw['id'].astype(str).str[:6],
        'nome_municipio': df_ibge_raw['nome'],
        'uf': df_ibge_raw.apply(
            lambda row: (
                row['microrregiao']['mesorregiao']['UF']['sigla']
                if isinstance(row['microrregiao'], dict)
                else row['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
            ),
            axis=1
        )
    })

    # salvando em parquet
    logging.info("Salvando municípios em Parquet...")
    df_municipios.to_parquet(
        caminho_saida, 
        engine='pyarrow', 
        compression='snappy'
        )

    logging.info(f"Total de municípios carregados: {len(df_municipios)}")
    logging.info("Feito.")


def main():
    """
    Realiza a estruturação da arquitetura de dados, 
    o download em disco dos dados SIH-R através do pacote PySUS,
    o download e extração de códigos e nomes de municípios pela
    API do IBGE e o download e a extração do arquivo TAB_SIH
    através do protocolo FTP, bem como a extração dos dados de
    dicionário.
    """

    logging.info("INÍCIO DO SCRIPT DE INGESTÃO DE DADOS SIH-RD")

    preparar_diretorios()
    checar_cache()
    sincronizar_sih_rd()
    processar_municipios_ibge()


if __name__ == "__main__":
    main()