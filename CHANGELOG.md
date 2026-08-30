# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

## [Unreleased]

### Adicionado
- Notebook mestre `90_tic_tim_emprego_analise_completa.ipynb` para reprodução da análise TIC-TIM a partir das bases adquiridas pelo próprio repositório.
- Módulo `tic_tim_analysis.py` com fórmulas canônicas de QL, HHI, shift-share, remuneração real, intensidade de fluxos, perfil etário, gaps remuneratórios, referência empírica de escolaridade por CBO e concentração de empregadores.
- Testes unitários sintéticos para os principais indicadores TIC-TIM.
- Protocolo `docs/TIC_TIM_REPRODUCAO.md` com princípios, fórmulas, produtos mínimos e gates de equivalência.
- Extra opcional `analysis` com NumPy, Matplotlib e GeoPandas.

## [0.1.0]

### Adicionado
- CLI `sou-rais` para planejar, baixar e validar RAIS, Novo CAGED e CNPJ.
- Planejamento/dry-run de consultas e estimativa de bytes no BigQuery.
- Validação configurável de municípios (`strict`, `warning`, `off`).
- Manifesto de execuções com SHA-256.
- Índice de partições Parquet e detecção de arquivos fora do padrão.
- Notebooks interativos de aquisição e validação.
- Scripts equivalentes para execução sem notebook.
- Testes, build de pacote e GitHub Actions.
