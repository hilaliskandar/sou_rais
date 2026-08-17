# sou_rais

Notebooks reproduzíveis para consulta local de RAIS, Novo CAGED e snapshots do CNPJ a partir das tabelas públicas da Base dos Dados no BigQuery.

## Princípios

- nenhuma dependência de Google Drive ou Google Colab;
- nenhum código IBGE ou projeto de cobrança é fixado no código;
- seleção de municípios por arquivo CSV ou lista no notebook;
- códigos IBGE municipais de 7 dígitos;
- execução incremental: partições locais existentes são reaproveitadas;
- saída em Parquet com compressão Snappy;
- CNPJ tratado explicitamente como snapshots administrativos;
- Novo CAGED mantido separado de regimes históricos anteriores a 2020.

## Preparação

Crie um ambiente Python e instale:

```bash
pip install -r requirements.txt
```

É necessário ter credenciais Google Cloud disponíveis para o BigQuery, por exemplo com:

```bash
gcloud auth application-default login
```

Defina o projeto usado para cobrança das consultas:

```bash
export BIGQUERY_PROJECT=seu-projeto-gcp
```

No Windows PowerShell:

```powershell
$env:BIGQUERY_PROJECT="seu-projeto-gcp"
```

## Municípios

Copie `municipios.exemplo.csv` para `municipios.csv` e substitua os códigos pelos municípios desejados:

```csv
id_municipio,nome
3516408,Franco da Rocha
3525904,Jundiai
```

Apenas `id_municipio` é obrigatório. Alternativamente, preencha `MUNICIPIOS_INLINE` diretamente em cada notebook.

## Ordem sugerida

1. `00_configurar_municipios.ipynb`
2. `10_rais.ipynb`
3. `20_novo_caged.ipynb`
4. `30_cnpj.ipynb`
5. `40_validar_e_indexar.ipynb`

Os arquivos são gravados em `dados/processado`, que está fora do Git por padrão.

## Fontes

As consultas usam tabelas públicas da Base dos Dados:

- `basedosdados.br_me_rais.microdados_vinculos`
- `basedosdados.br_me_rais.microdados_estabelecimentos`
- `basedosdados.br_me_caged.microdados_movimentacao`
- `basedosdados.br_me_cnpj.estabelecimentos`
- `basedosdados.br_me_cnpj.empresas`
- `basedosdados.br_me_cnpj.simples`

Consulte também a documentação oficial do Ministério do Trabalho e Emprego e da Receita Federal antes de interpretar as séries.

## Observações metodológicas

RAIS é uma base anual de estoque/declaração. Novo CAGED é uma base de movimentações mensais e não deve ser emendada automaticamente ao regime histórico anterior a 2020. Os arquivos CNPJ representam snapshots administrativos em datas específicas e não equivalem a uma série anual de emprego ou de empresas ativas sem tratamento metodológico adicional.
