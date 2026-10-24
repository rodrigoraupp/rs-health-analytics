#!/bin/bash

# flag para interromper script se qualquer comando falhar
set -e

echo "Iniciando a orquestração do pipeline SIH..."

# carrega funções conda para dentro do script invisível
eval "$(conda shell.bash hook)"

echo "Ativando ambiente virtual 'projeto_sih'..."
conda activate projeto_sih

# injetando variável ambiente dinamicamente
export PYSUS_CACHEPATH="$(pwd)/data/raw/pysus_cache"
echo "Variável PYSUS_CACHEPATH injetada: $PYSUS_CACHEPATH"

echo "Rodando pipeline de ingestão e tratamento..."
python src/ingestao.py

echo "Pipeline orquestrado e finalizado com sucesso!"