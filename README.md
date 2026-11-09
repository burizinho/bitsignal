# BitSignal — modelo de ciclo unificado do Bitcoin

Painel **só de leitura** que mostra, para a última semana fechada, em que fase do ciclo o Bitcoin está
e quanto o modelo sugere ter vendido ou comprado até ali. Não envia alertas, não registra operações e
não faz análise fiscal: os resultados são brutos, e as operações reais ficam na planilha do usuário.

> **Status: experimental.** O painel mostra o **modelo v2** (Fase 3), que é o v1 mais uma regra: no
> reinício de ciclo, comprar com todo o caixa disponível. O v1 foi avaliado uma única vez e **não**
> passou em todos os critérios (detalhes em [Validação](#validação)); o v2 só é avaliado com dados
> futuros. Os percentuais do painel são referências do modelo, não ordens.

O design completo está em [docs/designs/bitcoin_unified_cycle_model.md](docs/designs/bitcoin_unified_cycle_model.md).

## O que o painel mostra

* **Linha do topo:** semana fechada, fase (ACUMULAR, MANTER ou DISTRIBUIR), venda acumulada-alvo no
  ciclo (% da posição-base), compra da semana (% da reserva-base) e o motivo.
* **Insumos:** valor e estado de cada indicador (presente, aquecimento ou ausente) e o score.
* **Detector de reversão:** armamento, nível atual e episódios.
* **Ciclo:** gráfico de preço com as fases e o registro de eventos do ciclo atual.
* **Conferência com o Dune** (opcional): compara o último dado do CoinMetrics com uma consulta do Dune.
* **Backtest:** curvas de patrimônio do modelo, de comprar e segurar e do DCA uniforme, com os
  critérios gravados.

Se os dados estiverem desatualizados (mais de 9 dias) ou a fonte estiver fora do ar, o painel não
mostra veredito e oferece "Tentar de novo".

## O modelo

Tudo roda sobre fechamentos semanais (domingo, UTC). Uma semana só entra depois de fechada. Nenhum
dado ausente é preenchido.

1. **Score de valuation (0–100):** média ponderada de MVRV Z (25%), preço/SMA200 semanas (20%),
   Puell (20%), Pi Cycle (15%), RSI semanal de 14 (10%) e Hash Ribbon (10%), cada um normalizado
   entre um mínimo e um máximo fixos. MVRV e Puell são obrigatórios; se faltar mais de 20% do peso, o
   score fica indisponível. Com insumos ausentes, o score vira um intervalo (`score_min`–`score_max`).
2. **Escada de venda:** `score_min` ≥ 85 / 90 / 93 → venda acumulada de 5% / 15% / 30% da
   posição-base.
3. **Detector de reversão** (independente do score): fica armado por 52 semanas depois de uma nova
   máxima histórica. Dispara com 2 fechamentos abaixo da SMA30 semanas e preço ≤ 80% da máxima de 52
   semanas. Níveis: 10% no disparo, 25% com 2 fechamentos abaixo da SMA50 semanas, 50% quando, além
   disso, o preço chega a ≤ 60% da máxima de 52 semanas.
4. **Catraca e teto:** a venda acumulada-alvo só sobe dentro do ciclo:
   `min(50%, max(catraca, escada, detector))`. Os outros 50% da posição-base nunca são vendidos.
5. **Ciclo e reinício em duas etapas:** o reinício é armado com `score_max` ≤ 20 por 2 semanas e só
   vale com `score_min` ≥ 30 por 2 semanas e o detector em 0. Aí começa um ciclo novo e a catraca
   volta a 0.
6. **Compras (DCA pelo score):** 2% da reserva-base por semana com `score_max` ≤ 20, 4% com ≤ 10.
7. **Compra no reinício (só no v2):** na semana em que um ciclo novo começa, comprar com todo o caixa
   disponível, incluindo o produto das vendas do ciclo anterior. No v1 esse caixa ficava parado.

| Modelo | Config | Congelado em | Avaliação |
| :--- | :--- | :--- | :--- |
| v2 (painel) | [config/config.yaml](config/config.yaml) | [params_v2_2026-11-09.yaml](config/frozen/params_v2_2026-11-09.yaml) | só com dados futuros (`forward-eval`) |
| v1 | [config/config_v1.yaml](config/config_v1.yaml) | [params_2026-11-09.yaml](config/frozen/params_2026-11-09.yaml) | 2019+, gravada (não aprovado) |

## Fontes de dados

* **CoinMetrics Community API** (sem chave, licença CC BY-NC 4.0): fonte única dos insumos do modelo
  (`PriceUSD`, `CapMrktCurUSD`, `CapMVRVCur`, `IssTotUSD`, `HashRate`). O histórico usado pelo backtest
  fica congelado em `data/historical/btc_coinmetrics.csv`, com o hash conferido em cada leitura.
* **Dune** (opcional): só conferência. Configure `DUNE_API_KEY` e `DUNE_QUERY_ID` no `.env` (veja
  `.env.example`). Sem eles, a conferência é omitida e o modelo funciona igual.
* **Yahoo Finance** (yfinance): só o preço à vista exibido no painel; não entra no modelo.

## Instalação

Requer Python 3.11 ou mais novo.

```bash
pip install -e ".[ui,dev]"
```

O `requirements.txt` (usado pelo Streamlit Cloud) instala `-e .[ui]`.

## Comandos

| Comando | O que faz |
| :--- | :--- |
| `bitsignal ui` | Abre o painel (`streamlit run streamlit_app.py`). |
| `bitsignal evaluate` | Busca os dados no CoinMetrics e imprime o veredito da última semana fechada. |
| `bitsignal backtest` | Backtest offline na janela de calibração (até 2018-12-31), sem critérios. |
| `bitsignal backtest --window development` | Janela de desenvolvimento (2019+): mostra os critérios gravados ao lado do recálculo. Exige parâmetros congelados com o mesmo `model_hash`. |
| `bitsignal backtest --variants [--window development]` | Fase 2: o modelo padrão e as variantes de comparação lado a lado. Só diagnóstico sobre dados já vistos; nunca grava nada. |
| `bitsignal record-verdict [--config …]` | Grava o veredito da última semana fechada no registro semanal do modelo (veja abaixo). |
| `bitsignal forward-eval` | Avaliação do v2 com dados futuros (Fase 3): v2 contra v1, comprar e segurar e DCA uniforme desde o congelamento do v2, mais a comparação com o `minimal` (não é critério). Só exibe. |
| `bitsignal fetch-history` | Baixa o histórico do CoinMetrics e grava um novo CSV congelado. |
| `bitsignal freeze-params` | Congela os parâmetros num arquivo novo (recusa se os testes técnicos falharem ou se o arquivo existir). |

`backtest --window development --record` grava a avaliação uma única vez e já foi usado; rodar de novo
é recusado.

## Validação

* **Janela de calibração:** até 2018-12-31. É onde os parâmetros podem ser examinados.
* **Janela de desenvolvimento (2019+):** de 2019 até o congelamento. É validação histórica feita depois
  de ver esses dados, **não** uma amostra independente. Os critérios foram gravados uma vez, no arquivo
  congelado.

Critérios (Q1) e resultado gravado, rebaseados em 2019-01-01:

| Critério | Meta | Resultado | Passou |
| :--- | :--- | :--- | :--- |
| Patrimônio final vs. comprar e segurar | ≥ 0,90 | 0,325 | Não |
| Melhora da queda máxima vs. comprar e segurar | ≥ 10 p.p. | 31,35 p.p. | Sim |
| Patrimônio final vs. DCA uniforme completo | ≥ 1,00 | 1,016 | Sim |

Por isso o painel mostra o selo "Experimental". Os parâmetros não foram recalibrados depois da
avaliação; mudar qualquer um deles exige um novo design e um novo congelamento.

## Registro semanal (validação com dados futuros)

A janela 2019+ já foi vista, então nenhuma avaliação feita nela é independente. Para juntar
evidência que não seja retrospectiva, o workflow `.github/workflows/weekly-verdict.yml` roda toda
segunda e terça às 12:00 UTC, executa `bitsignal record-verdict` para cada modelo e commita uma
linha por semana fechada em `data/verdicts/weekly_verdicts.csv` (v1),
`data/verdicts/weekly_verdicts_v2.csv` (v2) e `data/verdicts/weekly_verdicts_minimal.csv` (o modelo
`minimal`, braço de comparação pré-registrado em 2026-11-09; colunas de score vazias). Um arquivo nunca mistura modelos: o comando recusa
gravar se o `model_hash` não for o do arquivo. Na semana de reinício do v2, `buy_pct` vale `all_cash`.
Colunas:

* semana, data da gravação, fase, venda acumulada-alvo, compra, score (e intervalo), estado do
  score, nível do detector, reinício pendente, início do ciclo, preço, `data_as_of`, `model_hash`
  e motivo.
* Uma semana já gravada nunca é reescrita, mesmo que o CoinMetrics revise os dados depois.
* Com dados desatualizados ou fonte fora do ar, o comando falha e não grava nada; a falha aparece
  na aba Actions do GitHub.

Não é registro das suas operações nem envia alerta: é só o histórico do que o modelo disse, na
hora em que disse.

## Fases

* **Fase 1 (implementada):** modelo único, painel só de leitura, backtest essencial com dois
  benchmarks e congelamento.
* **Fase 3 (implementada, em avaliação):** modelo v2 com compra no reinício
  ([design](docs/designs/bitcoin_cycle_phase3_reinvestment.md)). A janela de avaliação vai do
  congelamento (2026-11-09) até o primeiro reinício depois de uma fase DISTRIBUIR, ou 2030-12-31.
* **Fase 2 (implementada, diagnóstico):** variantes de comparação no backtest
  ([design e resultados](docs/designs/bitcoin_cycle_phase2_variants.md)). Não substituem o modelo
  padrão.

## Desenvolvimento

```bash
ruff check bitsignal tests
pytest -q --cov=bitsignal --cov-fail-under=70
pytest -q --cov=bitsignal/engine --cov=bitsignal/backtest --cov-fail-under=90
```

Os testes rodam sem rede. O CI (`.github/workflows/ci.yml`) roda os mesmos comandos em Python 3.11.
