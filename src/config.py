from pathlib import Path

# resolução de diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent

# camada Bronze
DATA_BRONZE = BASE_DIR / 'data' / 'bronze'
DATA_PYSUS_CACHE = DATA_BRONZE / 'pysus_cache'
DATA_BRONZE_SIH = DATA_PYSUS_CACHE / 'downloads' / 'ducklake' / 'sih'
DATA_TAB_SIH = DATA_BRONZE / 'tab_sih'
DATA_CNV = DATA_TAB_SIH / 'cnv'
DATA_IBGE = DATA_BRONZE / 'ibge'

# camada Silver
DATA_SILVER = BASE_DIR / 'data' / 'silver'
DATA_SILVER_DIM = DATA_SILVER / 'dim' 
DATA_SILVER_FATO = DATA_SILVER / 'fato'

# camada Gold
DATA_GOLD = BASE_DIR / 'data' / 'gold'