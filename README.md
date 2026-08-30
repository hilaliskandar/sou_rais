# sou_rais

Notebooks, scripts e uma CLI reproduzível para consulta local de RAIS, Novo CAGED e snapshots do CNPJ a partir das tabelas públicas da Base dos Dados no BigQuery.

Versão atual do código: `0.1.0`.

## Objetivo

O projeto permite selecionar qualquer conjunto de municípios por código IBGE, escolher períodos de interesse e reproduzir localmente a aquisição, validação e inventário das bases sem depender de Google Drive, Google Colab ou caminhos pessoais.

Além da aquisição, o repositório contém uma camada analítica específica para o estudo TIC-TIM, com indicadores, tabelas, gráficos e mapas reprodutíveis a partir dos microdados adquiridos.

## Instalação

Clone o repositório, crie um ambiente Python e instale o projeto em modo editável:

```bash
pip install -e ".[dev]"
```

Para executar o notebook analítico TIC-TIM, instale também o extra de análise:

```bash
pip install -e ".[dev,analysis]"
```

Isso instala também o comando:

```bash
sou-rais
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

Copie `municipios.exemplo.csv` para `municipios.csv` e substitua pelos municípios desejados:

```csv
id_municipio,nome
3516408,Franco da Rocha
3525904,Jundiai
```

Apenas `id_municipio` é obrigatório. Os códigos devem ter 7 dígitos.

## Configuração central

Copie `config.exemplo.json` para `config.json`.

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

Valores `null` significam utilizar toda a cobertura descoberta na fonte.

`validacao_municipios` aceita:

- `strict`: ausência de município interrompe a execução;
- `warning`: registra aviso e continua;
- `off`: desativa a verificação.

O padrão público é `warning`.

## CLI

Depois de `pip install -e ".[dev]"`, o fluxo principal pode ser feito sem abrir notebooks.

Verifique a configuração e o ambiente:

```bash
sou-rais doctor
sou-rais config
```

Planeje toda a aquisição sem baixar microdados:

```bash
sou-rais plan
```

Ou por base:

```bash
sou-rais plan rais
sou-rais plan caged
sou-rais plan cnpj
```

Baixe uma base:

```bash
sou-rais download rais
sou-rais download caged
sou-rais download cnpj
```

Ou todas em sequência:

```bash
sou-rais download all
```

Também é possível usar dry-run no próprio comando de download:

```bash
sou-rais download all --dry-run
```

Valide e indexe os Parquets locais:

```bash
sou-rais validate
```

Ajuda e versão:

```bash
sou-rais --help
sou-rais --version
```

## Dry-run

O dry-run:

- descobre a cobertura temporal disponível;
- aplica os filtros de período do `config.json`;
- estima bytes processados no BigQuery quando disponível;
- informa número de consultas previstas;
- informa número de partições locais previstas;
- não baixa microdados;
- não cria Parquets de dados.

Os planos são salvos em `dados/controle`.

No CNPJ, cada snapshot gera uma única consulta BigQuery para todo o conjunto municipal. A divisão por lotes ocorre localmente.

## Uso pelos notebooks

Os notebooks permanecem disponíveis como camada interativa:

1. `00_configurar_municipios.ipynb`
2. `10_rais.ipynb`
3. `20_novo_caged.ipynb`
4. `30_cnpj.ipynb`
5. `40_validar_e_indexar.ipynb`
6. `90_tic_tim_emprego_analise_completa.ipynb`

O notebook `90_tic_tim_emprego_analise_completa.ipynb` é o ponto de entrada para a reprodução do estudo TIC-TIM. Ele parte dos Parquets obtidos pelo próprio repositório e produz a camada de análise em `dados/analise_tic_tim/`.

A lógica analítica reutilizável foi separada em `tic_tim_analysis.py`, com testes unitários próprios. Entre as operações já formalizadas estão QL, HHI, número efetivo de categorias, shift-share, remuneração real, cobertura remuneratória, intensidade aproximada dos fluxos, perfil etário, índice de envelhecimento, gaps remuneratórios e concentração de empregadores.

## Reprodução TIC-TIM

Fluxo recomendado:

```bash
cp municipios.exemplo.csv municipios.csv
cp config.exemplo.json config.json
# editar os 30 códigos IBGE e os recortes temporais
sou-rais doctor
sou-rais plan
sou-rais download all
sou-rais validate
jupyter lab 90_tic_tim_emprego_analise_completa.ipynb
```

A janela analítica principal do estudo é 2015-2025. A reprodução deve manter separados os seguintes universos:

- RAIS Vínculos: estoque e atributos dos vínculos formais ativos;
- RAIS Estabelecimentos: distribuição do estoque entre estabelecimentos declarantes;
- Novo CAGED: admissões e desligamentos;
- CNPJ: fotografias cadastrais, sem interpretação como série de emprego ou demografia empresarial líquida.

As remunerações históricas devem ser deflacionadas para reais de dezembro de 2025 pelo IPCA. Remunerações iguais a zero permanecem no estoque, mas são excluídas de médias, medianas, percentis, massa salarial e gaps remuneratórios. O QL usa como referência o conjunto dos municípios configurados para a análise; no estudo TIC-TIM, o universo canônico é de 30 municípios.

A documentação metodológica detalhada está em `docs/TIC_TIM_REPRODUCAO.md`.

## Uso direto dos scripts

Também é possível executar:

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
├── analise_tic_tim/
│   ├── tabelas/
│   ├── figuras/
│   ├── mapas/
│   └── controle/
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
- municípios ausentes, quando aplicável;
- SHA-256.

O validador lê os metadados Parquet sem carregar os microdados completos e detecta arquivos vazios, nomes fora do padrão e lotes incompatíveis com a configuração atual.

A camada TIC-TIM gera ainda uma auditoria de completude e um manifesto SHA-256 dos produtos analíticos.

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

QL mede especialização relativa, não competitividade. HHI mede concentração, não vulnerabilidade. Shift-share é decomposição contábil da variação do emprego e não estima causalidade ou produtividade. A intensidade dos fluxos é uma medida aproximada de movimentação e não uma taxa longitudinal de rotatividade individual.

## Testes e empacotamento

Execute:

```bash
pytest -q
python -m build
python -m twine check dist/*
```

O GitHub Actions executa testes unitários, gera `sdist` e wheel e testa a instalação limpa do wheel em ambiente virtual separado.

## Changelog e licença

As mudanças por versão estão documentadas em `CHANGELOG.md`.

O código é distribuído sob a licença MIT. Consulte `LICENSE`.
