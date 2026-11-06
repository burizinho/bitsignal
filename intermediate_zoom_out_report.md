# Intermediate Zoom Out Review Report: Estratégia de Ciclo Macro com Gestão Tributária Nacional

**Target Document:** `docs/designs/bitcoin_national_execution_strategy.md` (lines 1..349)  
**Standard:** `resources/document_standards/zoom-out-standard.md`  
**Reviewer:** Skeptical Architect (Intermediate Zoom Out)  
**Date:** 2026-11-06  

---

## Executive Summary

Após a consolidação dos relatórios de Compreensão (`comprehension_report.md`), Crítica Técnica (`critic_report.md`) e Prontidão de Implementação (`implementation_readiness_report.md`), esta auditoria intermediária avalia as mitigações propostas sob a ótica de simplicidade radical, YAGNI, reuso da base de código e viabilidade operacional.

A proposta é viável e de alto valor, mas requer simplificação arquitetural imediata antes de seguir para a codificação:
1. **Eliminação de Tabelas de Estado Redundantes:** O design ganha robustez drástica ao descartar `strategy_state` e `tax_monthly_ledger` como tabelas mutáveis. Adotar `portfolio_transactions` como ledger único e append-only.
2. **Reuso Estrito de `bitsignal.engine.indicators`:** Reutilizar `calculate_sma` e `calculate_ema` já existentes e testados.
3. **Consolidação de Módulos (Anti-Fragmentação):** Reduzir a fragmentação de 5 arquivos no pacote `bitsignal.strategy` para 2 módulos coesos (`models.py` e `engine.py`).
4. **Resolução de Conflito de Paradigma:** Definir no `config.yaml` a chave `strategy_mode` para determinar se os alertas de desova de 90% substituem o alerta padrão de 40% do sentinela macro.

---

## Síntese de Decisões Arquiteturais Intermediárias

| Eixo de Auditoria | Avaliação / Diagnóstico | Diretriz de Simplificação |
| :--- | :--- | :--- |
| **Persistência SQLite** | 3 tabelas interligadas geram risco de dessincronização e problemas de migração. | **Manter apenas `portfolio_transactions`.** Saldo, CMP e alienação mensal calculados deterministicamente on-demand. |
| **Indicadores Técnicos** | O plano criava um novo calculador de médias móveis. | **Reuso obrigatório** de `bitsignal.engine.indicators.calculate_sma` e `calculate_ema`. |
| **Tributação e PTAX** | Risco de dependência de API do BACEN indisponível aos domingos. | A tributação RFB em corretoras nacionais utiliza o **preço real de execução em BRL** da nota de corretagem. O PTAX deve ser meramente informativo/fallback. |
| **Execução Dominical** | Risco de travamento por limite noturno de PIX às 21h00. | Orientar expressamente o agendamento de saque PIX para as 06h01 de segunda-feira quando o valor exceder o limite noturno bancário. |
| **Agendamento** | O avaliador semanal precisa ser acionado na rotina diária e no pré-alerta. | Integrar a checagem semanal em `bitsignal/cli.py` (`cmd_run_daily`) e criar workflow simples para o pré-alerta dominical das 18h BRT. |
