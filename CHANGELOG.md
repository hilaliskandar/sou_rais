# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue, em linhas gerais, Keep a Changelog e o versionamento segue Semantic Versioning.

## [0.1.0] - 2026-08-17

### Adicionado

- aquisição reproduzível de RAIS vínculos e estabelecimentos por código IBGE municipal;
- aquisição de microdados do Novo CAGED por competência;
- aquisição otimizada de snapshots do CNPJ, com uma consulta BigQuery por snapshot e divisão local em lotes;
- configuração por `municipios.csv`, lista inline e `config.json`;
- seleção opcional de períodos para RAIS, Novo CAGED e CNPJ;
- execução incremental com reaproveitamento de Parquets existentes;
- gravação atômica em Parquet com compressão Snappy;
- manifesto de execução com contagem de linhas, ausências municipais e SHA-256;
- validação municipal configurável em `strict`, `warning` e `off`;
- modo `dry-run` com estimativa de bytes processados e planejamento de consultas;
- validador e índice local de partições;
- CLI unificada `sou-rais`;
- notebooks finos para uso interativo;
- testes automatizados em GitHub Actions;
- documentação para execução local sem Google Drive ou Google Colab.

### Notas metodológicas

- RAIS é tratada como base anual de estoque e declaração;
- Novo CAGED permanece separado de regimes históricos anteriores a 2020;
- CNPJ é tratado como sequência de snapshots administrativos e não como série anual de emprego.
