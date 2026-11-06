# Plano de Entrada e Saída de Bitcoin — Corretoras Nacionais (BitSignal Strategy)

* **Author:** @Guilherme
* **Date:** 2026-11-06
* **Status:** In Review (Brainstorming Phase)

## Overview

Extensão do sistema BitSignal para suportar um motor de estratégias executáveis de ciclo macro do Bitcoin adaptado para o ecossistema financeiro e tributário brasileiro. O sistema combina acumulação assimétrica em bear market balizada pela ATH ($126k) e métricas on-chain, distribuição gradual em bull market com trailing stops móveis (21w EMA e 50w SMA no fechamento de domingo às 21h BRT), otimização da isenção de R$ 35.000/mês para carteiras < 0.5 BTC com split intermensal e liquidação para renda fixa diária em Reais via PIX.

## Analysis

### 1. Inconsistência Aritmética das Tranches de Venda (Blocker)
* **Achado:** A soma original das tranches de saída (V1: 10%, V2: 15%, V3: 15%, V4: 20%, V5: 15%, Moonbag: 10%) totalizava apenas 85%, deixando 15% da posição sem regra definida de desova.
* **Resolução:** Normalizar a alocação sobre a posição base ($P_0$): V1 (10%), V2 (15%), V3 (15%), V4 (20%), V5 (20%), Moonbag (10% intocável), e V6 residual (10%) ou ajuste da tranche V5 para 20%.

### 2. Atrito de Execução: Domingo às 21h BRT e Limites do PIX
* **Achado:** O fechamento semanal às 21h de domingo coincide com:
  1. Horário de limite noturno do PIX no Banco Central (R$ 1.000 a R$ 5.000 por padrão nos apps bancários).
  2. Impossibilidade de aplicação imediata em grande parte dos fundos de renda fixa e CDBs tradicionais fora de horário comercial.
  3. Fadiga do investidor para transferir da cold storage e executar no livro BTC/BRL à noite no final do fim de semana.
* **Resolução:** 
  1. O BitSignal emitirá um **pré-alerta dominical às 18h BRT** caso o preço esteja a menos de 2% do gatilho ou stop.
  2. O runbook orienta a parametrização prévia de limites noturnos PIX nos bancos cadastrados e priorização de CDBs com liquidez imediata 24/7 (ex.: Caixinhas Nubank, Inter, etc.).
  3. O alerta das 21h01 BRT trará ordens e volumes pré-calculados em satoshis e reais.

### 3. Split Intermensal vs. Risco de Desvalorização do Ativo
* **Achado:** Para vendas entre R$ 35k e R$ 70k, reter parte do lote para o início do mês seguinte esperando isenção tributária expõe o investidor a quedas de mercado que frequentemente superam a alíquota de 15% de imposto.
* **Resolução:** Split condicional: o fracionamento só é permitido se o sinal ocorrer a partir do dia 25 do mês (espera máxima de 5 a 6 dias). Se o sinal ocorrer antes do dia 25, liquida-se o volume total imediatamente a mercado/limite e emite-se o DARF com recolhimento para o mês seguinte.

### 4. Integração Arquitetural com a Base do BitSignal
* **Achado:** O núcleo atual do BitSignal (`bitsignal.engine`, `bitsignal.ingestion`) é agnóstico em relação a moeda fiat e portfólios individuais, rodando em bateladas diárias às 00:05 UTC.
* **Resolução:** Manter o core desacoplado e criar o submódulo `bitsignal.strategy`:
  - `bitsignal/strategy/national_dca.py`: Lógica dos degraus C1-C4 e V1-V5.
  - `bitsignal/strategy/trailing_stops.py`: Avaliador da 21w EMA e 50w SMA no fechamento semanal (rodado nas segundas-feiras às 00:05 UTC / 21h05 BRT de domingo).
  - `bitsignal/strategy/tax_br.py`: Livro razão de custo médio ponderado, apuração de ganho de capital e geração de DARF (código 4600).
  - Nova tabela SQLite `strategy_state` e `portfolio_transactions` para rastreamento de lotes.

### 5. Padronização de Métricas Técnicas
* **Achado:** O termo "MVRV < 0" era tecnicamente ambíguo (a razão MVRV não atinge valores negativos).
* **Resolução:** Padronizado formalmente como `mvrv_z_score <= 0.0`. A média de 50 semanas (`50w SMA`) utiliza a base diária de 350 períodos (`sma_350`) já persistida no BitSignal.

## Goals vs. Non-Goals

### In-Scope Goals
* Especificação formal em `docs/designs/bitcoin_national_execution_strategy.md` detalhando todas as regras de entrada, saída, stops e tributação.
* Módulo `bitsignal.strategy` com suporte aos cálculos semanais de gatilho de degraus e trailing stops (21w EMA e 50w SMA).
* Motor tributário nacional (cálculo de custo médio ponderado, validação do teto de R$ 35k/mês e cálculo de DARF de 15%).
* Alertas estruturados no Telegram com runbooks passo a passo, discriminação de lotes em BTC e BRL e dados de PIX/destinação.
* Módulo de simulação/backtesting da estratégia nos ciclos anteriores comparando retorno líquido com buy & hold puro.

### Out-of-Scope Non-Goals
* Conexão direta via API de corretoras para envio de ordens automáticas sem supervisão humana (execução continuará manual e sob custódia soberana).
* Gestão de carteiras com posições maiores que 1.0 BTC (o plano é estritamente desenhado para posições menores que 0.5 BTC para viabilizar a otimização tributária).
* Negociação de contratos derivativos ou futuros de Bitcoin.
* Alocação em stablecoins (USDT/USDC); o destino de fiat é estritamente Reais (BRL) via PIX para renda fixa de liquidez diária.

## Alternatives Weighed

* **Abordagem Rejeitada 1: Venda em dólares via corretora internacional.**
  - *Motivo:* Regime da Lei 14.754/2023 tributa investimentos no exterior a 15% fixo sobre o ganho anual sem qualquer faixa de isenção de R$ 35k/mês.
* **Abordagem Rejeitada 2: Trailing stop móvel intrassemanal com disparos diários.**
  - *Motivo:* Gera falsos rompimentos (*wicks*) frequentes de alta frequência em mercados voláteis, tirando o investidor prematuramente de bull runs sólidas. O fechamento semanal aos domingos tem fidelidade estatística superior.
* **Abordagem Rejeitada 3: Acoplamento do motor fiscal diretamente dentro do `bitsignal/engine/normalizer.py`.**
  - *Motivo:* Poluiria o sentinela global macro com especificidades cambiais e tributárias de uma única jurisdição, quebrando a modularidade e reusabilidade da engine.

## Key Decisions & Staging for Next Steps

1. **Ajuste da Tranche V5:** Tranche V5 fixada em 20% (10% + 15% + 15% + 20% + 20% = 80% vendido em alta + 10% moonbag + 10% reserva residual/stop).
2. **Janela de Split Intermensal:** Split autorizado somente se o sinal ocorrer a partir do dia 25 do mês civil.
3. **Pré-Alerta Dominical:** Disparo às 18h BRT no Telegram para preparação prévia de liquidez e checagem de limites PIX bancários.
4. **Próxima Etapa:** Handoff para `/egm-draft` para elaboração da especificação detalhada de design e subsequente codificação dos módulos.
