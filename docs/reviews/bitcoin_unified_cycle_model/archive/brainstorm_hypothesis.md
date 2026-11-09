# Hipótese de brainstorm: BitSignal — modelo de ciclo unificado e painel só de leitura

Data: 2026-11-08 · Repositório: `D:/Projetos Gui/BitSignal` (commit 393b837)

## Situação atual (como o usuário usa)

- O app roda no Streamlit Community Cloud (`streamlit_app.py` → `bitsignal/ui/app.py`). O usuário só olha o painel.
- O usuário NÃO quer alertas de Telegram e NÃO quer registrar compras/vendas pelo painel: vai manter os registros numa planilha própria.
- Os dados on-chain (MVRV Z, Puell) devem ficar com as fontes atuais (Dune se houver chave, senão fallback). Não é escopo trocar a fonte.
- Critério de sucesso: um backtest honesto que acerte os topos de 2017 e 2021 e o fundo de 2022.
- O usuário quer que os dois sistemas de decisão que hoje coexistem virem um só, e quer sugestões e crítica das faixas de compra e venda.

## Os dois sistemas que hoje coexistem

1. **Composite Score 0–100** (`bitsignal/engine/normalizer.py`): 6 indicadores ponderados (MVRV Z 25%, preço/SMA200w 20%, Puell 20%, Pi Cycle 15%, RSI semanal 10%, Hash Ribbon 10%). Faixas: venda 80/85/90 (20%/30%/40% acumulado, 60% nunca vendido), compra (DCA) ≤ 20, com histerese.
2. **Degraus por distância do ATH** (`bitsignal/strategy/national_dca.py`, `weekly_evaluator.py`, `trailing_stops.py`, `ui/cycle_gauge.py`): ATH fixo em `config.yaml` (US$ 126.000). Compra C0 −30% (30% da reserva R), C1 −45% (15%), C2 −55% (20%), C3 −65% ou MVRV ≤ 0 (20%), C4 fechamento > SMA50w (15% + não usados). Venda V1 novo ATH (10%), V2 1,3× (15%), V3 1,6× (15%), V4 2,0× (20%), V5 2,5× (20%). Stops semanais: abaixo da EMA21w vende 50%; abaixo da SMA50w vende tudo menos moonbag de 20%. O Composite Score não participa dessas decisões.

## Defeitos já confirmados no código (para os revisores verificarem)

- `engine/indicators.py:44` Pi Cycle Bottom invertido: testa `ema_150*0.745 <= sma_471` (quase sempre verdadeiro) em vez de `ema_150 < sma_471*0.745`. Resultado: Pi Cycle fica em 0 (15% do score).
- `ingestion.py`: a URL de fallback no GitHub retorna 404. Sem chave Dune, MVRV=2,10 e Puell=1,05 fixos são usados com `timestamp=agora`, então o circuit breaker de `integrity.py` nunca dispara. (Manter a fonte, mas a honestidade de exibição está em aberto.)
- `config.yaml` (pesos, limites, histerese) não é lido pelo normalizer, integrity nem histerese; valores duplicados no código.
- O último candle diário e o semanal da Binance ainda estão abertos quando o pipeline roda (RSI semanal, stops e OHLC usam candle parcial).
- `backtest/engine.py`: MVRV e Puell sintéticos derivados da própria razão SMA200w (dupla contagem); `sentinel_dd = bnh_dd*0.65` fixo; `false_positive_count=0` fixo; `lead_days` calculado errado; yfinance BTC-USD começa em 2014-09, a SMA200w (1400 dias) só existe a partir de ~2018 e é imputada como 50 antes disso; Hash Ribbon fixo em NORMAL.
- `trailing_stops.py`: STOP_2 dispara sempre que o fechamento semanal < SMA50w, inclusive em fase de ACUMULAÇÃO (manda vender 80% enquanto o outro bloco manda comprar). Degraus executados nunca são zerados entre ciclos.
- `ui/app.py` + `storage/db.py`: o upsert não atualiza `created_at`, então depois de 1h todo carregamento de página roda o pipeline inteiro de novo. No Streamlit Cloud o disco é efêmero: o histórico em SQLite volta ao estado do git a cada reinício.
- Streamlit Cloud roda nos EUA; `api.binance.com` costuma ser bloqueada lá → fallback yfinance; BTCBRL cai para câmbio com default fixo R$ 5,80.

## Hipótese ancorada

Transformar o BitSignal num painel Streamlit só de leitura, sem alertas e sem registro de transações, com um único modelo de ciclo que funde o Composite Score e os degraus por ATH (o score decide a fase e a intensidade; o preço/ATH define os degraus), corrigindo os bugs de cálculo (Pi Cycle, candles abertos, config ignorado, refresh) e com um backtest honesto que precisa acertar os topos de 2017/2021 e o fundo de 2022 — usado também para sugerir e criticar as faixas de compra e venda.

## Perguntas que a revisão deve atacar

1. Qual a forma mais simples de fundir os dois sistemas sem criar um terceiro? (Score como portão de fase? Degraus como escala dentro da fase? Descartar um deles?)
2. A estrutura de faixas atual é coerente? (venda máxima 40% vs escada V1–V5 que soma 80%; ATH fixo de US$ 126k; stops semanais vs histerese; "reserva R" para compras sem saldo conhecido, já que o registro vai para planilha.)
3. Como fazer um backtest honesto com dados gratuitos para 2017/2021/2022, sem MVRV/Puell sintéticos, e o que fazer quando faltam dados antigos?
4. Sem registro de transações, o que o painel deve mostrar (percentuais em vez de quantidades em BTC/R$)? O que pode ser apagado (alerts/, strategy/tax_br, tabelas de portfólio)?
5. Persistência no Streamlit Cloud: precisa persistir algo, ou dá para recalcular tudo do histórico de preços a cada carga com cache?
