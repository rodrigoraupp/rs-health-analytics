#!usr/bin/env python3
"""
Pipeline de ingestão de dados SIH-RD e dados auxiliares.
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
DICIONARIOS_CNV_ALVO = {
    "sih_especialidades": "LEITOS.CNV",
    "sih_marca_uti": "MARCAUTI.CNV",
    "sih_nacionalidade": "NACION3D.CNV",
    "sih_raca_cor": "RACACOR.CNV",
}

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
PATTERN_CNV = re.compile(
    r'^\s*\d+\s+(?:(?P<prefixo>\d+)-)?(?P<descricao>.+?)\s{2,}(?P<codigo>\d+)\s*$'
    )

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
    logging.info(f"Número de arquivos Parquet em disco: {status.parquet_files}")
    if status.last_modified != None:
        logging.info(f"Última modificação em: {status.last_modified}")

def sincronizar_sih_rd():
    """
    Executa o download dos microdados do SIH para data/raw
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
    o conjunto SIH-RD e salva em Parquet.
    """
    
    caminho_saida = DATA_PROCESSED / 'ibge_municipios.parquet'

    # checando se o arquivo já foi baixado e processado
    if caminho_saida.exists():
        logging.info("Dimensão IBGE já existe. Pulando etapa...")
        return

    logging.info("Download e processamento do conjunto de dados de municípios do IBGE.")
    logging.info("Baixando...")
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

def processar_dicionarios(mapeamento: dict):
    """
    Executa o download das tabelas de dicionários através
    de protocolo FTP e processa os dados necessários
    em formato Parquet.
    """
    # dicio de arquivos pendentes
    pendentes = {
        nome_parquet: arquivo_cnv
        for nome_parquet, arquivo_cnv in mapeamento.items()
        if not (DATA_PROCESSED / f"{nome_parquet}.parquet").exists()
    }

    # se nada está pendente, encerra a função
    if not pendentes:
        logging.info("Todas as dimensões CNV já existem em data/processed. Pulando etapa...")
        return

    # realiza o download do zip se tiverem pendências
    caminho_zip = DATA_TAB_SIH / 'TAB_SIH.zip'
    if not caminho_zip.exists():
        logging.info("Baixando TAB_SIH.zip via FTP...")
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

    logging.info(f"Processando {len(pendentes)} dicionário(s) pendente(s) em pasta temporária...")

    # unzip em pasta temporária
    with tempfile.TemporaryDirectory() as pasta_temporaria:
        with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
            zip_ref.extractall(pasta_temporaria)

        # iterando sobre arquivos pendentes
        for nome_parquet, arquivo_cnv in pendentes.items():
            caminho_cnv = Path(pasta_temporaria) / 'CNV' / arquivo_cnv
            caminho_saida = DATA_PROCESSED / f"{nome_parquet}.parquet"

            if not caminho_cnv.exists():
                logging.warning(f"Arquivo {arquivo_cnv} não encontrado no zip.")
                continue

            logging.info(f"Aplicando parser em {arquivo_cnv} -> {caminho_saida.name}")
            dados = []
            # encoding: always latin-1 (ISO-8859-1), pysus
            with open(caminho_cnv, 'r', encoding='iso-8859-1') as f:
                for linha in f:
                    linha_limpa = linha.strip()
                    
                    # Ignora linhas vazias e o cabeçalho inicial 'N 41 2 L'
                    if not linha_limpa or not linha_limpa[0].isdigit():
                        continue
                        
                    match = PATTERN_CNV.match(linha)
                    if match:
                        codigo = match.group('codigo').zfill(2)
                        descricao = match.group('descricao').strip()
                        
                        dados.append({
                            'codigo': codigo,
                            'descricao': descricao
                        })

            if dados:    
                df = pd.DataFrame(dados)
                df.to_parquet(caminho_saida, index=False)
                logging.info(f"Dimensão salva: {caminho_saida.name}")
        
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
    processar_dicionarios(DICIONARIOS_CNV_ALVO)
    logging.info("Script concluído.")


if __name__ == "__main__":
    main()