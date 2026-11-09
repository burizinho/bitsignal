# Fase 2 — Variantes de comparação (diagnóstico)

*   **Autor:** @burizinho
*   **Data:** 2026-11-09
*   **Status:** Approved (2026-11-09) — D1–D6 aprovadas pelo dono com as recomendações
*   **Depende de:** [bitcoin_unified_cycle_model.md](bitcoin_unified_cycle_model.md) (Fase 1, publicada; §7 traz o catálogo pré-registrado)

## Objetivo

Descobrir **qual peça** do modelo padrão faz o patrimônio ficar em 0,325 do comprar e segurar na
janela de desenvolvimento (2019+): escada de venda, detector, reinício, piso por ciclo, normalização
ou a forma de comprar. O resultado orienta um design futuro (Fase 3) da reserva e do piso.

**Não é objetivo:**

*   Substituir o modelo padrão. O padrão continua decidindo; nenhuma variante pode tomar o lugar dele
    depois de ver os resultados (regra do §7 da Fase 1).
*   Aprovar nada. Todas as janelas disponíveis já foram vistas. As variantes rodam sobre dados
    conhecidos e servem para entender o modelo, não para validá-lo. A única evidência independente é
    o registro semanal (`data/verdicts/weekly_verdicts.csv`).
*   Mudar o painel, o congelamento, o `model_hash` ou os parâmetros da Fase 1.

## O que já se sabe (variante padrão, sem rodar nenhuma variante)

Decomposição da carteira contínua (2014-05-11 → 2026-11-08), a partir dos trades do backtest gravado:

| Item | Valor |
| :--- | :--- |
| Vendas | 10 operações, 1,52 BTC vendidos por US$ 39,6 mil |
| Valor desses 1,52 BTC ao preço final (US$ 74.968) | US$ 113,7 mil |
| Compras | 167 operações, 0,90 BTC por US$ 1,1 mil (quase todo em 2014–2015) |
| Carteira final | 0,379 BTC + US$ 38,7 mil em caixa = US$ 67,2 mil |
| Comprar e segurar | 1,496 BTC = US$ 112,2 mil |
| Reinícios de ciclo | 2015-12, 2019-05, 2020-02, 2020-08, 2023-11 (2 com menos de 52 semanas) |

Leitura:

1.  **O dinheiro das vendas nunca volta para o bitcoin.** As compras são 2% / 4% de uma reserva-base
    fixa de US$ 219,56 (0,5 BTC em 2014), ou seja, US$ 4,39 / US$ 8,78 por semana, mesmo com US$ 7 mil
    em caixa em 2018 e US$ 30 mil em 2022. É a maior parte da diferença.
2.  **Vendas cedo demais em 2017.** 0,27 BTC vendidos a ~US$ 4,3 mil em ago–set/2017 (o topo foi
    ~US$ 19 mil).
3.  **O piso vale por ciclo** e os reinícios curtos de 2020 reiniciam a base; a posição encolhe de
    1,27 BTC (fim de 2017) para 0,38 BTC.

O catálogo pré-registrado testa sobretudo o lado da venda. Só `leftover_buy` e `floor40/60` tocam nos
itens 1 e 3. Por isso a decisão D1.

## Arquitetura

*   **Variante = override do config**, no mesmo mecanismo das sensibilidades (`apply_overrides`), num
    bloco novo `backtest.variants` fora do `model_hash`. Onde um override não basta, uma chave de
    comparação nova no config (ex.: `detector.enabled`), que `validate_for_panel` rejeita no painel.
*   **Saída só no CLI:** `bitsignal backtest --variants [--window calibration|development]`. Uma
    tabela por variante: patrimônio/comprar e segurar, melhora da queda máxima, patrimônio/DCA
    uniforme, BTC final, caixa final, nº de vendas e de reinícios. Cabeçalho fixo: "Comparação sobre
    janela já vista; não aprova nem substitui o modelo padrão."
*   **Sem gravação:** nada vai para o arquivo congelado. O painel não muda.

| Variante | Como entra | Código novo |
| :--- | :--- | :--- |
| `ladder_only` | `detector.enabled: false` (ver D2) | chave nova |
| `det_sma20` | `detector.trend_sma_weeks: 20` (disparo e fechamento já usam a mesma SMA) | não |
| `norm_high` | `score.inputs.*.max` | não |
| `floor40` / `floor60` | `cap.floor: 0.40` / `0.60` | não |
| `thr_plus5` / `thr_minus5` | `sell_ladder`, `cycle.arm_score/confirm_score`, `buys.tiers` deslocados | não (gerado por função) |
| `arm_score60` / `arm_score35` | `detector.arming: ath \| score60 \| score35` | sim, no `detect()` |
| `leftover_buy` | `buys.leftover_on_reset: true` | sim, no `simulate()` |
| `norm_hybrid` | ver D3 | — |
| `minimal` | ver D4 | modelo à parte |
| `reset_dd60` | fora (ver D5) | — |
| `proceeds_dca`, `floor_initial` | só se D1 = incluir | sim |

## Decisões (aprovadas em 2026-11-09)

*   **D1. Variantes pós-resultado.** A decomposição aponta para o reinvestimento do caixa e para o piso
    por ciclo, que o catálogo quase não cobre. Opções:
    *   (a) Incluir duas variantes **rotuladas "pós-resultado, não pré-registradas"**, numa tabela
        separada: `proceeds_dca` (compras em % do caixa disponível, não da reserva-base fixa) e
        `floor_initial` (piso de 50% sobre a posição inicial da carteira, não sobre a de cada ciclo).
        Servem só de insumo para o design da Fase 3.
    *   (b) Rodar só o catálogo pré-registrado.
    *   **Recomendação: (a).** Sem elas, a Fase 2 mede o lado que menos explica a perda. O rótulo e a
        tabela separada deixam claro que foram escolhidas depois de ver os dados.
*   **D2. `ladder_only` e o bloqueio do reinício.** Hoje o reinício exige `level == 0`. Opções:
    (a) detector desligado = `level` sempre 0, então ele também deixa de bloquear o reinício;
    (b) `V_det = 0`, mas o detector continua calculado e bloqueando o reinício.
    **Recomendação: (a)**, porque mede o efeito do detector inteiro, não de metade dele.
*   **D3. `norm_hybrid`.** "Picos de ciclos encerrados até t" depende dos ciclos que o próprio replay
    produz, o que torna a regra circular, e o design da Fase 1 não fixou como resolver. Opções:
    (a) tirar do conjunto executável, como `reset_dd60`; (b) definir ciclos encerrados pelos reinícios
    do modelo padrão (não da variante). **Recomendação: (a)**: definir agora seria escolher regra
    depois de ver os resultados.
*   **D4. `minimal`.** Lacunas e respostas propostas: compras só em ACUMULAR; um gatilho só vale na
    semana em que passa de falso para verdadeiro (um gatilho já ativo no início da carteira não
    dispara); base das vendas = saldo de BTC no início do ciclo; parâmetros num bloco `minimal:` só de
    comparação. **Recomendação: aprovar essas respostas e manter a variante**, porque é a referência
    "simples" contra a qual o modelo completo precisa se justificar.
*   **D5. `reset_dd60`.** Continua fora: a regra de saída da fase ACUMULAR nunca foi especificada.
*   **D6. Janelas.** Rodar cada variante na calibração (até 2018) e no desenvolvimento (2019+),
    sempre lado a lado com o padrão e com as mesmas sensibilidades desligadas. **Recomendação: sim**;
    ver as duas janelas mostra se um efeito é estável ou só de um período.

## Plano de implementação (depois das decisões)

1.  `config.py`: `backtest.variants` (fora do hash); chaves de comparação `detector.enabled`,
    `detector.arming`, `buys.leftover_on_reset` (e as de D1, se aprovadas); `validate_for_panel`
    rejeita todas.
2.  `engine/detector.py`: modos de armamento `score60` / `score35`; `enabled: false` zera `level`.
3.  `backtest/portfolio.py`: `leftover_on_reset` (e `proceeds_dca` / `floor_initial`, se D1 = a).
4.  `backtest/minimal.py`: o modelo `minimal`, com o mesmo `simulate()` e os mesmos preços de execução.
5.  `backtest/variants.py`: `VARIANTS` (nome → overrides), lista fixa e testada.
6.  `cli.py`: `backtest --variants`; `report.py`: tabela de variantes com o cabeçalho fixo.
7.  Testes: um caso sintético por chave nova; `test_variants.py` com a lista fixa de nomes; o padrão
    sem `variants` continua igual ao golden (o `model_hash` e o `replay_summary.json` não mudam).
