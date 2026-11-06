# Consolidated Review Report: Estratégia de Ciclo Macro com Gestão Tributária Nacional

**Target Document:** [`docs/designs/bitcoin_national_execution_strategy.md`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md)  
**Date:** 2026-11-06  
**Pipeline Mode:** Uninterrupted Full Flow (5 Stages Completed)  
**Deliverable:** Consolidated Multi-Lens Audit Findings & Traceability Matrix  

---

## 1. Executive Summary & Verdict

O plano para orquestração de ciclo macro do Bitcoin adaptado ao contexto tributário brasileiro (< 0.5 BTC) foi aprovado conceitualmente com mérito técnico elevado, mas recebeu **apontamentos críticos e convergentes** das 5 lentes revisoras (`egm-zoom-out`, `egm-comprehension`, `egm-design`, `egm-structural`, `egm-codebase-details` e `egm-style`).

A especificação requer ajustes estruturais em três frentes antes de seguir para a fase de implementação:
1. **Correção Lógica e Tributária:** Ajustar o algoritmo fiscal para considerar o volume acumulado mensal da RFB, tratar o limite noturno do PIX bancário aos domingos às 21h e eliminar a dependência frágil da API de PTAX do BACEN (já que operações no Brasil são tributadas pelo valor real da nota de corretagem em BRL).
2. **Simplicidade Radical e Reuso de Código (Zoom Out / YAGNI):** Eliminar tabelas secundárias de cache no SQLite (`strategy_state` e `tax_monthly_ledger`) em favor de um **ledger transacional único e append-only** (`portfolio_transactions`), e reutilizar diretamente as funções `calculate_sma` e `calculate_ema` de `bitsignal.engine.indicators`.
3. **Completude Operacional:** Integrar a rotina de avaliação no `cmd_run_daily`, prever gatilho de liquidação da 2ª parte do split no dia 1º do mês e parametrizar a coexistência com a política padrão do BitSignal de 60% de reserva soberana.

---

## 2. Severidade Consolidada dos Achados

| Severidade | Quantidade | Principais Tópicos |
| :---: | :---: | :--- |
| 🔴 **Blocker** | **6** | Lógica fiscal RFB e assinatura do método; PIX noturno aos domingos; PTAX em finais de semana; tabelas redundantes em SQLite; acoplamento no pipeline diário; gatilho do dia 1º para split. |
| 🟡 **Major** | **6** | Conflito filosófico com Baseline de 60% do Core; reuso de indicadores existentes; alinhamento de CUJ 2 e matemática do CMP; ambiguidade de timezone (`weekday == 0`); amostragem semanal da 21w EMA; arquivo autorreferencial. |
| 🟢 **Nit** | **4** | Sintaxe de fórmulas LaTeX; expansão de siglas fiscais/financeiras; argumentos CLI de `strategy-record-tx`; clarificação do escopo de DARF vs. SicalcWeb. |

---

## 3. Matriz Consolidada de Ações e Rastreabilidade

| ID | Severidade | Tópico / Discrepância | Lentes de Origem | Ação Corretiva Exigida na Especificação |
| :---: | :---: | :--- | :--- | :--- |
| **ACT-01** | 🔴 **Blocker** | Lógica e Assinatura de `evaluate_tax_strategy` | `egm-design`, `egm-comprehension`, `egm-zoom-out` | Refatorar a assinatura para receber `month_accumulated_brl`, `quantity_btc` e `current_cmp_brl`. Aplicar o teto de R$ 35k sobre o valor acumulado do mês e garantir que nenhuma parcela do split exceda R$ 35k. |
| **ACT-02** | 🔴 **Blocker** | Travamento de Limite Noturno do PIX às 21h de Domingo | `egm-design`, `egm-style` | Incorporar protocolo bancário no runbook: para valores superiores ao limite noturno cadastrado no banco (ex: > R$ 5.000), orientar o usuário a manter o saldo em BRL na exchange e agendar o PIX para as 06h01 de segunda-feira. |
| **ACT-03** | 🔴 **Blocker** | PTAX do BACEN aos Domingos vs. Preço Real em BRL | `egm-design`, `egm-zoom-out`, `egm-codebase-details` | Pela IN RFB 1.888/2019, operações nacionais são tributadas pelo valor real da nota de corretagem em BRL. Remover PTAX como dependência rígida de cálculo e usar o preço real da transação, mantendo PTAX apenas como referência informativa D-1 útil. |
| **ACT-04** | 🔴 **Blocker** | Redundância de Estado e Risco de Crash em SQLite | `egm-zoom-out`, `egm-codebase-details` | Simplificar o modelo: manter `portfolio_transactions` como ledger único e append-only. Calcular saldo, CMP e alienações mensais on-demand ou via SQL Views, eliminando tabelas mutáveis de cache. |
| **ACT-05** | 🔴 **Blocker** | Conexão Automática na Rotina Diária (`cli.py`) | `egm-codebase-details` | Descrever a modificação em `bitsignal/cli.py` para invocar a auditoria de estratégia dentro de `cmd_run_daily()` nas segundas-feiras às 00:05 UTC, e adicionar cron para o pré-alerta dominical das 18h BRT. |
| **ACT-06** | 🔴 **Blocker** | Agendamento da Parcela 2 do Split Intermensal no Dia 1º | `egm-comprehension` | Formalizar que a rotina diária do BitSignal no dia 1º de cada mês checa ordens com status de split pendente e emite o alerta de execução da segunda metade às 09h00 BRT. |
| **ACT-07** | 🟡 **Major** | Conflito com Baseline Soberano de 60% do BitSignal Core | `egm-zoom-out` | Adicionar chave no `config.yaml` (`strategy_mode: sovereign_sentinel | tax_optimized_cycle`) especificando que a ativação da estratégia nacional customiza os alertas de desova de topo do despachante Telegram. |
| **ACT-08** | 🟡 **Major** | Reuso Obrigatório de `bitsignal.engine.indicators` | `egm-zoom-out`, `egm-codebase-details` | Eliminar código redundante de médias móveis em `trailing_stops.py`. Importar e reutilizar diretamente `calculate_sma` e `calculate_ema` da engine do BitSignal. |
| **ACT-09** | 🟡 **Major** | Alinhamento do CUJ 2 e Correção Matemática do CMP no CUJ 1 | `egm-structural` | Corrigir o cálculo do CMP no CUJ 1 para R$ 316.734,69/BTC. No CUJ 2, ajustar o valor da tranche para > R$ 35k (ex: 0.08 BTC) para demonstrar a mecânica real do split, ou renomear o caso de uso. |
| **ACT-10** | 🟡 **Major** | Ambiguidade de Timezone (`weekday() == 0`) | `egm-structural`, `egm-style` | Fixar na documentação que todas as comparações temporais usam explicitamente `datetime.now(timezone.utc).weekday() == 0` (segunda-feira 00h00 UTC = domingo 21h00 BRT). |
| **ACT-11** | 🟡 **Major** | Amostragem Correta da 21w EMA sobre Velas Semanais | `egm-comprehension`, `egm-codebase-details` | Clarificar que a 21w EMA é aplicada sobre a série reamostrada de fechamentos semanais de domingo (`weekly_candles`), e não sobre 147 dias diários. |
| **ACT-12** | 🟡 **Major** | Remoção de Entrada Circular na Tabela de Implementação | `egm-style`, `egm-codebase-details` | Remover o próprio arquivo de design doc da tabela de arquivos a serem criados durante a implementação de código. |
| **ACT-13** | 🟢 **Nit** | Fórmulas LaTeX Quebradas | `egm-style` | Escapar adequadamente barras invertidas de $\text{EMA}_{21w}$ e $\alpha = \frac{2}{21+1}$ no Markdown. |
| **ACT-14** | 🟢 **Nit** | Expansão de Acrônimos (MVRV, DARF, GCAP, FGC) | `egm-comprehension` | Incluir expansão inline de cada sigla no primeiro uso no texto. |
| **ACT-15** | 🟢 **Nit** | Argumentos CLI de `strategy-record-tx` | `egm-codebase-details` | Documentar os argumentos da linha de comando (`--type`, `--btc`, `--price-brl`, `--fee`, `--exchange`, `--notes`). |
| **ACT-16** | 🟢 **Nit** | Esclarecimento de Relatório de DARF vs. SicalcWeb | `egm-comprehension` | Enfatizar que o sistema gera os dados mastigados de apuração para preenchimento no SicalcWeb, e não a guia oficial com código de barras via API governamental. |

---

## 4. Próximos Passos Recomendados

Para elevar a especificação técnica ao status de **Approved** e pronta para implementação de código:
1. Aplicar a resolução dos itens **ACT-01 a ACT-16** diretamente no documento [`docs/designs/bitcoin_national_execution_strategy.md`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md).
2. Atualizar o status no [`docs/designs/SITEMAP.md`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/SITEMAP.md) para `Approved`.
3. Proceder com a implementação do código seguindo as fases do plano detalhado.
