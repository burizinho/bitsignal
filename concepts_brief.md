# BitSignal — Modelo de Ciclo Unificado e Painel Só de Leitura

* **Author:** @burizinho
* **Date:** 2026-11-08

## Overview

O BitSignal hoje tem não dois, mas três sistemas de decisão sobre o mesmo ciclo do Bitcoin:

1. o Composite Score 0–100 (`bitsignal/engine/normalizer.py`);
2. a escada de degraus por distância do ATH em `strategy/national_dca.py` + `weekly_evaluator.py` + `trailing_stops.py`, que só roda pela CLI às segundas-feiras;
3. uma cópia separada, só de preço e sem estado, em `ui/cycle_gauge.py`, que é a que o painel realmente mostra (e com números diferentes: V5 15% vs 20%, moonbag 10% vs 20%).

A proposta: transformar o BitSignal num painel Streamlit só de leitura, sem alertas e sem registro de transações, com uma única função pura que recebe o histórico de mercado e devolve, para cada semana fechada, fase + faixa + ação em percentual. O painel e o backtest chamam a mesma função. Nada é persistido no servidor; tudo é recalculado do histórico com cache.

Esta revisão foi feita por seis lentes (design, detalhes de código, zoom-out, compreensão, prontidão de implementação, estrutura). Todos os defeitos listados na hipótese foram verificados no código e confirmados, com nuances descritas em "Verificação dos defeitos". Nenhum foi rejeitado. A URL de fallback no GitHub (404) não pôde ser testada (sem rede).

Conclusão central: o critério de sucesso ("acertar 2017, 2021 e 2022") não é alcançável nem mensurável com o backtest atual. O topo de 2017 é matematicamente impossível de atingir (score máximo 47,5–62,5 contra limiar 80). Antes de mexer em faixas, é preciso (1) um backtest honesto com histórico real e (2) uma definição pré-registrada de "acerto".

Nota: as faixas aqui são crítica de design de modelo e hipóteses para o backtest testar, não recomendação financeira.

## Analysis

Severidades: **Bloqueante** (impede o objetivo ou gera sinal errado), **Maior** (distorce resultado ou confunde o usuário), **Menor**.

### 1. Verificação dos defeitos listados

| Defeito (hipótese) | Veredito | Evidência | Nuance |
|---|---|---|---|
| Pi Cycle Bottom invertido | Confirmado, mais grave | `engine/indicators.py:45` (`ema_150*0.745 <= sma_471`); `engine/normalizer.py:35-36` força 0 quando "fundo" ativo | Não é só o fundo: como o sub-score vira 0, o sinal de topo do Pi Cycle também some quase sempre. `tests/test_indicators.py:52-54` trava o comportamento errado. |
| Fallback on-chain com `timestamp=agora` | Confirmado, mais amplo | `ingestion.py:245-250` (2,10/1,05); também `:221` (Dune) e `:239` (mirror) carimbam `now`; `cli.py:134-141` idem para as demais métricas | `integrity.py:54-64` nunca vê dado vencido, com ou sem chave Dune. O ramo não-200 do mirror (`ingestion.py:232`) não loga nada. 404 não verificado. |
| `config.yaml` ignorado | Confirmado | Só `cli.py:59/195/320` carrega o arquivo, e só a seção `strategy` é usada (`weekly_evaluator.py:147-152`). Pesos em `normalizer.py:76-94`, de novo em `integrity.py:7-14`; histerese em `normalizer.py:139-169`; UI repete pesos/limites/ATH em `ui/app.py:168-172,187-195,221-222,244-247` | Caminho relativo ao diretório de trabalho (`cli.py:59`). `integrity.py:51` não repassa `fresh_hours/expired_hours`. |
| Candles abertos | Confirmado | `ingestion.py:56-68` ignora o close time; `cli.py:93-105` usa `iloc[-1]`; `weekly_evaluator.py:157,193` | O passo semanal roda segunda UTC (`cli.py:196`), então o "fechamento semanal" é a semana que acabou de abrir. yfinance também traz a barra do dia. |
| Backtest: MVRV/Puell sintéticos | Confirmado | `backtest/engine.py:104-108` | 65% do peso vira uma única variável (preço/SMA200w) contada três vezes. |
| Backtest: `sentinel_dd = bnh_dd*0.65` | Confirmado | `backtest/engine.py:195` | Constante, não simulação. |
| Backtest: `false_positive_count=0` | Confirmado | `backtest/engine.py:211` | |
| Backtest: `lead_days` errado | Confirmado | `backtest/engine.py:164` conta dias abaixo de 80 na janela | Janelas (`:153-155`) se estendem após o pico, então sinal pós-topo conta como acerto. |
| Backtest: SMA200w imputada 50 | Confirmado, mecanismo diferente | `engine.py:90` `rolling(1400)` → NaN até ~2018-07 → None (`:125`) → 50 (`normalizer.py:20-21`) | MVRV/Puell sintéticos herdam o NaN, então 65% do peso fica em 50. `cli.py:237` pede 2012, mas yfinance começa 2014-09-17: janelas de 2013/2015 vêm vazias. |
| Backtest: Hash Ribbon fixo | Confirmado | `backtest/engine.py:109-110` | |
| STOP_2 em acumulação; degraus nunca zerados | Confirmado com ressalva | `trailing_stops.py:45-47` sem checagem de fase; stops avaliados antes da fase (`weekly_evaluator.py:192` vs `:253`); executados via `SELECT DISTINCT stage` sem ciclo (`storage/db.py:344-349`) | Stops e vendas V exigem `current_btc_balance > 0.0001` (`weekly_evaluator.py:192,254`). Sem registro de transações, todo o lado de venda fica mudo, sem erro. O painel nunca mostra o estado dos stops (`ui/app.py:350-365` é texto estático). |
| `created_at` não atualizado; disco efêmero | Confirmado | `storage/db.py:130-145,162-172`; `ui/app.py:72-85` | `app.py:84-85` devolve "não vencido" em qualquer exceção. Cada widget reroda o script. Nenhum `st.cache_data` no projeto. `data/bitsignal.db` não está no `.gitignore`. |
| Binance bloqueada nos EUA; BTCBRL 5,80 | Confirmado no código (bloqueio não testável) | `ingestion.py:36-41,129-138` (retries antes do fallback); 5,80 em `weekly_evaluator.py:50`, `ui/app.py:247,499`, `cli.py:293`, `ui/cycle_gauge.py:11` | Fallback logado só em `debug` (`weekly_evaluator.py:37,49`). |

Defeitos adicionais encontrados:

- **Bloqueante, a confirmar no app publicado**: provável página em branco após a primeira interação. `streamlit_app.py:22` faz `import bitsignal.ui.app` e o módulo fica em `sys.modules`; o purge de `:14-19` só remove módulos de fora do repositório, então num rerun o import pode não executar nada. Correção: expor `main()` em `ui/app.py` e chamá-la explicitamente.
- **Maior**: indicadores diferentes no painel e no backtest. O painel usa RSI(14) e SMA(200) semanais (`cli.py:104-105`); o backtest usa RSI(98) e SMA(1400) diários (`backtest/engine.py:90-91`). Limiares calibrados no backtest não valem no painel.
- **Maior**: `ui/app.py:96,124` importa `bitsignal.cli.cmd_run_daily`, e `cli.py:12,44,48` importa alerts, tax_br e weekly_evaluator no nível do módulo. Apagar esses módulos quebra o painel.
- **Maior**: falha do Mempool aborta a execução inteira (`cli.py:86`, sem try).
- **Maior**: a escada V é documentada como % da posição inicial P0 (`national_dca.py:19-20`, `cycle_gauge.py:58,110`), mas aplicada sobre o saldo atual (`weekly_evaluator.py:307`). A saída real acumulada é ~58%, não 80%.
- **Maior**: a lógica do C4 (`national_dca.py:36-42`) só soma degraus não usados se o preço ainda estiver abaixo do limiar, o que contradiz "15% + não usados". C4 nunca é retornado por `cycle_gauge.get_cycle_stage_info`, embora apareça na tabela (`ui/app.py:444`).
- **Menor**: o Dune assume `rows[-1]` ordenado e quebra com campo nulo (`ingestion.py:216`). Se essa consulta já devolve a série diária, há histórico on-chain real disponível sem trocar de fonte. Vale verificar.
- **Menor**: histerese reavaliada contra a própria linha do dia em reruns intradiários (`storage/db.py:214`, `cli.py:147`). BUY_RECOVERY dura um dia só (`ingestion.py:183`). `requirements.txt` sem versões fixadas.

### 2. Fusão dos sistemas (lente a)

**Bloqueante.** As seis lentes convergem na mesma forma mínima: uma função pura

`avaliar(historico_semanal_fechado, cfg) -> DataFrame[fase, faixa, acao_pct, motivo, qualidade_dados]`

reexecutada sobre todo o histórico, sem estado gravado:

- **O score decide a fase** (ACUMULAR / MANTER / DISTRIBUIR), com histerese replayada sobre a série. A lógica de `normalizer.py:139-169` passa a receber limiares do config.
- **Dentro de ACUMULAR**, a queda a partir do ATH corrente (`cummax` dos fechamentos semanais) define a intensidade da compra.
- **Dentro de DISTRIBUIR**, os níveis do score definem a intensidade da venda. A escada V1–V5 por múltiplo de ATH é eliminada (ver seção 3).
- **Stop de tendência** só existe dentro de DISTRIBUIR, depois da primeira venda do ciclo, em candle semanal fechado. `trailing_stops.py` deixa de existir como módulo; a regra vira uma linha da tabela de faixas.
- **"Quais degraus já foram atingidos neste ciclo"** é derivado da trajetória do preço desde o início do ciclo, não do banco. O ciclo zera na transição DISTRIBUIR → ACUMULAR.

A lente zoom-out propõe ir além: reduzir o score de 6 para 2–3 indicadores (preço/SMA200w, cruzamento do Pi Cycle Top, MVRV Z só onde há histórico real). O motivo: cerca de 26 parâmetros livres (6 pesos, 12 limites em `normalizer.py:76-83`, 4 limiares e 4 bandas de histerese) contra 3 eventos rotulados permitem "acertar" qualquer coisa. Recomendação: manter os 6 indicadores na primeira versão, porque o usuário quer as fontes atuais, mas rodar o backtest também na variante de 3 indicadores e ficar com a mais simples se o resultado fora da amostra for equivalente.

### 3. Faixas de compra e venda: crítica e sugestão

**Crítica (Maior/Bloqueante):**

1. **Três tetos de venda incompatíveis.** O score vende no máximo 40% e nunca vende 60% (`config.yaml:59-67`). A escada V1–V5 soma 80% (`national_dca.py:66-84`), ou ~58% como aplicada de fato. A UI diz 75% e moonbag de 10% (`ui/cycle_gauge.py:29-39,438-450`, `ui/app.py:363`). STOP_2 vende tudo menos 20% (`config.yaml:82`, `weekly_evaluator.py:205`). Deve haver um teto, um piso nunca vendido e uma base de cálculo.
2. **ATH fixo de US$ 126k** (`config.yaml:78`, repetido em `ui/app.py:244`, `ui/cycle_gauge.py:10,225,331`). Envelhece a cada ciclo, e no backtest um ATH fixo é lookahead. Os múltiplos de pico sobre o ATH anterior caem a cada ciclo (2017 ~17x, 2021 ~3,5x, atual ~1,8x). Em 2021, com o ATH anterior de ~US$ 19,7k, V5 (2,5x ≈ US$ 49k) teria disparado por volta de fev/2021, meses antes do topo de novembro. No ciclo atual, V4/V5 podem nunca disparar. Venda por múltiplo de ATH não é estável entre ciclos.
3. **Compra enche cedo demais.** Em 2022 o fundo foi ~−77%. C3 (−65%) teria disparado por volta de junho/2022, e o preço ainda caiu cerca de 35%. Guardar 30–40% da reserva para uma confirmação (score ≤ 20 ou retomada acima da SMA50w).
4. **Stops e histerese competem.** STOP_2 manda vender 80% enquanto C0–C3 mandam comprar.
5. **"Reserva R" sem saldo conhecido.** Com a planilha externa, o painel não sabe R nem a posição. Toda ação deve ser em % de uma base declarada: compras em % da reserva do ciclo, vendas em % da posição no início do ciclo.
6. **C0 em 12 parcelas mensais** (`ui/cycle_gauge.py:143`) vs lote único (`national_dca.py:60`). Inconsistente, e torna "quanto de R sobrou" dependente do tempo.

**Sugestão de tabela** (hipótese para o backtest testar; todos os números vêm de um único bloco `bands:` no config; limiares congelados antes de rodar):

| Faixa | Fase | Condição (semana fechada) | Ação | % acumulado |
|---|---|---|---|---|
| C-DCA | ACUMULAR | score < 45 e queda ≥ 30% do ATH corrente | comprar 2,5% da reserva por mês, até 25% | até 25% da reserva |
| C1 | ACUMULAR | queda ≥ 50% e score < 35 | comprar 20% da reserva | 45% |
| C2 | ACUMULAR | score ≤ 20 (rearma > 25) ou queda ≥ 70% | comprar 25% da reserva | 70% |
| C3 | ACUMULAR | fechamento semanal > SMA50w depois de C1 ou C2 | comprar o restante (~30%) | 100% |
| Neutro | MANTER | score 35–75 e nenhuma condição acima | nada | — |
| D1 | DISTRIBUIR | score ≥ 75 (rearma < 70) | vender 10% da posição no início do ciclo | 10% |
| D2 | DISTRIBUIR | score ≥ 82 (rearma < 77) | vender 10% | 20% |
| D3 | DISTRIBUIR | score ≥ 88 | vender 15% | 35% |
| D4 | DISTRIBUIR | score ≥ 93 ou cruzamento real do Pi Cycle Top | vender 15% | 50% |
| Saída de tendência | DISTRIBUIR, após D1 | fechamento semanal < SMA50w | vender até o teto | 50% (teto) |
| Piso | sempre | — | nunca vender abaixo de 50% da posição do início do ciclo | — |
| Reinício | — | transição DISTRIBUIR → ACUMULAR | zera degraus atingidos | — |

**Ajuste depois do teste com dados reais (seção 4.1):** com os limites de normalização atuais, D1 (score ≥ 75) teria vendido 10% em maio/2017 a ~US$ 2.000 e em dez/2020 a ~US$ 27 mil. A tabela só faz sentido depois de recalibrar a normalização para que 75+ apareça perto do topo. Opções a testar no walk-forward:

- normalizar cada indicador pelo seu percentil histórico expansivo, em vez de limites fixos;
- subir os limites de topo (ex.: MVRV Z 7, preço/SMA200w 5, Puell 3,5) com decaimento por ciclo;
- exigir que o score fique acima do nível por N semanas, ou que o preço já esteja acima do ATH anterior, antes de cada venda.

Como o score não viu novembro/2021, a saída por tendência (SMA50w após D1) continua necessária, sabendo que ela vende longe do pico (~47% em 2021).

Comparação com a proposta mínima da lente zoom-out (rejeitada como padrão, mantida como variante de teste): fase só por preço/SMA200w (< 1,0 acumula; ≥ 3,5 ou Pi Cycle Top distribui), compras 40/30/30 da reserva por queda de 0/50/70%, vendas 15+15 com teto de 30–40%. É mais simples e tem menos parâmetros. Deve rodar lado a lado no backtest.

O que o backtest precisa mostrar para justificar a tabela, por ciclo (2017, 2021, 2022):

- preço médio de venda como % do pico;
- preço médio de compra como % do fundo;
- BTC final vs comprar e segurar;
- número de vendas falsas no meio da alta (ex.: 2019-06, 2024-03);
- o mesmo com todos os limiares deslocados ±5 pontos (sensibilidade).

Se o resultado mudar muito com ±5, a faixa está sobreajustada.

### 4. Backtest honesto com dados gratuitos (lente c)

- **Bloqueante no backtest atual — o topo de 2017 é impossível com yfinance.** Com SMA200w, MVRV e Puell em 50 e Hash Ribbon fixo, o score máximo em 2017 é 47,5 (62,5 com o Pi corrigido), abaixo de 80.
- **Fonte histórica escolhida (verificada em 2026-11-08): CoinMetrics Community API, sem chave.** Endpoint `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&frequency=1d`, métricas `PriceUSD`, `CapMrktCurUSD`, `CapMVRVCur`, `IssTotUSD`, `HashRate`. Todas vêm desde 2010-07-18 (5.957 dias até 2026-11-07, defasagem de 1 dia). Uma única fonte cobre os seis indicadores.
  - `CapRealUSD` é bloqueada no plano gratuito ("not available with supplied credentials"). O realized cap sai de `CapMrktCurUSD / CapMVRVCur`.
  - Blockchain.com charts também responde (preço e miners-revenue desde 2009), como reserva. Não usar miners-revenue para Puell (inclui taxas).
  - Congelar o dataset como CSV versionado (ex.: `data/historical/btc_coinmetrics.csv`, com data de coleta); o CI roda sem rede.
- **MVRV Z real**: (MC − RC) / desvio-padrão expansivo de MC. O desvio sobre o histórico inteiro é lookahead.
- **Puell**: `IssTotUSD / média de 365 dias de IssTotUSD`.
- **Hash Ribbon**: SMA30/SMA60 de `HashRate`.

#### 4.1 Teste rápido com dados reais (CoinMetrics, Pi Cycle corrigido, pesos e limites atuais)

Script exploratório, fora do repositório; números aproximados, servem para orientar, não para validar.

| Evento | Score no período | Primeiro dia ≥ 80 | Preço nesse dia vs pico |
|---|---|---|---|
| Topo 2013 (dez) | máx 85,0 | 2013-03-26 | 7% do pico |
| Topo 2017 (17/12) | máx 95,0, no próprio dia do pico | 2017-05-23 | 11% do pico (207 dias antes) |
| Topo 2021 abril | máx 93,4 | 2021-01-02 | 47% do pico de novembro |
| Topo 2021 novembro | máx 65,5 — **não atinge 80** | — | — |
| Fundo 2022 | mín 1,1 | ≤ 20 desde 2022-05-06 | US$ 36 mil (fundo US$ 15,8 mil) |
| Hoje (2026-11-07) | 18,5 | ≤ 20 desde 2025-11-20 | US$ 75,7 mil; MVRV Z 0,71; Puell 0,92; preço/SMA200w 1,12 |

Conclusões:

1. **Com dados reais, o score acerta a direção nos três eventos do critério** (2017 e abril/2021 acima de 90; 2022 abaixo de 20). O defeito do Pi Cycle sozinho mudava muito: a fórmula atual marca "fundo" em 75% dos dias desde 2019; a corrigida, em 13%.
2. **Mas o score chega às faixas de venda cedo demais.** O nível 80 aparece 200–300 dias antes do pico, a 7–47% do preço do pico. Os limites de normalização (MVRV Z 5, preço/SMA200w 3,5, Puell 2,2) saturam no começo da alta. Uma venda por "score ≥ 80" teria vendido 2017 a ~US$ 2.300.
3. **O topo de novembro/2021 não é visto pelo score** (máx 65,5). Precisa de um gatilho de tendência ou de preço para ser pego.
4. **Uma saída por tendência simples também é fraca:** "score ≥ 80 nas últimas 17 semanas + fechamento semanal < EMA21w" vendeu 2017 a 42% do pico (fev/2018) e 2021 a 68% (mai/2021). A mesma regra deu 10 semanas seguidas de "venda" em mai–jul/2021, antes de o preço subir mais 80%.
5. **Do lado da compra o score funciona razoavelmente como zona,** mas entra cedo. Em 2022 marcou ≤ 20 a US$ 36 mil, e o fundo foi US$ 15,8 mil. Isso reforça as compras em parcelas ao longo de meses, não em lote.

Consequência para o critério de sucesso: "score ≥ 80 em algum dia da janela" é fácil de passar e não diz nada. O critério tem de medir **o preço médio em que cada faixa venderia ou compraria** em relação ao pico ou fundo (seção 3).
- **Tensão com a fonte do painel** (Maior): o painel continua com Dune ou o fallback fixo. Os níveis do Dune podem diferir do CoinMetrics. É preciso um teste de paridade numa janela comum (ex.: |ΔZ| < 0,3). Quando o painel cair no 2,10/1,05 fixo, o indicador deve ser tratado como ausente, não como valor real.
- **Sem imputação**: a avaliação começa na primeira data em que todos os insumos estão aquecidos. Ciclos anteriores aparecem como "NÃO AVALIÁVEL", não como "errou". Escolher e documentar uma política para insumo ausente num dia: pular o dia ou renormalizar os pesos.
- **Uma só função de indicadores** para painel e backtest, sobre semanas fechadas (W-SUN), com forward-fill para dias.
- **Definição de acerto, pré-registrada** (Bloqueante):
  - picos e fundos em fechamento diário: 2017-12-17, 2021-11-08, 2022-11-21;
  - topo acertado = primeiro sinal de DISTRIBUIR em [pico − 90d, pico + 7d] com preço ≥ 75% do pico;
  - fundo acertado = sinal de ACUMULAR intensa (C1/C2) em [fundo − 60d, fundo + 30d] com preço ≤ 1,3× o fundo;
  - `lead_days = data_pico − data_primeiro_sinal`.
  - Decidir antes se abril/2021 conta como acerto ou falso positivo; MVRV Z e Pi Cycle atingiram o pico em abril, e o score provavelmente não marca novembro.
  - Decidir se o fundo de 2022 é junho ou novembro.
- **Falsos positivos** por episódio (entrada em estado), não por dia. Uma venda é falsa se não houver queda ≥ 30% em 180 dias; uma compra é falsa se o preço ainda cair ≥ 30%.
- **Simulação real de patrimônio** no lugar de `bnh_dd*0.65`.
- **Sobreajuste** (Maior): 3 eventos. Fazer walk-forward: calibrar com ciclos até 2017 (2013/2015 com histórico longo), congelar, avaliar 2021/2022 fora da amostra. Os limites atuais de normalização (`normalizer.py:76-82`) já foram escolhidos olhando o passado; declarar isso.
- **Exibição** (lente de compreensão): gráfico de preço em escala log com faixas sombreadas e os três eventos marcados, mais uma tabela por evento (data do sinal, lead, preço vs extremo, % vendido/comprado até ali). Marcar períodos com dado ausente.
- **Testes novos**:
  - tabela-verdade do Pi Cycle;
  - filtro de candle fechado;
  - paridade de indicadores entre painel e backtest;
  - ausência de lookahead (truncar em t não muda saídas ≤ t);
  - MVRV Z expansivo;
  - não imputação;
  - calculadoras de acerto, lead e falso positivo em séries sintéticas;
  - ATH corrente e reinício de ciclo;
  - config lido = config usado;
  - golden file sobre o CSV congelado.

### 5. O que apagar (lente d)

**Maior — a ordem importa.** Cerca de 1.750 linhas, ~48% das 3.672 do pacote:

- `bitsignal/alerts/` (236 linhas). Importado por `cli.py:12`, `tests/test_alerts.py`, `tests/test_strategy_weekly_evaluator.py:8`. A UI também lê a tabela `alert_dispatches` (`ui/app.py:61,233-235`).
- `strategy/tax_br.py` (157). Importado por `ui/app.py:36`, `cli.py:44`, `weekly_evaluator.py:23`.
- `strategy/weekly_evaluator.py` (353), incluindo o runbook PIX/DARF e `fetch_btc_brl_spot`.
- `strategy/trailing_stops.py` e `strategy/national_dca.py`: as regras viram linhas da tabela de faixas.
- Em `strategy/models.py`: `PortfolioTransaction`, `PortfolioSummary`, `TaxExecutionPlan`, `TaxStatus`, `StrategyRunbook`. Atenção: `storage/db.py:8` importa esses tipos.
- `storage/db.py` (349) inteiro, depois de tirar a histerese do banco.
- Em `cli.py`: os comandos `strategy-*` (`:254-379`), alertas (`:176-222`), `db-init`.
- Em `ui/app.py`: a aba de estratégia (`:368-529`), o log de alertas e as entradas de R$/BTC (`:242-247`).
- Testes: `test_alerts`, `test_strategy_tax_br`, `test_strategy_storage`, `test_strategy_weekly_evaluator`, `test_storage`.
- Do config: `alerting` (vira `bands`), `bank_night_limit`, `default_exchange`, `total_reserve_brl`.
- `ui/cycle_gauge.py` (453): manter só o desenho, recebendo a tabela de faixas; hoje repete ~40 constantes.

Ordem segura: (1) extrair a função pura e fazer `ui/app.py` parar de importar `cli.py`; (2) apagar `weekly_evaluator`, `tax_br`, `alerts`; (3) apagar funções/tabelas do `db.py` e tipos de `strategy/models.py`; (4) garantir que `cli.py` e `__main__.py` ainda importam.

Reaproveitar:

- `engine/indicators.py` (com o Pi corrigido);
- `normalize_linear`/`clamp`;
- `evaluate_hysteresis_state` (com limiares injetados);
- os fetchers de `ingestion.py`;
- o cálculo de Hash Ribbon (`ingestion.py:166-186`) como função pura compartilhada;
- o laço vetorizado do backtest, sem `apply`/`iterrows` (`backtest/engine.py:93-101,121`);
- os desenhos de `cycle_gauge`.

### 6. Painel só de leitura e honestidade dos dados

- **Bloqueante**: o painel mostra valores substitutos como reais. MVRV/Puell fixos, câmbio 5,80 em `ui/app.py:247` e preço que vira US$ 95.000 quando é 0 (`ui/app.py:249`) aparecem sem aviso, e não há campo de fonte (`OnChainSnapshot`, storage). Gravar `fonte`/`data_do_dado` por insumo. Mostrar um selo ("real (Dune)", "estimado: valor fixo", "candle aberto"). Se algum insumo do score estiver estimado, o veredito vira "indicativo".
- **Bloqueante**: as abas não se conversam. A aba 1 mostra o score sem ação; a aba 2 dá ação só por preço; os stops nunca são calculados na UI. Substituir por uma linha única no topo: "Semana fechada em dd/mm: COMPRAR X% da reserva | VENDER Y% da posição | NADA — motivo: fase + faixa; dados: OK/estimados", com os insumos abaixo.
- **Maior**: mostrar só percentuais e o acumulado do ciclo. Renomear "Executado" para "Atingido". Remover quantidades em BTC/R$ inventadas (`ui/app.py:242-247,282-297`).
- **Maior**: glossário curto (reserva, posição base, fase, histerese, piso) e a interface toda em português. Hoje a aba 1 está em inglês, e `ui/app.py:132` manda um usuário que só visualiza rodar comandos de CLI.
- **Menor**: "Última atualização" mostra a gravação no banco (`ui/app.py:118-120`). Mostrar "último fechamento semanal usado".

### 7. Streamlit Community Cloud (lente e)

- **Maior — disco efêmero.** Não persistir nada. Histerese, ATH corrente e faixas são replayados do histórico. O SQLite só gera um histórico curto e enganoso (`ui/app.py:59,212`). O único arquivo versionado é o CSV congelado do backtest.
- **Maior — custo de refresh.** `@st.cache_data(ttl=3600)` para preço, `ttl` de 6–12h para on-chain, e cache separado por fonte. A partida a frio custa uma busca de ~3–4 mil candles diários (segundos); o cálculo vetorizado leva milissegundos. O cache deve absorver erro/limite do yfinance e mostrar o último valor bom com a idade. Elimina o laço do `created_at`.
- **Maior — região EUA.** No Cloud, usar yfinance como fonte primária via variável de ambiente e não tentar a Binance (hoje há 3 retries por chamada antes do fallback). `data-api.binance.vision` pode ser testada. Descartar a barra parcial do yfinance. Sem quantidades em R$, o BTCBRL deixa de ser necessário. Se ficar para exibição, usar `BRL=X` do yfinance com selo.
- **Menor**: fixar versões de `streamlit` e `yfinance` em `requirements.txt`.

## Goals vs. Non-Goals

**Goals**

- Um único modelo de ciclo (função pura, sem estado) usado pelo painel e pelo backtest.
- Painel Streamlit só de leitura, com uma linha de ação semanal em percentuais e a origem e data de cada dado visíveis.
- Corrigir os erros de cálculo: Pi Cycle, candles abertos, config ignorado (um `config.py` com caminho a partir do pacote, validado, sem defaults numéricos espalhados), refresh em laço, timestamps falsos.
- Backtest honesto: histórico real e longo, sem dado sintético nem imputação, critério de acerto pré-registrado, falsos positivos e simulação de patrimônio reais, walk-forward e teste de sensibilidade.
- Uma tabela de faixas com um teto, um piso, uma base de cálculo e ATH corrente.

**Non-Goals**

- Alertas (Telegram ou outros).
- Registro de compras/vendas, saldo, imposto (DARF), runbook bancário.
- Trocar a fonte on-chain do painel (Dune + fallback continuam). O backtest usa fonte histórica separada.
- Persistência no servidor.
- Otimizar faixas para maximizar retorno no passado. As faixas são congeladas antes do teste.
- Aconselhamento financeiro pessoal.

## Alternatives Weighed

| Alternativa | Decisão | Motivo |
|---|---|---|
| Manter os dois sistemas lado a lado na UI | Rejeitada | Já geram ordens contraditórias (STOP_2 vende 80% enquanto C0 compra) e números divergentes (moonbag 10%/20%/60%). |
| Score como portão de fase + degraus por ATH como intensidade de compra | Escolhida | Menor mudança que elimina o conflito; reaproveita histerese e a ideia da escada de compra. |
| Manter V1–V5 por múltiplo de ATH para vendas | Rejeitada | Múltiplos de pico caem a cada ciclo (17x → 3,5x → 1,8x); com ATH fixo, V5 dispararia meses antes do topo de 2021 e talvez nunca no ciclo atual. |
| Descartar o score e usar só preço/ATH | Rejeitada como padrão | Não distingue topo de meio de alta; o usuário quer manter MVRV/Puell. Fica como variante de comparação. |
| Score reduzido a 2–3 indicadores | Variante a testar | Menos parâmetros para 3 eventos; adotar se o resultado fora da amostra for equivalente. |
| Persistir em SQLite / banco externo | Rejeitada | Disco efêmero; todo estado é derivável do histórico; banco externo adiciona custo e segredo. |
| Manter MVRV/Puell sintéticos no backtest | Rejeitada | Conta a mesma variável três vezes; não testa o modelo que o painel usa. |
| Imputar 50 para dados ausentes | Rejeitada | Torna 2017 inatingível e esconde falta de dado; usar "não avaliável". |
| ATH fixo em config | Rejeitada | Envelhece e é lookahead no backtest; usar `cummax`, com override opcional. |
| Flag `model: legacy|unified` para rollback | Rejeitada como desnecessária após S6 | Útil só durante a transição; sem registro de transações, voltar é um revert de commit. |

## Key Decisions & Staging for Next Steps

Decisões que precisam ser tomadas antes do PRD:

1. Definição de acerto (janelas, tolerância de preço, abril vs novembro/2021, junho vs novembro/2022) e orçamento de falsos positivos.
2. Base das porcentagens: compras em % da reserva do ciclo, vendas em % da posição no início do ciclo; teto único (proposto 50%) e piso único.
3. Regra do ATH corrente e do reinício de ciclo.
4. Precedência quando sinais conflitam (proposta: fase manda; stop só dentro de DISTRIBUIR).
5. Política de insumo ausente no painel: tratar como ausente e renormalizar os pesos, ou marcar o veredito como "indicativo".
6. ~~Fonte histórica do backtest~~ **Decidido:** CoinMetrics Community (verificada; sem chave; desde 2010). Falta o teste de paridade com o Dune.
7. Como recalibrar a normalização para que as faixas de venda disparem perto do topo (percentil expansivo, limites decrescentes por ciclo ou confirmação por tempo). Ver 4.1.
8. Se vale usar a CoinMetrics também como fallback do painel no lugar dos valores fixos 2,10/1,05. O usuário pediu para manter a fonte on-chain atual; esta opção só substitui o valor inventado, não o Dune.

Plano em etapas, da menor e mais segura para a maior:

- **S0** — Verificar no app publicado se a página fica em branco após interagir; se sim, `main()` explícito em `ui/app.py`.
- **S1** — Corrigir o Pi Cycle e seu teste (`indicators.py:45`, `tests/test_indicators.py:52-54`); filtrar candles abertos (diário e semanal); atualizar `created_at` no upsert como paliativo.
- **S2** — `config.py` único (caminho via `Path(__file__)`, validação de pesos e ordem das faixas). Remover constantes duplicadas de `normalizer.py`, `integrity.py`, `ui/app.py`, `ui/cycle_gauge.py`.
- **S3** — Timestamps honestos e campo `fonte` por insumo; selos na UI; fallback logado em WARNING; try em volta do Mempool.
- **S4** — Módulo único de indicadores semanais usado por painel e backtest; `ui/app.py` deixa de importar `cli.py`.
- **S5** — Coletor histórico da CoinMetrics Community que gera o CSV congelado (`PriceUSD`, `CapMrktCurUSD`, `CapMVRVCur`, `IssTotUSD`, `HashRate`, desde 2010-07-18), com paginação por `next_page_url`.
- **S6** — Reescrever o backtest: sem sintéticos e sem imputação, início na primeira data válida, calculadoras de acerto/lead/falso positivo, simulação de patrimônio; pré-registrar as definições e rodar walk-forward e sensibilidade ±5.
- **S7** — Implementar a função `avaliar()` com a tabela de faixas da seção 3 (e as variantes de comparação). Ajustar só o que o walk-forward justificar.
- **S8** — Painel só de leitura: linha de ação semanal, tabela de faixas única, glossário, `st.cache_data`, yfinance primário no Cloud; remover SQLite.
- **S9** — Apagar código morto na ordem da seção 5, em commit separado; fixar versões em `requirements.txt`.
