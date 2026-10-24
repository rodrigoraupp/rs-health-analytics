# ADR 0001: Estratégia de Ingestão e Processamento de Dados e Metadados do SIH/SUS

**Data:** Outubro 2026

## 1. Contexto

*Architecture Decision Records* (ARDs) são documentos que retratam as decisões arquiteturais de um projeto em Ciência de Dados. Essa documentação exprime o que foi realizado e sua justificativa. Para a realização desse projeto, optou-se por documentar de maneira simples porque estou inicialmente executando de maneira individual.

O pipeline de dados de internações hospitalares resumidos (SIH-RD) começa pela ingestão, que apresenta vários desafios de manipulação.

* Os microdados principais possuem milhões de registros.
* Os arquivos auxiliares de domínio (como tabelas de especialidades) são distribuídos em pacotes legados zipados (`TAB_SIH.zip`).
* Pacientes são frequentemente transferidos ou internados fora do seu estado de residência, o que gera códigos municipais não mapeados se limitarmos a base geográfica apenas ao RS.

## 2. Decisão 
Adoto uma arquitetura de ingestão desacoplada baseada no princípio de separação de conceitos e imutabilidade dos dados brutos.

1. **Gerenciamento de Ambiente e Execução (Python/Conda)**: Optou-se pelo uso do Conda para garantir o isolamento estrito das dependências (como PySUS e DuckDB) e a reprodutibilidade multiplataforma do projeto. O acionamento do pipeline de dados foi encapsulado em um único ponto de entrada modular (o script src/ingestao.py), separando completamente a orquestração da infraestrutura em relação à lógica de análise futura.
2. **Idempotência com PySUS:** Utilizo a biblioteca PySUS para sincronização dos microdados principais via API de FileBag. Os arquivos são armazenados em disco no formato colunar Parquet, delegando à biblioteca o gerenciamento do cache local para evitar re-downloads desnecessários.
3. **Escopo Geográfico Nacional:** Consumi a API do IBGE para gerar uma tabela de dimensão contendo todos os municípios do Brasil, e não apenas os do RS, para garantir o mapeamento de pacientes interestaduais.
4. **Parsing Local de Dicionários Legados:** Devido à instabilidade estrutural do `TAB_SIH.zip`, isolei a extração da tabela de especialidades utilizando a biblioteca padrão do Python (`zipfile`). Implementei um parser utilizando Expressões Regulares (`regex`) para ler arquivos nativos (como `LEITOS.CNV`) e convertê-lo localmente em Parquet.
5. **Isolamento da Integração:** Os dados brutos (`data/raw`) não sofrem alteração in-place (como substituição de códigos por textos). Toda tradução de colunas de alta cardinalidade é feita dinamicamente via JOINs utilizando o DuckDB durante a fase de análise.

## 3. Consequências

### Positivas
* **Resiliência:** Se o governo alterar a estrutura dos arquivos `.dbf` no futuro, nosso script continua funcional pois lê a definição fonte diretamente do `.CNV`.
* **Performance e Economia de Rede:** O script `ingestao.py` pode ser executado múltiplas vezes sem penalidade de tempo ou banda, garantindo que o pipeline seja executável em instâncias de CI/CD ou máquinas limitadas.
* **Integridade (Single Source of Truth):** Mantive os microdados originais intactos. Qualquer erro de mapeamento pode ser corrigido alterando apenas a query SQL do DuckDB, sem necessidade de reprocessar milhões de linhas.

### Negativas / Trade-offs
* **Complexidade de Manutenção:** A extração de arquivos como `LEITOS.CNV` via Regex adiciona uma lógica customizada ao repositório que precisará ser mantida caso o SUS altere radicalmente a formatação de seus arquivos de texto legados.
* **Sobrecarga Inicial de Código:** Exige a manutenção de scripts separados para ingestão e integração, em vez de um único notebook exploratório monolítico.