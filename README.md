# sou_rais

Notebooks, scripts e uma CLI reproduzível para consulta local de RAIS, Novo CAGED e snapshots do CNPJ a partir das tabelas públicas da Base dos Dados no BigQuery.

Versão atual do código: `0.2.0`.

## Objetivo

O projeto permite selecionar qualquer conjunto de municípios por código IBGE, escolher períodos de interesse e reproduzir localmente a aquisição, validação e inventário das bases sem depender de Google Drive, Google Colab ou caminhos pessoais.

Além da aquisição, o repositório contém uma camada analítica específica para o estudo TIC-TIM, com indicadores, tabelas, gráficos e mapas reprodutíveis a partir dos microdados adquiridos.

## Instalação

Clone o repositório, crie um ambiente Python e instale o projeto em modo editável:

```bash
pip install -e ".[dev]"
```

Para executar a camada analítica TIC-TIM:

```bash
pip install -e ".[dev,analysis]"
```

Para mapas municipais com GeoPandas:

```bash
pip install -e ".[dev,geo]"
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

## CLI de aquisição

Depois de `pip install -e ".[dev]"`, o fluxo principal pode ser feito sem abrir notebooks.

```bash
sou-rais doctor
sou-rais config
sou-rais plan
sou-rais download all
sou-rais validate
```

Também é possível usar dry-run:

```bash
sou-rais download all --dry-run
```

O dry-run descobre cobertura temporal, aplica filtros, estima bytes, informa consultas/partições previstas e não baixa microdados.

## Notebooks

1. `00_configurar_municipios.ipynb`
2. `10_rais.ipynb`
3. `20_novo_caged.ipynb`
4. `30_cnpj.ipynb`
5. `40_validar_e_indexar.ipynb`
6. `90_tic_tim_emprego_analise_completa.ipynb`

O notebook `90_tic_tim_emprego_analise_completa.ipynb` é o ponto de entrada interativo para a reprodução do estudo TIC-TIM.

A lógica metodológica reutilizável está em `tic_tim_analysis.py`. Entre as operações formalizadas estão estoque, participação regional, QL, HHI, número efetivo, shift-share, remuneração real, cobertura remuneratória, intensidade aproximada dos fluxos, perfil etário, índice de envelhecimento, gaps remuneratórios, referência empírica de escolaridade por CBO, concentração de empregadores e auditoria de equivalência.

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
python scripts/analisar_tic_tim.py
jupyter lab 90_tic_tim_emprego_analise_completa.ipynb
```

A janela analítica principal é 2015-2025. Devem permanecer separados:

- RAIS Vínculos: estoque e atributos dos vínculos formais ativos;
- RAIS Estabelecimentos: distribuição do estoque entre estabelecimentos declarantes;
- Novo CAGED: admissões e desligamentos;
- CNPJ: fotografias cadastrais, sem interpretação como série de emprego ou demografia empresarial líquida.

As remunerações históricas devem ser deflacionadas para reais de dezembro de 2025 pelo IPCA. Remunerações iguais a zero permanecem no estoque, mas são excluídas de médias, medianas, percentis, massa salarial e gaps remuneratórios. O QL usa como referência o conjunto dos municípios configurados; no estudo TIC-TIM, o universo canônico é de 30 municípios.

A documentação metodológica detalhada está em `docs/TIC_TIM_REPRODUCAO.md`.

## Gates de equivalência

Quando houver uma tabela canônica publicada em CSV, o gate genérico pode ser executado por:

```bash
python scripts/validar_equivalencia_tic_tim.py \
  dados/analise_tic_tim/tabelas/02_trajetoria_2015_2025.csv \
  referencias/trajetoria_publicada.csv \
  --chaves id_municipio \
  --colunas estoque_inicial estoque_final variacao_abs crescimento_pct
```

O comando termina com erro quando qualquer comparação ultrapassa as tolerâncias informadas. Isso permite usar os entregáveis publicados como testes de regressão do pipeline.

## Uso direto dos scripts

```bash
python scripts/baixar_rais.py
python scripts/baixar_novo_caged.py
python scripts/baixar_cnpj.py
python scripts/validar_e_indexar.py
python scripts/analisar_tic_tim.py
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

Cada partição criada registra base, tipo, lote, período/snapshot, caminho relativo, linhas, municípios ausentes e SHA-256. A camada TIC-TIM gera auditoria de completude e manifesto SHA-256 dos produtos analíticos.

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

RAIS é estoque anual de vínculos declarados. Novo CAGED é movimentação mensal e não deve ser emendado automaticamente ao regime histórico anterior a 2020. CNPJ é fotografia cadastral e não equivale a série anual de emprego.

QL mede especialização relativa, não competitividade. HHI mede concentração, não vulnerabilidade. Shift-share é decomposição contábil e não estima causalidade ou produtividade. A intensidade dos fluxos é aproximação da movimentação relativa, não taxa longitudinal de rotatividade individual.

## Testes e empacotamento

```bash
pytest -q
python -m build
python -m twine check dist/*
```

O GitHub Actions executa testes unitários, gera `sdist` e wheel e testa a instalação limpa do wheel.

## Changelog e licença

As mudanças por versão estão documentadas em `CHANGELOG.md`.

O código é distribuído sob a licença MIT. Consulte `LICENSE`.
