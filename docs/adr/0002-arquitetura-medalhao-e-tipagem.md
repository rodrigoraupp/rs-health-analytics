# ADR 0002: Adoção de Arquitetura Medalhão (ELT), Centralização de Caminhos e Tipagem na Camada Silver

**Data:** Novembro 2026

## 1. Contexto
Com a evolução do pipeline de dados hospitalares (SIH-RD/DATASUS e IBGE), surgiram dois gargalos principais: a repetição de caminhos de arquivos (*hardcoded*) entre scripts e notebooks, e a baixa eficiência nas consultas devido ao armazenamento de todos os dados brutos como texto (`VARCHAR`), exigindo conversões constantes em tempo de execução. Era necessário separar as etapas de extração e transformação e padronizar o armazenamento.

## 2. Decisão
1. **Estrutura Medalhão:** Organizar o diretório `data/` nas camadas `bronze` (dados brutos imutáveis), `silver` (dados higienizados e tipados, divididos em `fato/` e `dim/`) e `gold` (tabelas agregadas para análise).
2. **Centralização de Caminhos:** Criar o módulo `src/config.py` como fonte única de verdade para os diretórios do projeto, sendo importado tanto pelos scripts quanto pelos notebooks.
3. **Ingestão Focada na Camada Bronze:** Restringir o `src/ingestao.py` à criação da árvore de diretórios e ao download dos dados originais (microdados SIH-RD em Parquet, payload da API do IBGE em JSON e o pacote compactado `TAB_SIH.zip`). Como exceção pragmática, o próprio script já trata e salva a dimensão de municípios em `silver/dim`.
4. **Qualidade, Parsing e Tipagem na Camada Silver:** Concentrar no notebook `01_data_quality.ipynb` a auditoria de qualidade, a seleção das colunas de interesse e a conversão estrita de tipos (datas nativas e tipos numéricos/textuais alinhados), além do *parsing* dos dicionários `.CNV` brutos para Parquet tipado, garantindo compatibilidade direta nos *JOINs* via DuckDB.

## 3. Consequências

### Positivas
* Separação clara de responsabilidades (modelo ELT); possibilidade de reprocessar toda a camada Silver sem depender de novos downloads na rede; consultas mais rápidas e com menor consumo de memória RAM no DuckDB pela eliminação de `CAST` dinâmico; manutenção centralizada de diretórios.

### Negativas / Trade-offs
* Maior número de artefatos intermediários no projeto e necessidade de garantir manualmente que a tipagem das chaves primárias extraídas dos arquivos `.CNV` corresponda exatamente às chaves estrangeiras da tabela fato.