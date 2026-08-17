# sou_rais

Notebooks e scripts reproduzíveis para consulta local de RAIS, Novo CAGED e snapshots do CNPJ a partir das tabelas públicas da Base dos Dados no BigQuery.

## Objetivo

O projeto foi estruturado para permitir que qualquer usuário selecione um conjunto arbitrário de municípios por código IBGE, escolha períodos de interesse e reproduza localmente a aquisição e o inventário das bases sem depender de Google Drive, Google Colab ou caminhos pessoais.

## Princípios

- nenhuma dependência de Google Drive ou Google Colab;
- nenhum município ou projeto de cobrança fixado no código;
- seleção de municípios por `municipios.csv` ou lista inline no notebook de configuração;
- configuração central opcional em `config.json`;
- códigos IBGE municipais de 7 dígitos;
- seleção opcional de período para RAIS, Novo CAGED e CNPJ;
- execução incremental com reaproveitamento de Parquets existentes;
- modo `--dry-run` para descobrir cobertura e estimar processamento sem baixar microdados;
- estimativa de bytes processados antes das consultas quando disponível;
- validação municipal configurável em `strict`, `warning` ou `off`;
- gravação atômica em Parquet com compressão Snappy;
- manifesto de execução com número de linhas, municípios ausentes e SHA-256;
- CNPJ tratado explicitamente como snapshots administrativos;
- Novo CAGED mantido separado dos regimes históricos anteriores a 2020.

## Preparação

Crie um ambiente Python e instale:

```bash
pip install -r requirements.txt
```

É necessário ter credenciais Google Cloud disponíveis para o BigQuery, por exemplo:

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

Apenas `id_municipio` é obrigatório. Os códigos devem ter 7 dígitos.

Também é possível preencher `MUNICIPIOS_INLINE` em `00_configurar_municipios.ipynb` quando não existir `municipios.csv`.

## Configuração central

Copie:

```bash
cp config.exemplo.json config.json
```

No Windows, basta duplicar o arquivo manualmente.

Campos disponíveis:

```json
{
  "arquivo_municipios": "municipios.csv",
  "lote_tamanho": 5,
  "ano_inicial": null,
  "ano_final": null,
  "competencia_inicial": null,
  "competencia_final": null,
  "snapshot_inicial": null,
  "snapshot_final": null,
  "estimar_custo": true,
  "sobrescrever": false,
  "validacao_municipios": "warning"
}
```

Exemplos:

- RAIS de 2010 a 2025: `ano_inicial=2010`, `ano_final=2025`;
- Novo CAGED de `2022-01` a `2025-12`;
- CNPJ entre dois snapshots, usando datas no formato `AAAA-MM-DD`.

Valores `null` significam utilizar toda a cobertura descoberta na fonte.

### Validação municipal

`validacao_municipios` controla o comportamento quando um código configurado não aparece em determinada partição:

- `strict`: interrompe a execução;
- `warning`: registra um aviso e continua;
- `off`: não testa presença municipal.

O padrão público é `warning`, pois ausência de registros pode ser legítima em períodos antigos, municípios pequenos ou determinados recortes administrativos. Para auditorias de integridade, use `strict`.

Os municípios ausentes são registrados em `manifesto_execucoes.csv` quando a execução continua.

## Dry-run

Antes de baixar microdados, é recomendável executar:

```bash
python scripts/baixar_rais.py --dry-run
python scripts/baixar_novo_caged.py --dry-run
python scripts/baixar_cnpj.py --dry-run
```

O `dry-run`:

- consulta apenas a cobertura temporal necessária para montar o plano;
- faz dry-run das consultas BigQuery para estimar bytes processados quando o serviço retorna essa informação;
- informa número de consultas BigQuery previstas;
- informa número de partições locais previstas;
- não baixa os microdados;
- não cria Parquets de dados.

Os planos são salvos em:

```text
dados/controle/plano_rais.csv
dados/controle/plano_novo_caged.csv
dados/controle/plano_cnpj.csv
```

No CNPJ, a quantidade de consultas BigQuery é igual ao número de snapshots selecionados, independentemente do número de lotes locais: cada snapshot é consultado uma única vez para todo o conjunto municipal e depois dividido localmente.

## Uso pelos notebooks

Ordem sugerida:

1. `00_configurar_municipios.ipynb`
2. `10_rais.ipynb`
3. `20_novo_caged.ipynb`
4. `30_cnpj.ipynb`
5. `40_validar_e_indexar.ipynb`

Os notebooks são deliberadamente finos: a lógica principal fica em `sou_rais.py` e em `scripts/`, facilitando manutenção, testes e uso fora do Jupyter.

## Uso pela linha de comando

As rotinas podem ser executadas sem Jupyter:

```bash
python scripts/baixar_rais.py
python scripts/baixar_novo_caged.py
python scripts/baixar_cnpj.py
python scripts/validar_e_indexar.py
```

## Estrutura de saída

```text
dados/
├── processado/
│   ├── rais/
│   │   ├── vinculos/
│   │   └── estabelecimentos/
│   ├── caged/
│   └── cnpj/
└── controle/
    ├── manifesto_execucoes.csv
    ├── indice_particoes.csv
    ├── indice_particoes_fora_padrao.csv
    ├── plano_rais.csv
    ├── plano_novo_caged.csv
    └── plano_cnpj.csv
```

A pasta `dados/` permanece fora do Git por padrão.

## Controle e integridade

Cada partição criada registra no manifesto:

- base;
- tipo;
- lote;
- período ou snapshot;
- caminho relativo;
- número de linhas;
- municípios configurados que não apareceram naquela partição;
- SHA-256.

O validador lê os metadados Parquet sem carregar os microdados completos e detecta arquivos vazios, nomes fora do padrão e lotes incompatíveis com a configuração atual.

## Fontes

As consultas usam tabelas públicas da Base dos Dados:

- `basedosdados.br_me_rais.microdados_vinculos`
- `basedosdados.br_me_rais.microdados_estabelecimentos`
- `basedosdados.br_me_caged.microdados_movimentacao`
- `basedosdados.br_me_cnpj.estabelecimentos`
- `basedosdados.br_me_cnpj.empresas`
- `basedosdados.br_me_cnpj.simples`

Consulte a documentação oficial do Ministério do Trabalho e Emprego, da Receita Federal e da Base dos Dados antes de interpretar as séries.

## Observações metodológicas

RAIS é uma base anual de estoque e declaração. Novo CAGED é uma base de movimentações mensais e não deve ser emendado automaticamente ao regime histórico anterior a 2020. Os arquivos CNPJ representam snapshots administrativos em datas específicas e não equivalem a uma série anual de emprego ou de empresas ativas sem tratamento metodológico adicional.

## Testes

Execute:

```bash
pytest -q
```

O repositório também possui workflow de GitHub Actions para executar os testes básicos automaticamente em pushes e pull requests.
