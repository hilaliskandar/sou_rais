# Protocolo de reprodução — Emprego e Estrutura Econômica TIC-TIM

## 1. Finalidade

Este documento registra o contrato metodológico da reprodução computacional do estudo TIC-TIM de Emprego e Estrutura Econômica. O objetivo é permitir que a aquisição, transformação, cálculo de indicadores, tabelas e produtos visuais possam ser refeitos a partir das fontes públicas, sem dependência de caminhos pessoais, Google Drive ou artefatos manuais não documentados.

A janela analítica principal é 2015-2025. Os marcos 2015, 2019, 2020, 2022 e 2025 devem ser preservados nas comparações por representarem início da janela, período pré-pandemia, choque pandêmico, transição administrativa recente e fechamento da linha de base.

## 2. Princípios obrigatórios

1. RAIS Vínculos, RAIS Estabelecimentos, Novo CAGED e CNPJ são universos distintos.
2. Vínculo não é sinônimo de trabalhador: um indivíduo pode possuir mais de um vínculo.
3. O Novo CAGED mede movimentações, não estoque.
4. O CNPJ é fotografia cadastral; snapshots não devem ser interpretados como série anual de emprego ou demografia empresarial líquida.
5. Remuneração zero permanece no estoque de vínculos, mas é excluída dos cálculos de remuneração.
6. Descontinuidades de cobertura, especialmente na passagem 2022-2023, devem ser marcadas antes de receber interpretação substantiva.
7. Não se produz índice sintético geral de qualidade, vulnerabilidade ou maturidade do mercado de trabalho.
8. QL, HHI, shift-share, intensidade de fluxos e gaps são medidas descritivas e não estimativas causais.

## 3. Fontes

### RAIS Vínculos

Uso: estoque anual em 31/12, CNAE, CBO, escolaridade, remuneração, idade, sexo, raça/cor, tempo de vínculo, jornada e modalidades contratuais.

### RAIS Estabelecimentos

Uso: número de estabelecimentos com estoque positivo, distribuição dos vínculos entre empregadores, HHI empresarial e participações Top 1/5/10/20.

### Novo CAGED

Uso: admissões, desligamentos, saldo e intensidade aproximada dos fluxos. A série começa em 2020 e não deve ser emendada mecanicamente a regimes anteriores.

### CNPJ

Uso: situação cadastral, matriz/filial, CNAE principal, porte, MEI e Simples, quando disponíveis nos snapshots públicos.

### CNAE 2.0 e CBO 2002

A divisão CNAE é a escala setorial principal. A família CBO em quatro dígitos é a escala ocupacional detalhada preferencial.

### IPCA

Remunerações históricas são convertidas para reais de dezembro de 2025.

### Malha municipal

A cartografia usa limites municipais oficiais em SIRGAS 2000. A fonte, data e hash da malha utilizada devem ser registrados no manifesto de execução.

## 4. Fórmulas canônicas

### Crescimento do estoque

`crescimento = 100 * (estoque_final / estoque_inicial - 1)`

### Participação regional

`participacao = estoque_municipio / estoque_30_municipios`

A mudança de participação é expressa em pontos percentuais.

### Quociente Locacional

`QL = (emprego_setor_municipio / emprego_total_municipio) / (emprego_setor_regiao / emprego_total_regiao)`

O universo de referência do estudo é o conjunto dos 30 municípios. QL > 1 indica participação local acima da referência. O marcador QL >= 1,25 pode ser usado como convenção de especialização pronunciada, sem interpretação automática de competitividade.

### HHI

`HHI = soma(share_i ** 2)`

O número efetivo de categorias é `1 / HHI`.

### Shift-share

Para cada setor municipal com estoque inicial positivo:

- efeito regional: `E0 * g`;
- efeito mix: `E0 * (g_setor - g)`;
- efeito local: `E0 * (g_local - g_setor)`.

A soma dos três componentes deve reconstruir a variação observada, dentro de tolerância numérica. Setores com estoque inicial zero são marcados como não elegíveis para a decomposição relativa.

### Remuneração real

`remuneracao_real_t = remuneracao_nominal_t * (IPCA_dez_2025 / IPCA_dez_t)`

A mediana é a medida central preferencial. A cobertura remuneratória corresponde à proporção de vínculos com remuneração positiva. A massa salarial observada é a soma das remunerações positivas de dezembro.

### Novo CAGED

`saldo = admissoes - desligamentos`

`intensidade = ((admissoes + desligamentos) / 2) / estoque_referencia`

A intensidade é uma medida aproximada de movimentação relativa e não uma taxa longitudinal de rotatividade individual.

### Índice de envelhecimento

`indice_envelhecimento = 100 * (share_55_mais / share_ate_29)`

O indicador descreve o estoque formal, não a população residente.

### Gap remuneratório por sexo

`gap_sexo = 100 * (mediana_feminina / mediana_masculina - 1)`

### Gap remuneratório por raça/cor

Nas fichas publicadas, o gap compara remunerações médias dos vínculos pretos/pardos e brancos com raça/cor identificada:

`gap_raca = 100 * (media_pretos_pardos / media_brancos - 1)`

### Referência empírica de escolaridade por CBO

Para cada família CBO e ano, calcula-se a mediana de escolaridade observada no conjunto dos 30 municípios quando houver pelo menos 50 vínculos na célula. Distâncias ordinais de +2 ou mais são classificadas como acima da referência; -2 ou menos, abaixo; os demais casos, próximos. A medida não é requisito normativo de escolaridade da ocupação.

## 5. Produtos mínimos

A execução completa deve gerar, no mínimo:

- estoque municipal anual;
- estoque regional anual;
- crescimento e mudança de participação regional;
- estrutura CNAE e QL;
- HHI setorial e número efetivo de setores;
- shift-share por município e setor;
- estrutura CBO e QL ocupacional;
- escolaridade e referência empírica CBO;
- remuneração real, cobertura e massa salarial;
- Novo CAGED: admissões, desligamentos, saldo e intensidade;
- perfil etário e índice de envelhecimento;
- sexo, raça/cor e gaps remuneratórios;
- concentração de empregadores e Top 1/5/10/20;
- fotografia CNPJ;
- tabelas-síntese para fichas municipais;
- gráficos regionais;
- mapas temáticos municipais;
- auditoria de completude;
- manifesto SHA-256 dos produtos.

## 6. Série cartográfica do Relatório Regional

A reprodução editorial do relatório deve contemplar oito mapas-síntese:

1. mudança da participação regional 2015-2025, com círculo proporcional ao acréscimo absoluto;
2. principal especialização setorial em 2025, condicionada a QL >= 1,25;
3. HHI ocupacional em 2025;
4. variação real da remuneração mediana 2015-2025;
5. intensidade aproximada dos fluxos em 2025;
6. índice de envelhecimento em 2025;
7. participação dos dez maiores empregadores em 2025;
8. síntese bivariada: crescimento do estoque x variação real da remuneração.

Os mapas quantitativos devem usar convenção cromática contínua de frio para quente, começando em azul claro e terminando em vermelho tinto, com legenda explícita. Símbolos proporcionais devem possuir legenda de tamanho. Todos os municípios devem ser identificáveis e a checagem de sobreposição de rótulos deve integrar a auditoria visual.

## 7. Gates de equivalência

Antes de considerar a reprodução encerrada, devem ser executados controles contra os produtos publicados.

### Gate A — universo

- 30 municípios canônicos;
- códigos IBGE válidos;
- cobertura dos anos definidos;
- ausência tratada como ausência, não como zero, quando a observação não é aplicável.

### Gate B — agregação

- totais municipais reconciliados com totais regionais;
- composição setorial e ocupacional soma ao estoque aplicável;
- denominadores explicitados.

### Gate C — fórmulas

- QL e HHI testados em exemplos sintéticos;
- shift-share com erro de reconstrução próximo de zero;
- intensidade do Novo CAGED conforme fórmula canônica;
- índice de envelhecimento conforme fórmula canônica.

### Gate D — remuneração

- remuneração zero excluída somente dos cálculos salariais;
- IPCA de dezembro registrado e versionado;
- mediana 2025 e variação real reconciliadas com a publicação;
- cobertura remuneratória preservada.

### Gate E — fichas municipais

Para cada município, comparar ao menos:

- estoque 2025;
- crescimento 2015-2025;
- mediana real 2025;
- massa salarial;
- saldo CAGED;
- idade mediana;
- participação feminina;
- Top 10 empregadores;
- cinco maiores CNAE e respectivos QL;
- cinco maiores famílias CBO e respectivos QL.

### Gate F — mapas

- todos os 30 municípios presentes;
- rótulos legíveis;
- legenda completa;
- círculos proporcionais com legenda;
- unidade, período, fonte e CRS documentados;
- ausência de sobreposição crítica.

## 8. Territorialização de empregadores

A territorialização intraurbana não deve ser misturada à reprodução municipal básica. Ela constitui módulo próprio e precisa conservar a linhagem de regras de alocação (quadra, conjunto de quadras, setor e níveis de incerteza). A eventual incorporação ao repositório deve ocorrer após migração controlada dos notebooks históricos e criação de testes específicos de equivalência.

## 9. Status atual da implementação

O arquivo `tic_tim_analysis.py` contém o núcleo das fórmulas canônicas e `tests/test_tic_tim_analysis.py` contém testes unitários sintéticos. O notebook `90_tic_tim_emprego_analise_completa.ipynb` constitui o orquestrador inicial.

O pipeline somente deve ser declarado equivalente à publicação após executar os gates contra os valores canônicos dos entregáveis finais.