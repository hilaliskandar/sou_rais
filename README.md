# sou_rais

Repositório reprodutível para aquisição, validação, processamento e análise de dados de emprego formal e estrutura empresarial no Brasil, com uma implementação completa voltada ao estudo **TIC–TIM — Emprego e Estrutura Econômica**.

Versão atual do código: `0.2.0`.

## Visão geral

O projeto organiza em uma única cadeia computacional a consulta de microdados públicos, a construção de bases locais versionáveis, o cálculo de indicadores regionais e municipais, a geração de tabelas, gráficos e mapas e a comparação dos resultados calculados com referências canônicas publicadas.

A arquitetura foi desenhada para reduzir dependências de ambientes pessoais, Google Drive, Google Colab e caminhos absolutos. O objetivo é permitir que outra pessoa, dispondo das credenciais necessárias para consulta ao BigQuery, possa reconstruir o estudo a partir do código, das configurações e das fontes públicas documentadas neste repositório.

O repositório tem dois usos complementares:

1. **uso geral** — aquisição reprodutível de RAIS, Novo CAGED e fotografias cadastrais do CNPJ para qualquer conjunto de municípios brasileiros;
2. **uso TIC–TIM** — reprodução da linha de base de Emprego e Estrutura Econômica dos 30 municípios definidos no estudo, com janela principal 2015–2025, indicadores, gates de equivalência e produtos editoriais.

A camada TIC–TIM reproduz o desenho metodológico público consolidado do estudo. O período 2015–2025 é tratado como **linha de base anterior à operação do TIC–TIM**. Os resultados descrevem estruturas e tendências preexistentes; não constituem estimativa causal de impactos do empreendimento.

---

## 1. Princípios metodológicos

A reprodução segue cinco princípios.

**Unidades estatísticas não são intercambiáveis.** RAIS Vínculos, RAIS Estabelecimentos, Novo CAGED e CNPJ são fontes diferentes, com unidades, temporalidades e significados próprios. Estoque, fluxo, empregador e cadastro não são concatenados como se formassem uma única série.

**O município é a unidade territorial básica.** Os indicadores são construídos por município e posteriormente sintetizados regionalmente. O conjunto dos 30 municípios funciona como espaço de referência interno para medidas relativas, como participação regional, Quociente Locacional e componentes de decomposição.

**Indicadores são multidimensionais.** Crescimento, especialização, concentração, remuneração, escolaridade, estabilidade, envelhecimento, desigualdades e estrutura empresarial são examinados em dimensões distintas. O estudo não produz um escore único de “desempenho”.

**Toda transformação deve ser auditável.** Partições, tabelas derivadas e produtos analíticos registram cobertura, caminhos, número de linhas e, quando aplicável, SHA-256. Valores publicados funcionam como referências congeladas de regressão e não podem ser alterados para acomodar uma nova execução.

**Descontinuidades administrativas são tratadas explicitamente.** A ampliação do eSocial na formação da RAIS, sobretudo na passagem 2022–2023, exige cautela. Mudança de cobertura ou forma de declaração não é interpretada automaticamente como transformação econômica real.

---

## 2. Fontes de dados

### 2.1 RAIS — Relação Anual de Informações Sociais

A RAIS é a fonte principal para o estoque e a estrutura do emprego formal. O estudo utiliza dois universos separados:

- **RAIS Vínculos**: vínculos formais ativos em 31 de dezembro e seus atributos;
- **RAIS Estabelecimentos**: estabelecimentos declarantes e distribuição do estoque entre empregadores.

Na RAIS Vínculos são utilizados, conforme disponibilidade e consistência de cada ano, município do estabelecimento, CNAE, CBO, remuneração, escolaridade, idade, sexo, raça/cor, duração do vínculo, jornada e características contratuais.

A unidade elementar é o **vínculo**, não necessariamente uma pessoa. Um indivíduo pode manter mais de um vínculo. Por isso, resultados derivados diretamente da RAIS são denominados “vínculos formais”, salvo quando outra unidade estiver explicitamente demonstrada.

A série pode ser preservada desde 1985 para fins documentais, mas a janela analítica principal do TIC–TIM é 2015–2025.

Tabelas de acesso utilizadas no repositório:

- `basedosdados.br_me_rais.microdados_vinculos`
- `basedosdados.br_me_rais.microdados_estabelecimentos`

A Base dos Dados funciona aqui como **camada de acesso computacional**. A fonte estatística substantiva continua sendo o Ministério do Trabalho e Emprego.

### 2.2 Novo CAGED

O Novo CAGED é utilizado para fluxos de admissões e desligamentos desde 2020. Ele combina informações provenientes do eSocial, CAGED e Empregador Web e possui metodologia própria de consolidação.

O estudo utiliza o Novo CAGED para:

- admissões;
- desligamentos;
- saldo de movimentações;
- intensidade aproximada dos fluxos.

O Novo CAGED não é utilizado como substituto da RAIS para medir estoque anual.

Tabela de acesso:

- `basedosdados.br_me_caged.microdados_movimentacao`

### 2.3 CNPJ — Cadastro Nacional da Pessoa Jurídica

Os Dados Abertos do CNPJ são empregados como fotografias cadastrais da estrutura empresarial. São considerados, conforme disponibilidade, situação cadastral, matriz/filial, atividade principal, porte, natureza jurídica, MEI e opção pelo Simples.

No estudo original foram consolidadas 47 fotografias entre 23 de novembro de 2021 e 11 de janeiro de 2026.

Diferenças entre snapshots não são interpretadas automaticamente como nascimentos ou mortes de empresas. O CNPJ é um cadastro administrativo sujeito a alterações de situação, atualização de registros e mudanças de cobertura.

Tabelas de acesso:

- `basedosdados.br_me_cnpj.estabelecimentos`
- `basedosdados.br_me_cnpj.empresas`
- `basedosdados.br_me_cnpj.simples`

A fonte substantiva é a Receita Federal do Brasil; a Base dos Dados é usada como camada de consulta.

### 2.4 CNAE

A estrutura econômica é classificada segundo a **Classificação Nacional de Atividades Econômicas — CNAE 2.0**, conforme estrutura e notas explicativas oficiais do IBGE/CONCLA.

A divisão CNAE é a escala principal das comparações setoriais. Classes e subclasses podem ser preservadas para auditorias ou aprofundamentos, mas os produtos regionais principais procuram manter comparabilidade e legibilidade.

### 2.5 CBO

A estrutura ocupacional utiliza a **Classificação Brasileira de Ocupações — CBO 2002**, do Ministério do Trabalho e Emprego. A família CBO em quatro dígitos é a escala detalhada preferencial; grandes grupos podem ser empregados em sínteses editoriais.

### 2.6 IPCA

Comparações remuneratórias longitudinais são expressas em reais de dezembro de 2025, utilizando o **Índice Nacional de Preços ao Consumidor Amplo — IPCA**. O procedimento utiliza índice de nível de dezembro de cada ano e converte valores nominais para o nível de preços do ano-base.

### 2.7 Malha municipal

Os mapas utilizam limites municipais oficiais e código IBGE de sete dígitos. A rotina auxiliar obtém ou lê a malha municipal e a reprojeta, quando necessário, para **SIRGAS 2000 / UTM zona 23S (EPSG:31983)** nos produtos cartográficos do estudo TIC–TIM.

---

## 3. Universo territorial TIC–TIM

O universo canônico contém 30 municípios paulistas. O script `scripts/preparar_config_tic_tim.py` reconstrói automaticamente a lista a partir da referência municipal congelada em `referencias/tic_tim_fichas_v2_7_quadro1.csv`, evitando a manutenção de uma segunda lista manual potencialmente divergente.

O conjunto é mantido constante em todas as análises comparativas. Anos anteriores à existência jurídica de um município devem ser tratados como não aplicáveis, e não como estoque igual a zero.

Para uso geral do `sou_rais`, qualquer outro conjunto de municípios pode ser informado em `municipios.csv`.

---

## 4. Instalação

Clone o repositório, crie um ambiente Python e instale o projeto em modo editável:

```bash
pip install -e ".[dev]"
```

Para executar a camada analítica TIC–TIM:

```bash
pip install -e ".[dev,analysis]"
```

Para mapas municipais:

```bash
pip install -e ".[dev,geo]"
```

O pacote instala também a CLI:

```bash
sou-rais
```

---

## 5. Credenciais e BigQuery

As consultas aos microdados públicos são realizadas via BigQuery. É necessário dispor de um projeto Google Cloud habilitado para executar jobs.

Em ambiente local:

```bash
gcloud auth application-default login
export BIGQUERY_PROJECT=seu-projeto-gcp
```

No Windows PowerShell:

```powershell
$env:BIGQUERY_PROJECT="seu-projeto-gcp"
```

O repositório não armazena credenciais.

Para execução pelo GitHub Actions, o workflow manual de reprodução utiliza GitHub Secrets:

- `BIGQUERY_PROJECT`
- `GCP_SERVICE_ACCOUNT_JSON`

O segundo deve conter o JSON da service account utilizada para autenticação. O workflow nunca imprime esse conteúdo nos logs.

---

## 6. Configuração

Para uso geral:

```bash
cp municipios.exemplo.csv municipios.csv
cp config.exemplo.json config.json
```

Estrutura mínima de `municipios.csv`:

```csv
id_municipio,nome
3516408,Franco da Rocha
3525904,Jundiai
```

Apenas `id_municipio` é obrigatório.

Configuração geral:

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

`validacao_municipios` aceita `strict`, `warning` e `off`.

Para o estudo TIC–TIM, recomenda-se não editar manualmente esses arquivos. Execute:

```bash
python scripts/preparar_config_tic_tim.py
```

A rotina produz a configuração canônica com 30 municípios, RAIS 2015–2025, Novo CAGED 2020-01 a 2025-12, snapshot final do CNPJ em 2026-01-11 e validação municipal estrita.

---

## 7. Processo completo de reprodução

A reprodução é organizada em etapas dependentes.

### Etapa 1 — diagnóstico do ambiente

```bash
sou-rais doctor
sou-rais config
```

Verifica instalação, credenciais, configuração e parâmetros principais.

### Etapa 2 — planejamento das consultas

```bash
sou-rais plan
```

O planejamento descobre cobertura temporal, divide municípios em lotes, registra consultas previstas e permite estimar custo antes da aquisição.

Para testar sem baixar dados:

```bash
sou-rais download all --dry-run
```

### Etapa 3 — aquisição

```bash
sou-rais download all
```

São adquiridos, em universos separados:

1. RAIS Vínculos;
2. RAIS Estabelecimentos;
3. Novo CAGED;
4. CNPJ.

Os dados brutos consultados não são versionados no Git. As partições locais ficam em `dados/processado/`.

### Etapa 4 — validação e indexação

```bash
sou-rais validate
```

ou, de forma explícita:

```bash
python scripts/validar_e_indexar.py
```

São conferidos schema, cobertura, municípios, períodos, partições fora do padrão e hashes.

### Etapa 5 — aquisição de auxiliares

```bash
python scripts/baixar_auxiliares_tic_tim.py
```

A rotina prepara IPCA e malha municipal usados na análise longitudinal e cartográfica.

### Etapa 6 — construção analítica

```bash
python scripts/analisar_tic_tim.py
```

O script lê as bases processadas e produz tabelas canônicas para estoque, crescimento, especialização, concentração, ocupações, remuneração, perfil sociodemográfico, CAGED, empregadores e CNPJ.

### Etapa 7 — intensidade aproximada dos fluxos

```bash
python scripts/calcular_intensidade_fluxos.py
```

A definição reconciliada com o caderno metodológico é:

```text
estoque_medio_t = (estoque_RAIS_{t-1} + estoque_RAIS_t) / 2
movimentacao_media_t = (admissoes_t + desligamentos_t) / 2
intensidade_t = movimentacao_media_t / estoque_medio_t
```

A medida representa intensidade relativa de entradas e saídas. Não acompanha indivíduos longitudinalmente e não deve ser denominada taxa de turnover individual em sentido estrito.

### Etapa 8 — gates de equivalência

Gate regional:

```bash
python scripts/validar_controles_regionais.py
```

Gate das fichas municipais:

```bash
python scripts/validar_fichas_publicadas.py
```

Gate genérico para qualquer tabela publicada:

```bash
python scripts/validar_equivalencia_tic_tim.py \
  calculado.csv referencia.csv \
  --chaves id_municipio \
  --colunas indicador1 indicador2
```

Os gates classificam equivalência, divergência e ausência de implementação. Valores de referência são congelados; divergências devem provocar investigação de filtros, schema, cobertura, classificação ou versão da fonte.

### Etapa 9 — figuras e mapas

```bash
python scripts/gerar_figuras_tic_tim.py
python scripts/gerar_mapas_tic_tim.py
```

A série cartográfica reproduz oito pranchas A3 associadas aos grandes blocos do relatório. Os mapas quantitativos utilizam escala frio→quente, do azul-claro ao vermelho-tinto; mapas categóricos preservam categorias nominais. Pranchas incluem título, legenda, escala, norte, fonte, nota metodológica e identificação territorial.

### Etapa 10 — execução orquestrada

Depois que `dados/processado/` estiver disponível:

```bash
python scripts/executar_pipeline_tic_tim.py
```

Ordem executada:

```text
análise
→ intensidade dos fluxos
→ gate regional
→ gate municipal
→ figuras
→ mapas
```

Para validação tabular sem visuais:

```bash
python scripts/executar_pipeline_tic_tim.py --sem-visuais
```

### Etapa 11 — execução completa no GitHub Actions

O workflow `.github/workflows/reproducao_tic_tim.yml` é acionado manualmente por `workflow_dispatch`.

Ele executa:

```text
configuração canônica
→ autenticação GCP
→ diagnóstico
→ planejamento
→ aquisição
→ validação
→ auxiliares
→ análise
→ intensidade
→ gates
→ figuras
→ mapas
→ artifact de resultados
```

Essa é a forma recomendada para uma execução de auditoria independente e documentada no próprio GitHub.

---

## 8. Indicadores principais

### 8.1 Estoque e crescimento

O estoque anual corresponde aos vínculos formais ativos em 31 de dezembro.

```text
Variação (%) = 100 × (Estoque_t1 - Estoque_t0) / Estoque_t0
```

A análise separa magnitude absoluta, taxa relativa e contribuição municipal ao crescimento regional.

### 8.2 Participação regional e redistribuição

```text
Participação_mt = Estoque_mt / Estoque_regiao,t
Mudança_pp = 100 × (Participação_m,2025 - Participação_m,2015)
```

“Redistribuição” é usada em sentido contábil e relativo. Não significa deslocamento físico de empresas ou trabalhadores.

### 8.3 Quociente Locacional

```text
QL_ms = (Emprego_ms / Emprego_m) / (Emprego_regiao,s / Emprego_regiao)
```

O QL mede especialização relativa ao conjunto de referência. O limiar `QL >= 1,25` é uma regra operacional de triagem do estudo, não um padrão universal.

QL elevado não implica automaticamente produtividade, competitividade ou importância econômica. O indicador deve ser lido juntamente com escala absoluta e participação do setor no município.

### 8.4 HHI e número efetivo

```text
HHI = soma(p_i²)
Numero_efetivo = 1 / HHI
```

O índice é empregado para concentração setorial, ocupacional ou territorial, conforme a distribuição analisada. Maior HHI indica maior concentração. O estudo não converte concentração automaticamente em vulnerabilidade.

### 8.5 Shift-share

A decomposição separa o crescimento observado em:

```text
efeito de referência
+ efeito de composição setorial
+ componente diferencial local
```

A formulação é contábil e descritiva. O componente diferencial não é interpretado como produtividade ou vantagem competitiva causal.

### 8.6 Remuneração real

A variável longitudinal prioritária é a remuneração de dezembro. Valores nominais são convertidos para reais de dezembro de 2025 pelo IPCA.

Vínculos com remuneração igual ou inferior a zero permanecem no estoque, mas são excluídos de:

- média;
- mediana;
- percentis;
- massa salarial;
- gaps remuneratórios.

Não há imputação editorial de salários ausentes ou inválidos.

### 8.7 Escolaridade

A escolaridade é analisada como atributo declarado na RAIS. A interpretação considera cobertura e a ruptura administrativa 2022–2023. Quando utilizada como dimensão relativa à estrutura ocupacional, a referência empírica por CBO deve ser documentada separadamente da simples distribuição observada de escolaridade.

### 8.8 Perfil etário

O pipeline calcula idade mediana, participação de jovens, participação de vínculos em faixas superiores e índice de envelhecimento.

O indicador não mede diretamente reposição futura de mão de obra; ele descreve a composição etária observada do estoque formal.

### 8.9 Sexo e raça/cor

Participações e gaps remuneratórios são produzidos apenas com categorias identificáveis e devem ser acompanhados de informação de cobertura. Diferenças brutas não são interpretadas como estimativas causais de discriminação.

### 8.10 Empregadores

A RAIS Estabelecimentos é usada para medir número de empregadores com estoque positivo e participação dos maiores estabelecimentos no emprego municipal.

A participação dos dez maiores empregadores é uma medida de concentração da distribuição dos vínculos entre estabelecimentos, não uma medida de poder de mercado.

### 8.11 CNPJ

Snapshots do CNPJ descrevem a estrutura cadastral ativa, incluindo MEI e Simples. Eles não são convertidos automaticamente em estoque de empregos nem em demografia empresarial.

---

## 9. Comparabilidade e cautelas

### Ruptura RAIS 2022–2023

A incorporação crescente do eSocial alterou cobertura e declaração de algumas dimensões. A documentação do MTE registra problemas específicos, inclusive subdeclaração remuneratória em segmentos da administração pública em 2023.

Por isso, o estudo diferencia:

- fotografia transversal recente;
- variação longitudinal que atravessa a ruptura.

A segunda exige cautela e, quando substantiva para uma conclusão, triangulação com anos intermediários ou fontes complementares.

### RAIS versus Novo CAGED

RAIS é estoque anual; Novo CAGED é movimentação. O saldo anual do CAGED não deve ser usado mecanicamente para reconstruir o estoque RAIS.

### Estabelecimentos versus CNPJ

Um estabelecimento empregador RAIS e uma inscrição CNPJ ativa não são universos equivalentes. Uma inscrição pode estar ativa sem possuir vínculos formais e as bases têm processos administrativos distintos.

### Ausência de município de residência

A base usada nesta reprodução localiza o vínculo pelo estabelecimento. Ela não reconstrói fluxos residência–trabalho e não deve ser transformada em matriz de deslocamentos pendulares.

### Causalidade

Nenhum indicador deste pipeline identifica impacto causal do TIC–TIM. Avaliação futura exigirá estratégia específica de identificação, grupo de comparação e controle de tendências anteriores.

---

## 10. Estrutura dos notebooks e scripts

Notebooks:

1. `00_configurar_municipios.ipynb`
2. `10_rais.ipynb`
3. `20_novo_caged.ipynb`
4. `30_cnpj.ipynb`
5. `40_validar_e_indexar.ipynb`
6. `90_tic_tim_emprego_analise_completa.ipynb`

O notebook `90_tic_tim_emprego_analise_completa.ipynb` é o ponto de entrada interativo. A lógica metodológica reutilizável permanece fora do notebook em `tic_tim_analysis.py`, para permitir testes unitários e reuso independente da interface Jupyter.

Scripts principais:

- `scripts/preparar_config_tic_tim.py`
- `scripts/baixar_rais.py`
- `scripts/baixar_novo_caged.py`
- `scripts/baixar_cnpj.py`
- `scripts/validar_e_indexar.py`
- `scripts/baixar_auxiliares_tic_tim.py`
- `scripts/analisar_tic_tim.py`
- `scripts/calcular_intensidade_fluxos.py`
- `scripts/validar_controles_regionais.py`
- `scripts/validar_fichas_publicadas.py`
- `scripts/validar_equivalencia_tic_tim.py`
- `scripts/gerar_figuras_tic_tim.py`
- `scripts/gerar_mapas_tic_tim.py`
- `scripts/executar_pipeline_tic_tim.py`

---

## 11. Estrutura de saída

```text
dados/
├── processado/
│   ├── rais/
│   │   ├── vinculos/
│   │   └── estabelecimentos/
│   ├── caged/
│   └── cnpj/
├── auxiliares/
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

---

## 12. Reprodutibilidade, integridade e gates

Cada partição adquirida pode registrar:

- base e tipo;
- lote de municípios;
- período ou snapshot;
- caminho relativo;
- número de linhas;
- municípios ausentes;
- SHA-256.

A camada analítica gera controles adicionais de completude e equivalência.

As referências canônicas atualmente versionadas incluem:

- `referencias/tic_tim_fichas_v2_7_quadro1.csv`
- `referencias/tic_tim_fichas_v2_7_quadro1.metadata.json`
- `referencias/tic_tim_controles_regionais_v16_26.csv`
- `referencias/tic_tim_controles_regionais_v16_26.metadata.json`

Essas referências funcionam como **testes de regressão empírica**. Uma execução nova deve reproduzi-las dentro das tolerâncias definidas. Divergência não autoriza ajuste retroativo da referência; exige investigação.

Entre os controles regionais congelados estão estoque formal, massa salarial observada, admissões, desligamentos, saldo, empregadores positivos, CNPJs ativos e série 2020–2025 da intensidade aproximada dos fluxos.

---

## 13. Produtos analíticos

O pipeline foi desenhado para alimentar três produtos públicos complementares do estudo TIC–TIM:

1. **Relatório Regional — Emprego e Estrutura Econômica**: síntese das tendências e contrastes regionais;
2. **Caderno de Fichas Municipais**: leitura padronizada dos 30 municípios;
3. **Caderno Metodológico**: fontes, processamento, indicadores, critérios de interpretação, controles e limites.

O código não substitui esses documentos; ele fornece a trilha de reprodução numérica e gráfica que os sustenta.

---

## 14. Referências metodológicas e institucionais

As referências abaixo correspondem às fontes e à bibliografia adotadas na metodologia pública do estudo. O README as apresenta em formato próximo ao padrão ABNT para tornar explícita a fundamentação dos dados e dos procedimentos analíticos.

BRASIL. Ministério do Trabalho e Emprego. **Nota técnica sobre o Novo CAGED**. Brasília, DF: MTE, 2020. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/notas-tecnicas/1796-nota-tecnica-sobre-o-novo-caged. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **Classificação Brasileira de Ocupações — CBO: saiba mais**. Brasília, DF: MTE, 2023. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo/saiba-mais. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **Nota técnica RAIS 2023**. Brasília, DF: MTE, 2024. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2023/nota-tecnica-rais-2023_11-12-2024.pdf. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **Microdados RAIS e CAGED**. Brasília, DF: MTE, 2026. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/microdados-rais-e-caged. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **O que é o Novo CAGED?** Brasília, DF: MTE, 2026. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/o-pdet/o-que-e-o-novo-caged. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **RAIS 2025**. Brasília, DF: MTE, 2026. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2025. Acesso em: 30 ago. 2026.

BRASIL. Ministério do Trabalho e Emprego. **Comunicado — Microdados RAIS 2024**. Brasília, DF: MTE, 2026. Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/comunicados/comunicado-microdados-rais-2024. Acesso em: 30 ago. 2026.

BRASIL. Receita Federal do Brasil. **Novo layout para os dados abertos do CNPJ**. Brasília, DF: RFB, 2021. Disponível em: https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf. Acesso em: 30 ago. 2026.

BRASIL. Receita Federal do Brasil. **Dados abertos — Cadastros: Cadastro Nacional da Pessoa Jurídica**. Brasília, DF: RFB, 2026. Disponível em: https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/cadastros. Acesso em: 30 ago. 2026.

DUNN JR., Edgar S. **A statistical and analytical technique for regional analysis**. *Papers in Regional Science*, v. 6, n. 1, p. 97–112, 1960. DOI: 10.1111/j.1435-5597.1960.tb01705.x.

HERFINDAHL, Orris C. **Concentration in the U.S. steel industry**. 1950. 175 f. Tese (Doutorado) — Columbia University, New York, 1950.

HIRSCHMAN, Albert O. **National power and the structure of foreign trade**. Berkeley: University of California Press, 1945.

IBGE. Centro de Documentação e Disseminação de Informações. **Normas de apresentação tabular**. 3. ed. Rio de Janeiro: IBGE, 1993. 62 p. ISBN 85-240-0471-1. Disponível em: https://biblioteca.ibge.gov.br/visualizacao/livros/liv23907.pdf. Acesso em: 30 ago. 2026.

IBGE. Comissão Nacional de Classificação. **Classificação Nacional de Atividades Econômicas — CNAE 2.0: estrutura detalhada e notas explicativas**. Rio de Janeiro: IBGE, 2015. Disponível em: https://ftp.ibge.gov.br/Informacoes_Gerais_e_Referencia/Classificacoes/CNAE/cnae2_0_2edicao/cnae2_0_2edicao_20150609.pdf. Acesso em: 30 ago. 2026.

IBGE. **Sistema Nacional de Índices de Preços ao Consumidor: métodos de cálculo**. 8. ed. Rio de Janeiro: IBGE, 2020. 149 p. Série Relatórios Metodológicos, v. 14. Disponível em: https://biblioteca.ibge.gov.br/visualizacao/livros/liv101767.pdf. Acesso em: 30 ago. 2026.

ISSERMAN, Andrew M. **The location quotient approach to estimating regional economic impacts**. *Journal of the American Institute of Planners*, v. 43, n. 1, p. 33–41, 1977. DOI: 10.1080/01944367708977758.

JANNUZZI, Paulo de Martino. **Indicadores sociais no Brasil: conceitos, fontes de dados e aplicações**. 6. ed. Campinas: Alínea, 2017. 196 p. ISBN 978-85-7516-807-3.

OCDE. **Job creation and local economic development 2024: the geography of generative AI**. Paris: OECD Publishing, 2024. Disponível em: https://www.oecd.org/en/publications/job-creation-and-local-economic-development-2024_83325127-en/. Acesso em: 30 ago. 2026.

OIT. **Measuring job quality: difficult but necessary**. Geneva: ILOSTAT, 2020. Disponível em: https://ilostat.ilo.org/blog/measuring-job-quality-difficult-but-necessary/. Acesso em: 30 ago. 2026.

PAIVA, Carlos A. N.; JANNUZZI, Paulo M. **Indicadores socioeconômicos e análise regional: fundamentos da centralidade do Quociente Locacional**. *Informe GEPEC*, v. 26, n. 3, 2022. DOI: 10.48075/igepec.v26i3.29569.

### Base dos Dados

As tabelas públicas da Base dos Dados são usadas como infraestrutura de acesso ao BigQuery. Para interpretação substantiva devem prevalecer as definições, notas técnicas e layouts dos órgãos produtores originais — MTE, Receita Federal e IBGE.

---

## 15. Padrões editoriais dos produtos

Tabelas e figuras devem ser compreensíveis de forma autônoma, com título, unidade, período, fonte e notas necessárias. A apresentação tabular segue, sempre que pertinente, as **Normas de Apresentação Tabular do IBGE**.

Mapas devem informar legenda, escala, orientação, sistema de referência, fonte e identificação territorial suficiente. Quando o tamanho de um símbolo representa uma grandeza, a legenda deve explicitar essa dimensão.

Essas regras editoriais fazem parte da reprodutibilidade: o pipeline não busca apenas reproduzir números, mas também documentar como esses números são transformados em objetos analíticos legíveis.

---

## 16. Testes e empacotamento

```bash
pytest -q
python -m build
python -m twine check dist/*
```

O workflow `tests.yml` executa:

- instalação do projeto e dependências de desenvolvimento;
- teste da CLI;
- testes unitários;
- geração de `sdist` e `wheel`;
- verificação dos metadados da distribuição;
- instalação limpa do wheel.

Esses testes verificam a integridade do software. A equivalência empírica com a publicação é verificada separadamente pelos gates regionais e municipais sobre os microdados efetivamente adquiridos.

---

## 17. Status da reprodução TIC–TIM

A arquitetura computacional, as fórmulas principais, as referências congeladas e os testes unitários estão implementados. O fechamento da reprodução exige uma execução empírica completa sobre os microdados públicos, seguida da aprovação dos gates regionais e municipais.

Por essa razão, a passagem dos testes de software não deve ser interpretada, isoladamente, como prova de equivalência integral com todos os produtos publicados.

---

## 18. Changelog e licença

As mudanças por versão estão documentadas em `CHANGELOG.md`.

O código é distribuído sob a licença MIT. Consulte `LICENSE`.
