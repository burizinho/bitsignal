# Architecture & Design Sitemap

| Design Document | Date | Author | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| [Bitcoin Macro Cycle Sentinel (BitSignal)](bitcoin_macro_cycle_sentinel.md) | 2026-11-05 | Project Lead | Superseded | Autonomous quantitative macro cycle sentinel with piecewise linear normalization, defensive circuit breakers, and tiered cold-storage alert runbooks. |
| [Estratégia de Ciclo Macro com Gestão Tributária Nacional](bitcoin_national_execution_strategy.md) | 2026-11-06 | @Guilherme | Superseded | Orquestração de compras em degraus (-30% a -65%), saídas em múltiplos de ATH (V1-V5), trailing stops semanais (21w EMA / 50w SMA) e otimização fiscal de R$ 35k/mês com DARF 15% para posições <0.5 BTC. |
| [Modelo de Ciclo Unificado e Painel Só de Leitura](bitcoin_unified_cycle_model.md) | 2026-11-08 | @burizinho | Approved — Phase 1 Implementation (Fase 2: Proposed) | Substitui o modelo de alertas do Sentinel e a estratégia nacional: score de valuation + detector de reversão independente, teto de venda compartilhado de 50% com catraca, DCA pelo score, CoinMetrics como fonte única, painel Streamlit só de leitura e backtest com critérios de carteira. |
| [Fase 2 — Variantes de comparação (diagnóstico)](bitcoin_cycle_phase2_variants.md) | 2026-11-09 | @burizinho | Approved | Variantes do catálogo pré-registrado rodadas só no CLI, sobre janelas já vistas, para descobrir qual peça faz o modelo perder para comprar e segurar; não aprova nem substitui o padrão. |
