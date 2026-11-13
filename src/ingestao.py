#!usr/bin/env python3
"""
Pipeline de ingestão ELT de dados SIH-RD e dados auxiliares.
Script responsável por executar o download dos microdados,
a lista de municípios do IBGE e extrair os dicionários de
especialidades do DATASUS.
"""

# bibliotecas
import logging
import os
from pathlib import Path
import re
from ftplib import FTP
import zipfile
import tempfile
import json
import requests

# resolução de diretórios
from config import (
    DATA_BRONZE,
    DATA_PYSUS_CACHE,
    DATA_TAB_SIH,
    DATA_IBGE,
    DATA_SILVER,
    DATA_SILVER_DIM,
    DATA_SILVER_FATO,
    DATA_GOLD,
)

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

# dict com dicionários para traduzir colunas do SIH-RD
# "nome_arquivo_parquet_final" : "NOME_ARQUIVO_DENTRO_DO_ZIP.CNV"
# estrutura em star schema
CNV_FILES = [
    "LEITOS.CNV",
    "MARCAUTI.CNV",
    "NACION3D.CNV",
    "RACACOR.CNV",
]

# urls para download
URL_TAB_SIH = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Auxiliar/TAB_SIH.zip"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

# # regex para arquivos de dicionários
# PATTERN_CNV = re.compile(
#     r'^\s*\d+\s+(?:(?P<prefixo>\d+)-)?(?P<descricao>.+?)\s{2,}(?P<codigo>\d+)\s*$'
#     )

# FUNÇÕES DO PIPELINE
def preparar_diretorios():
    """
    Configuração da estrutura do Data Lakehouse para
    acomodação dos dados em todas as camadas na Arquitetura
    Medalhão (bronze, silver, gold).
    """
    # diretórios
    diretorios = [
        DATA_BRONZE,
        DATA_PYSUS_CACHE,
        DATA_TAB_SIH,
        DATA_IBGE, 
        DATA_SILVER,
        DATA_SILVER_DIM,
        DATA_SILVER_FATO,
        DATA_GOLD,
    ]
    # criando diretórios
    for diretorio in diretorios:
        diretorio.mkdir(parents=True, exist_ok=True)

    # configurando diretório do cache do PySUS
    #os.environ["PYSUS_CACHEPATH"] = str(DATA_PYSUS_CACHE)

    # forçando cache
    pysus.set_cache(str(DATA_PYSUS_CACHE))

    logging.info("Diretórios da Arquitetura Medalhão e cache configurados com sucesso.")

def checar_cache():
    """
    Realiza checagem de número de arquivos do SIH
    e última data de modificação.
    """
    logging.info("Checando status do cache.")

    status = pysus.api.cache_utils.cache_status()

    logging.info(f"Diretório de cache: {status.path}")
    logging.info(f"Número de arquivos Parquet em disco: {status.parquet_files}")
    if status.last_modified != None:
        logging.info(f"Última modificação em: {status.last_modified}")

def sincronizar_sih_rd():
    """
    Executa o download dos microdados do SIH para data/bronze
    de forma idempotente.
    """
    logging.info(f"Sincronizando FileBag SIH-RD\nEstado: {ESTADO}\nAnos: {ANOS}\nMeses: {MESES}")

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
    o conjunto SIH-RD e salva em Parquet (silver).
    """

    # caminho dos dados tratados (silver)
    caminho_saida = DATA_SILVER_DIM / 'dim_municipio.parquet'

    # caminho dos dados brutos (bronze)
    caminho_bronze = DATA_IBGE / 'raw_municipios.json'

    # checando se o arquivo já foi baixado e processado
    if caminho_saida.exists():
        logging.info("Dimensão IBGE (Silver) já existe. Pulando etapa...")
        return

    if not caminho_bronze.exists():
        logging.info("Download do arquivo JSON (bronze) dos municípios brasileiros através da API do IBGE.")
        logging.info("Baixando...")
        # dataframe cru em JSON
        resposta = requests.get(URL_IBGE)
        resposta.raise_for_status()

        # salvar o arquivo que a API retornou
        with open(caminho_bronze, 'w', encoding='utf-8') as f:
            json.dump(resposta.json(), f, ensure_ascii=False)

    # abrindo arquivo JSON baixado
    with open(caminho_bronze, 'r', encoding='utf-8') as f:
        dados_json = json.load(f)

    # achatando árvore com JSON normalize
    df_ibge_raw = pd.json_normalize(dados_json)

    logging.info("Transformando dados de municípios...")
    # transformando em um dataframe para fazer joins com o datasus
    df_municipios = pd.DataFrame({
        'code_ibge_7': df_ibge_raw['id'].astype(str),
        'code_ibge_6': df_ibge_raw['id'].astype(str).str[:6],
        'nome_municipio': df_ibge_raw['nome'].astype(str),
        'uf': df_ibge_raw['microrregiao.mesorregiao.UF.sigla'].astype('category')
    })

    # salvando em parquet
    logging.info("Salvando municípios em Parquet (Silver)...")
    df_municipios.to_parquet(
        caminho_saida, 
        engine='pyarrow', 
        compression='zstd', # compressão otimizada para category
        index=False
    )

    logging.info(f"Total de municípios carregados: {len(df_municipios)}")
    logging.info("Feito.")

def processar_dicionarios(lista_cnv: list):
    """
    Executa o download das tabelas de dicionários através
    de protocolo FTP e extrai seletivamente os dados necessários
    em formato original na camada Bronze.
    """
    # como o zip cria a subpasta, vamos validar a existência nela
    pendentes = [
        arquivo_cnv for arquivo_cnv in lista_cnv
        if not (DATA_TAB_SIH / 'CNV' / arquivo_cnv).exists()
    ]

    # se nada está pendente, encerra a função
    if not pendentes:
        logging.info("Todas as dimensões brutas CNV já existem em data/bronze/tab_sih/CNV. Pulando etapa...")
        return

    # realiza o download do zip se tiverem pendências e o zip não existir
    caminho_zip = DATA_TAB_SIH / 'TAB_SIH.zip'
    if not caminho_zip.exists():
        logging.info("Baixando TAB_SIH.zip (bronze) via FTP...")
        # acessando diretório do governo
        endereco_ftp = 'ftp.datasus.gov.br'
        ftp = FTP(endereco_ftp, timeout=30.0)
        logging.info(f"Logando em {endereco_ftp}")
        logging.info(f"{ftp.login()}")

        # mensagem de boas-vindas
        logging.info("Mensagem de boas-vindas")
        logging.info(f"{ftp.getwelcome()}\n")

        # identificando caminho
        caminho_exato = "/dissemin/publicos/SIHSUS/200801_/Auxiliar/"
        logging.info(f"Arquivos em {caminho_exato}\n")

        # entrando no diretório exato
        ftp.cwd(caminho_exato)

        # loop para listagem de arquivos
        ftp.retrlines('LIST')

        # BAIXANDO ARQUIVO TAB_SIH.zip
        logging.info("Transferindo arquivo para disco local...")
        with open(caminho_zip, 'wb') as arquivo_dicio:
            logging.info(f"{ftp.retrbinary('RETR TAB_SIH.zip', arquivo_dicio.write)}")

        logging.info("Fechando conexão...")
        logging.info(f"{ftp.quit()}")

    # unzipping
    logging.info(f"Extraindo {len(pendentes)} dicionário(s) pendente(s) diretamente para a camada Bronze...")

    with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
        arquivos_no_zip = zip_ref.namelist()
        
        # Filtra na lista interna do zip os caminhos exatos dos arquivos que estão na nossa lista de pendentes
        # Ex: procura por "CNV/SEXO.CNV" dentro do .namelist() baseado em "SEXO.CNV"
        caminhos_para_extrair = [
            arq_interno for arq_interno in arquivos_no_zip
            # Pega o nome do arquivo após a última barra e compara (case-insensitive)
            if arq_interno.split('/')[-1].upper() in [p.upper() for p in pendentes]
        ]
        
        if not caminhos_para_extrair:
            logging.warning("Nenhum arquivo pendente correspondente foi encontrado dentro do ZIP.")
            return

        for arquivo_interno in caminhos_para_extrair:
            # Extrai diretamente em DATA_TAB_SIH. 
            # Como o arquivo interno é do tipo 'CNV/nome.CNV', o Python cria a pasta 'CNV' dentro de DATA_TAB_SIH.
            zip_ref.extract(arquivo_interno, path=DATA_TAB_SIH)
            logging.info(f"Extraído (Bronze): {arquivo_interno}")
            
    logging.info("Processamento da Camada Bronze (Dicionários) concluído.")

        # --- CÓDIGO ANTIGO (ETL) COMENTADO PARA REFERÊNCIA ---
        #     zip_ref.extractall(pasta_temporaria)

        # # iterando sobre arquivos pendentes
        # for nome_parquet, arquivo_cnv in pendentes.items():
        #     caminho_cnv = Path(pasta_temporaria) / 'CNV' / arquivo_cnv
        #     caminho_saida = DATA_SILVER_DIM / f"{nome_parquet}.parquet"

        #     if not caminho_cnv.exists():
        #         logging.warning(f"Arquivo {arquivo_cnv} não encontrado no zip.")
        #         continue

        #     logging.info(f"Aplicando parser em {arquivo_cnv} -> {caminho_saida.name}")
        #     dados = []
        #     # encoding: always latin-1 (ISO-8859-1), pysus
        #     with open(caminho_cnv, 'r', encoding='iso-8859-1') as f:
        #         for linha in f:
        #             linha_limpa = linha.strip()
                    
        #             # Ignora linhas vazias e o cabeçalho inicial 'N 41 2 L'
        #             if not linha_limpa or not linha_limpa[0].isdigit():
        #                 continue
                        
        #             match = PATTERN_CNV.match(linha)
        #             if match:
        #                 codigo = match.group('codigo').zfill(2)
        #                 descricao = match.group('descricao').strip()
                        
        #                 dados.append({
        #                     'codigo': codigo,
        #                     'descricao': descricao
        #                 })

        #     if dados:    
        #         df = pd.DataFrame(dados)
        #         df.to_parquet(caminho_saida, index=False)
        #         logging.info(f"Dimensão salva: {caminho_saida.name}")

def main():
    """
    Pipeline ELT. Realiza a estruturação da arquitetura de dados, 
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
    processar_dicionarios(CNV_FILES)
    logging.info("Script concluído.")


if __name__ == "__main__":
    main()