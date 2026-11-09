# Relatório Goldfish: Teste de Prontidão para Implementação (Etapa 9, rodada 1)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md`, linhas 664–1098 (de "## Detailed Implementation Plan" até o fim do arquivo). As linhas 1–663 (§1–§8, Q1–Q9) foram usadas como especificação normativa.
**Modo:** REVIEW, egm-review-loop rodada 1.
**Código conferido:** `D:/Projetos Gui/BitSignal` (`bitsignal/`, `tests/`, `config/config.yaml`, `streamlit_app.py`, `requirements.txt`, `pyproject.toml`) e os scripts de contexto `docs/reviews/bitcoin_unified_cycle_model/probe.py` e `sev.py`.

## Status dos revisores

| Revisor | Status | Achados brutos |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 0 Blocker, 12 Major, 9 Nit |
| `egm-codebase-details` | completed | 3 Blocker, 14 Major, 12 Nit |
| `egm-style` | completed | 1 Blocker, 21 Major, 13 Nit |

Nenhum revisor falhou, então nenhum precisou ser rodado de novo. Depois de remover duplicatas, sobraram **4 Blockers, 25 Majors e 17 Nits**. Conferi diretamente no documento os quatro Blockers (linhas 708, 793, 871, 889–890, 976, 986, 1013, 1037–1040).

## Escopo do veredito

- **"Pronto para implementar"** significa que as regras estão completas, são coerentes entre si e podem ser testadas sem deixar ao implementador decisões que afetem o resultado. É isso que este relatório avalia.
- **"Estratégia financeiramente validada"** não está demonstrada, e o plano não tem como demonstrá-la: os critérios da Q1 só podem ser medidos depois do congelamento (S6), quando o backtest roda. Essa ausência **não** conta como defeito do plano.
- A exceção é o ir-r1-1. Ali o plano calcula e grava os critérios 2019+ antes do congelamento. Esse é um defeito de **ordem das etapas**, não de finanças.
- Nenhum achado propõe mudar parâmetros financeiros ou as decisões Q1–Q9.

---

## Verificação dos itens pedidos

| Item | Status | Evidência (uma linha) |
| --- | --- | --- |
| **M1** escopo canônico do `model_hash` | **Parcial** | O escopo está fechado (L404, L732, L979: só os blocos de modelo, sem `frozen_params`/`data`/UI). Mas a serialização "números como no YAML" (L404) não é implementável, `1/52` (L728) não é número YAML, e `freeze-params` "copia o config efetivo" (L1040), o que contradiz o item 31 (L977). Ver ir-r1-5. |
| **M2** agregação semanal do Hash Ribbon | **Parcial** | A regra está completa e é a mesma em L266, L701 e L810. Porém L708 testa `hash_ribbon_state`, que não existe, `test_weekly.py` (L854–858) não testa a agregação, e o nome da coluna muda de item para item. Ver style-r1-2. |
| **M3** fixture offline do detector | **Parcial** | A fixture está definida (L871, L884–891). Porém não dá para gerá-la como está escrito: `sev.py` executa `probe.py`, que acessa a rede e importa o `normalizer` que será apagado. O teste roda em S4, mas o arquivo só é criado em S5. A Q5b tem 6 casos, não 8. Ver codebase-details-r1-2 e codebase-details-r1-3 (Blockers). |
| **M4** variantes totalmente especificadas (`reset_dd60` removida) | **Parcial** | `reset_dd60` saiu (L425, L727). `arm_score35`, `thr_±5`, `floor40/60` e `leftover_buy` estão completas. `ladder_only`, `norm_high`, `norm_hybrid` e `minimal` ainda deixam decisões abertas. Ver ir-r1-2, ir-r1-3, ir-r1-4 e codebase-details-r1-4. |
| **A2** nomes das regras do detector | **Resolvido** | L725 (`trigger`, `below_sma50w_2w`, `n2_reached_and_le_60pct_high52`) bate com a tabela do §5 (L322–324). Falta só dizer se `rule` é vocabulário executável ou apenas rótulo (style-r1-9). |
| **A5** duplicação residual (item 19) | **Resolvido** | L836 aponta para os passos 1–5 do §6 sem repeti-los. Sobram uma divergência de grafia (`cycle_start` × `cycle_start_date`, Nit N3) e a repetição do §5 no item 18 (Nit N4). |
| **E5-4** variante mínima | **Parcial** | A regra em L419 está quase completa. Faltam: se há compra por queda fora de ACUMULAR, se gatilhos já atendidos disparam na semana de entrada, a base da posição, e como `run_backtest` despacha a variante e qual tipo ela retorna (L937). Ver ir-r1-4 e codebase-details-r1-4. |
| **E5-5** opções só de comparação bloqueadas no painel | **Parcial** | `validate_for_panel` existe (L733), mas a lista cobre só 4 chaves (`ladder_only`, `det_sma20`, `floor40/60` passariam). O item 32 nunca chama a função, e o item 8 não a testa. Ver style-r1-7. |
| **E5-8** aviso no painel antigo em S0 | **Resolvido** | L691 e a linha de risco em L642. Problema relacionado, mas separado: `bitsignal ui` mostra uma página em branco depois de S0 (codebase-details-r1-10). |
| **E5-12** inflação do config | **Parcial** | `CapConfig` ficou só com `floor` (L726). Porém `DataConfig` ainda carrega URL, lista de métricas, `page_size` e ttl (L730), o ttl também está fixo no código do item 32 (L986), e as sensibilidades estão duplicadas entre `BacktestConfig` (L729) e `SENSITIVITIES` (L929). Ver style-r1-6. |
| **E5-13** ordem das regras | **Resolvido** | L836: "mesma ordem de passos (1 a 5), sem regra adicional". |

**Resumo:** 4 Resolvidos (A2, A5, E5-8, E5-13), 7 Parciais (M1, M2, M3, M4, E5-4, E5-5, E5-12), 0 Não resolvidos.

---

## Achados priorizados

### 🔴 Blockers

#### codebase-details-r1-1: os comandos da CLI chegam só em S8, mas S3, S5 e S6 precisam deles antes
- **Revisores:** codebase-details (B1), implementation-readiness (M1), style (M17, em parte)
- **Linhas:** 793, 889, 942, 976–979, 1032–1042, 666, 1084
- **Discrepância:**
  - O item 14 (S3) e o item 22b (S5) geram o CSV com `bitsignal fetch-history`, que só é criado no item 37 (S8). Hoje `bitsignal/cli.py:382-449` não tem `fetch-history`, `evaluate` nem `freeze-params`.
  - S6 precisa de `freeze-params`, que também é S8.
  - S5 reescreve `run_backtest(history, cfg, variants)`, mas `cli.py:229-245` (`cmd_backtest`) ainda chama `run_backtest(df)` e `report.summary()`. Assim, `bitsignal backtest` fica quebrado de S5 a S8, justamente quando S5 e S6 precisam rodá-lo.
- **Por que é Blocker:** as etapas não podem ser executadas em sequência, o que quebra L666 ("o painel continua funcionando depois de cada uma") e L1084.
- **Correção:** dividir o item 37:
  - `fetch-history` entra em S3 (Modify `cli.py`, mudança só aditiva);
  - `cmd_backtest` passa a usar a nova assinatura em S5;
  - `freeze-params` e `evaluate` entram em S6, ou o item 31 diz que o arquivo é escrito à mão, com o formato exato;
  - S8 fica só com a remoção de `db-init`, `run-daily` e `strategy-*`.

#### codebase-details-r1-2: um teste de S4 depende de um golden criado em S5
- **Revisores:** codebase-details (B2), implementation-readiness (M1), style (M12)
- **Linhas:** 871, 884–891, 1084
- **Discrepância:** `tests/test_detector.py` (S4) compara com `tests/golden/detector_episodes.json`, mas o item 22b só gera esse arquivo "Em S5" (L889).
- **Por que é Blocker:** `pytest -q` falha no commit de S4.
- **Correção:** escolher uma destas e escrever qual:
  - mover o item 22b para S4, depois do CSV;
  - mover essa asserção para S5.

#### codebase-details-r1-3: `sev.py --csv` não gera um golden offline compatível com o detector de produção
- **Revisores:** codebase-details (B3), implementation-readiness (M3), style (M13)
- **Linhas:** 884–891, 1027, 145–146
- **Discrepância:**
  - `sev.py:15-19` executa (`exec`) o início de `probe.py`. Esse trecho acessa a rede (`probe.py:5-9`) e importa `bitsignal.engine.normalizer` (`probe.py:3-4`), que o item 36 apaga em S8.
  - `probe.py:16` monta semanas com `resample("W-SUN").last()`, que mantém semanas sem preço de domingo. O item 16 descarta essas semanas.
  - O plano não define:
    - o schema do JSON;
    - se entram os episódios anteriores a 2014 (`sev.py:57-59` os filtra);
    - como gravar um episódio ainda aberto (`sev.py:50-52`);
    - os `min_periods`.
  - L890 manda conferir "os 8 episódios citados na Q5b", mas a Q5b (L145–146) cita 6 (3 + 3).
- **Por que é Blocker:** o golden não é independente do código de produção nem roda offline, e depois de S8 não pode mais ser regenerado.
- **Correção:**
  - O item 22b reescreve `sev.py --csv` para não executar `probe.py` e não importar `bitsignal`.
  - O script monta as semanas com a mesma regra do item 16 (W-SUN, preço de domingo presente, só semanas fechadas) e com os mesmos `min_periods`.
  - Schema: `[{start, n2|null, n3|null, end|null, max_level}]`, datas ISO, todos os episódios desde 2010, `end: null` para episódio aberto.
  - Trocar "8" por "os 6 casos da Q5b" ou listar as datas.

#### style-r1-1: o portão de S6 exige um teste de paridade que só existe em S7
- **Revisores:** style (B1), implementation-readiness (M1)
- **Linhas:** 976, 1013–1016
- **Discrepância:** S6, passo 1, exige o teste de "paridade" antes de congelar, mas `tests/test_parity.py` é o item 35, em S7.
- **Por que é Blocker:** o portão de congelamento não pode ser executado.
- **Correção:** mover o item 35 para S4 ou S5, já que ele só depende de funções de S3 e S4. A outra saída é reescrever o passo 1 citando só testes que já existem.

### 🟡 Majors

#### ir-r1-1: os critérios 2019+ são calculados e versionados antes do congelamento
- **Revisores:** implementation-readiness (M2), style (M16)
- **Linhas:** 965–968, 942, 405, 978
- **Discrepância:** o item 30 (S5) grava "critérios" no golden a partir de `run_backtest(["default"])`. Como `approval_window_start = 2019-01-01`, isso já mostra o resultado 2019+, mas L978 diz que a validação roda "uma única vez" depois de S6.
- **Por que importa:** é um defeito de ordem, não financeiro, mas enfraquece o pré-registro da Q1.
- **Correção:**
  - Antes de S6, `run_backtest` reporta só a janela de calibração.
  - O golden de S5 guarda datas de ciclo, eventos e métricas de calibração.
  - Os critérios 2019+ entram num commit separado, depois do item 31, passo 3.

#### ir-r1-2: `ladder_only` não diz se o detector continua bloqueando o reinício do ciclo
- **Revisores:** implementation-readiness (M4), codebase-details (M5), style (M8)
- **Linhas:** 413, 353, 725
- **Discrepância:** "`V_det = 0` sempre" não diz se `level` continua impedindo o passo 3. Além disso, `DetectorConfig` não tem chave para desligar o detector.
- **Correção:**
  - Adicionar `detector.enabled: bool` (default `true`).
  - `ladder_only` passa `enabled: false`, o que dá `level = 0` e `V_det = 0` em todas as semanas.
  - Escrever no §7 que, nesse caso, o detector não bloqueia o passo 3.

#### ir-r1-3: `norm_high` e `norm_hybrid` não cabem no schema de config
- **Revisores:** implementation-readiness (M5), codebase-details (M5), style (M8)
- **Linhas:** 417–418, 723, 842, 930
- **Discrepância:**
  - `ScoreConfig` tem um único conjunto de `min/max`, então não há onde guardar os limites altos (7 / 5 / 3.5 / 85).
  - `norm_hybrid` depende de "ciclos encerrados", que vêm do `replay()`, mas `score_weekly` roda antes do `replay()` (L842). A dependência é circular.
  - Também não estão definidos o máximo usado nem quais limites mudam.
  - Os parâmetros 75% / 25% / ±20% não têm chave.
- **Correção:**
  - `norm_high`: override direto de `score.inputs.<x>.max` em `VARIANTS`, e tirar `high` do enum.
  - `norm_hybrid`: escrever a fórmula exata, com fonte dos picos sem dependência circular (por exemplo, datas `top` em `backtest.events` anteriores a t), clamp `[0.8, 1.2]·max_orig`, e chaves `score.hybrid {weight_orig, weight_max, max_shift}`.
  - Se não der para fechar a fórmula, registrar `norm_hybrid` como não executável, como foi feito com `reset_dd60`.

#### ir-r1-4: a semântica da variante `minimal` está incompleta
- **Revisor:** implementation-readiness (M11)
- **Linhas:** 419, 898, 937
- **Discrepância:** não diz:
  - se as compras por queda de 50% e 70% acontecem fora de ACUMULAR;
  - se gatilhos já atendidos na entrada disparam juntos;
  - qual é a base da posição para as vendas de 15% + 15%.
- **Correção:** acrescentar três frases explícitas em L419, por exemplo:
  - "compras só em ACUMULAR";
  - "gatilhos já atendidos disparam na semana de entrada";
  - "base = saldo BTC na primeira semana de DISTRIBUIR".

#### ir-r1-5: o arquivo congelado, a serialização do `model_hash` e o selo aprovado/experimental não têm schema
- **Revisores:** implementation-readiness (M6), codebase-details (M14), style (M17, M18)
- **Linhas:** 398–404, 732, 977–979, 986–997, 1040
- **Discrepância:**
  - Faltam as chaves de `params_<data>.yaml`.
  - "Números como no YAML" não é implementável depois do `safe_load` e do pydantic.
  - `freeze-params` "copia o config efetivo", mas o item 31 diz "só blocos de modelo".
  - Não existe `load_frozen()`.
  - Não está dito onde fica o resultado da validação única 2019+.
  - O item 32 não mostra o selo "experimental" / "Desempenho histórico aprovado" nem o aviso "parâmetros diferentes dos congelados".
- **Correção:**
  - Schema `{frozen_at, csv_sha256, model_hash, model: {...}, approval: null | {run_at, criteria}}`.
  - `model_hash = sha256(json.dumps(cfg.model_dump(mode="json", include=MODEL_FIELDS), sort_keys=True, separators=(",", ":")))`.
  - `load_frozen(path) -> FrozenParams` em `config.py`.
  - O item 32 lê `approval` para escolher o selo e mostra o aviso quando o hash difere ou o arquivo falta.
  - `freeze-params` grava exatamente esse schema.

#### ir-r1-6: a assinatura de `simulate` recebe só preço semanal, mas executa a preço diário
- **Revisores:** implementation-readiness (M8), codebase-details (M7), style (M14)
- **Linhas:** 896–897, 903, 917–919, 963
- **Discrepância:**
  - Há duas assinaturas diferentes.
  - A execução é no dia seguinte ao domingo (lag 1 ou 2), o que exige a série diária.
  - A frequência da curva de patrimônio, que define o drawdown máximo do critério 2, não está definida.
  - O rebase em 2019-01-01 não tem índice definido.
  - `catraca_em_start` é um identificador em português.
- **Correção:**
  - Uma única assinatura `simulate(weeks, daily_price, cfg, start, baseline_ratchet)`.
  - Curva de patrimônio diária; o rebase usa a primeira linha diária ≥ data.
  - Definir o que acontece quando falta preço no dia de execução.
  - Renomear para `ratchet_at_start`.

#### ir-r1-7: o benchmark DCA uniforme (critério 3 da Q1) está subespecificado
- **Revisor:** implementation-readiness (M7)
- **Linhas:** 387, 911, 728, 362
- **Discrepância:**
  - `uniform_complete(...)` não tem assinatura.
  - "Mesmas vendas" pode significar mesmos % ou mesmas quantidades.
  - Não diz se compra em semana com score `indisponível`.
- **Correção:** `uniform_complete(history, cfg)` = `run_model` + `simulate` com override `buys.mode = uniform`, mesma `ratchet_sell` do default (em %), `uniform_weekly` em toda semana com `reset_pending` independentemente do status do score, e mesmos `leftover` e `start`.

#### ir-r1-8: os diagnósticos do §7 e da CUJ 3 não têm definição
- **Revisores:** implementation-readiness (M12), style (M15)
- **Linhas:** 407, 920–923
- **Discrepância:**
  - `false_resets(...)` não tem critério.
  - "Custo de oportunidade" não está definido.
  - `false_episodes` não diz de onde mede a "queda ≥ 30%".
  - `premature_sales` usa "subir mais 50%", enquanto L407 diz "≤ 2/3 da máxima posterior", e nenhum dos dois define o horizonte.
  - Uso da reserva e quebra por ciclo não aparecem no item 25.
- **Correção:** dar uma fórmula para cada função, com preço de referência e janela, e reaproveitar a redação do §7.

#### codebase-details-r1-4: a variante `minimal` não passa pelo caminho de `VARIANTS`/`run_model`
- **Revisores:** codebase-details (M5, N11), style (M4)
- **Linhas:** 842, 928–931, 937, 942
- **Discrepância:**
  - `VARIANTS` é `dict[str, dict]` de overrides, mas `minimal` é outro modelo, chamado por `run_minimal`.
  - `run_minimal` retorna `pd.DataFrame` "no mesmo formato de `replay()`", só que `replay()` retorna `ReplayResult`.
  - Os parâmetros (3.5, 15/15%, 40/30/30%, −50/−70%) não têm lugar no config, o que contraria a CUJ 4.
  - L842 chama `run_model` de "única porta de entrada".
- **Correção:**
  - Bloco `MinimalConfig` e chave `model: "minimal"`.
  - `run_backtest` despacha para `run_minimal`, que retorna `ReplayResult`.
  - Reescrever L842 como "única porta do modelo padrão e das variantes paramétricas".

#### codebase-details-r1-5: o YAML alvo não está escrito, e os nomes conflitam com o `config.yaml` atual
- **Revisores:** codebase-details (M4, M12), style (M7), implementation-readiness (N4)
- **Linhas:** 721–741, 820, 729
- **Discrepância:**
  - O item 7 não diz o que acontece com os blocos `system` e `metrics` (`config/config.yaml:1-38`).
  - `essential = ["mvrv_z", "puell"]`, mas a chave atual é `puell_multiple`.
  - As seis chaves de insumo não estão listadas.
  - Faltam no `ScoreConfig` o mapa do Hash Ribbon (L820) e o fator 0.745 do Pi Cycle Bottom.
  - `uniform_weekly = 1/52` não é número YAML.
  - `start = first_all_valid_week` não tem tipo.
  - `events` não tem as datas.
  - A política `extra` do pydantic não está definida.
- **Correção:**
  - Colocar no item 7 o YAML literal completo: nomes canônicos dos seis insumos, `hash_ribbon_points`, `picycle_bottom_factor`, `uniform_weeks: 52` (inteiro) ou decimal, `start: Literal["first_all_valid_week"] | date`, e as datas (ou janelas) de cada evento.
  - Remover `system` e `metrics`.
  - `extra="forbid"`.

#### codebase-details-r1-6: a regra de dados desatualizados (9 dias, §3) não tem função, chamador nem teste
- **Revisores:** codebase-details (M6), implementation-readiness (M10), style (M18)
- **Linhas:** 277, 444, 730, 837, 995
- **Discrepância:** `max_staleness_days` só existe como campo. `latest_verdict(result)` não recebe o horário atual, e o item 32 só trata a falha de `load_history()`. A CUJ 2b e a Q6 dependem dessa regra.
- **Correção:**
  - `data_status(result, now_utc, cfg) -> Literal["ok", "desatualizado"]` em `engine/cycle.py` ou `pipeline.py`.
  - O item 32 mostra a tela sem veredito também quando o status é desatualizado.
  - Testes com 8 e 10 dias.

#### codebase-details-r1-7: `BacktestReport` e as assinaturas do backtest não estão definidas
- **Revisor:** codebase-details (M8), style (N11)
- **Linhas:** 911, 923, 942, 968, 1039
- **Discrepância:**
  - Os campos de `BacktestReport` não são dados. A classe atual (`backtest/engine.py:21-72`) é outra.
  - O item 30 chama `run_backtest(["default"])`, o que não bate com a assinatura `run_backtest(history, cfg, variants=…)`.
  - Os valores de `--window` e `--variants all` não estão definidos.
- **Correção:** dataclass com campos e módulo, chamada corrigida, e valores válidos dos argumentos da CLI.

#### codebase-details-r1-8: convenções de janela e `min_periods`, e o reuso de `calculate_rsi` reintroduz o "NaN vira 50"
- **Revisores:** codebase-details (M2), implementation-readiness (M9)
- **Linhas:** 701, 806–810, 863, 265, 276
- **Discrepância:**
  - `indicators.py:31` termina com `.fillna(50.0)`, e `indicators.py:14` e `:24-25` usam `ewm` sem `min_periods`. Reusar essas funções viola L863 e a flag de aquecimento.
  - Nenhuma janela tem `min_periods` declarado: máxima de 52 semanas, SMA30/50/200w, RSI 14, EMA150, SMA111/350/471, SMA30/60 do hashrate. O golden depende disso.
  - O plano não diz se o frame diário é reindexado no calendário.
  - Uma lacuna em `IssTotUSD` deixa o Puell NaN por cerca de 365 dias sem nenhum aviso.
  - Não diz se a primeira semana conta como novo ATH.
- **Correção:**
  - Declarar: reindexar no calendário com NaN e sem ffill, `min_periods = janela` em todas as janelas, primeira semana não é ATH.
  - Corrigir ou substituir `calculate_rsi` e ajustar `test_indicators.py:33-43`.
  - `fetch-history` avisa sobre lacunas internas.

#### codebase-details-r1-9: helpers escalares contra operações em coluna
- **Revisor:** codebase-details (M3)
- **Linhas:** 699–700, 775, 808
- **Discrepância:** `indicators.py:34-52` (`calculate_picycle_top_ratio`, `is_picycle_bottom_triggered`, `calculate_200w_sma_ratio`) recebem e devolvem escalares, mas `derive_daily` e `to_weekly` trabalham com colunas inteiras. O plano não diz se cria versões em coluna ou aplica os escalares linha a linha, e isso pesa na meta de < 1 s.
- **Correção:** nomear as funções vetoriais (`picycle_spread`, `picycle_bottom`, `price_to_sma`), dizer em que arquivo ficam, e dizer se as versões escalares saem em S8.

#### codebase-details-r1-10: `bitsignal ui` mostra uma página em branco depois de S0
- **Revisor:** codebase-details (M9)
- **Linhas:** 688–691
- **Discrepância:** `cli.py:248-251` roda `streamlit run bitsignal/ui/app.py` diretamente. Depois de S0 o corpo do módulo fica dentro de `main()`, e ninguém chama `main()`.
- **Correção:** em S0, adicionar `if __name__ == "__main__": main()` (ou chamada no nível do módulo) em `app.py`, ou apontar `cmd_ui` para `streamlit_app.py` e listar `cli.py` como Modify em S0.

#### codebase-details-r1-11: `sys.path` e empacotamento ficam a cargo do implementador, e a ordem S7/S9 está invertida
- **Revisores:** codebase-details (M10, M11), style (M19, M20), implementation-readiness (N5)
- **Linhas:** 1011, 1060–1062, 1083
- **Discrepância:**
  - O item 34 diz que a manipulação de `sys.path` "não é mais necessária com `-e .`". Mas `requirements.txt:11` já tem `-e .`, e os commits 1cdf128 e 53e1e04 adicionaram essa manipulação justamente por causa do Cloud.
  - "Se o Cloud exigir…" deixa a decisão aberta.
  - O item 32 não diz o que acontece com `app.py:10-23`.
  - O item 40 deixa um "ou" entre duas opções de empacotamento, não fixa versões e omite `pyyaml` e `python-dotenv`.
  - O item 34 (S7) depende do item 40 (S9).
- **Correção:**
  - Decidir: manter só a inserção do root e a limpeza de módulos em `streamlit_app.py`, e remover de `app.py`.
  - Item 40: `ui` como extra, `-e .[ui]` em `requirements.txt` (coerente com L1083), versões fixadas incluindo `pyyaml`.
  - Mover para S7 o que o item 34 precisa.

#### codebase-details-r1-12: o item 13 "move" o código do Dune em S3 e muda o comportamento em produção
- **Revisor:** codebase-details (M13)
- **Linhas:** 786
- **Discrepância:** o bloco do Dune é `ingestion.py:207-224`; as linhas 225–228 são o espelho no GitHub. `cmd_run_daily` usa esse código até S8. Movê-lo em S3 faz o painel atual cair para os valores fixos 2.10 / 1.05 (`ingestion.py:245-250`).
- **Correção:** "copiar (adaptado)" em S3, remover junto com `ingestion.py` em S8, e corrigir a faixa para `:207-224`.

#### style-r1-2: o nome do Hash Ribbon muda entre itens, e a agregação semanal não tem teste
- **Revisores:** style (M5), codebase-details (M1), implementation-readiness (N1)
- **Linhas:** 701, 708, 775, 810, 854–858
- **Discrepância:**
  - O item 3 define `hash_ribbon_daily`.
  - O item 4 (S1) testa `hash_ribbon_state`, que não existe.
  - O item 11 cria a coluna `hash_state`.
  - A coluna semanal do item 16 não tem nome.
  - Não há teste da agregação de segunda a domingo (M2).
- **Correção:**
  - O item 4 testa `hash_ribbon_daily`.
  - O item 11 grava `hash_sma30`, `hash_sma60` e `hash_cross_up`.
  - O item 16 nomeia a coluna semanal `hash_ribbon`.
  - `test_weekly.py` ganha três casos: cruzamento na quarta dá BUY_RECOVERY; SMA30 < SMA60 no domingo depois do cruzamento dá CAPITULATION; igualdade no dia do cruzamento.

#### style-r1-3: códigos de status em inglês no plano e em português na especificação
- **Revisores:** style (M1), implementation-readiness (N6)
- **Linhas:** 807, 817–818 (contra L298–301, L347–361, L97)
- **Discrepância:** o item 17 usa `ok | interval | unavailable`. O §4, o §6 e a G5 usam `ok | intervalo | indisponível`, e o item 16 usa `aquecimento` / `ausente`. `ScoreStatus` aparece sem valores.
- **Correção:** tabela de enum no item 21, por exemplo `ScoreStatus = {OK, INTERVAL, UNAVAILABLE}` com os rótulos em português e `InputState = {WARMUP, MISSING}`. Usar só os valores do código no plano.

#### style-r1-4: `ReplayResult.weeks` não tem as colunas de que os consumidores precisam
- **Revisor:** style (M3)
- **Linhas:** 834, 837, 987, 1003 (contra L234)
- **Discrepância:** faltam `score`, `score_min`, `score_max`, `status` e `level`, que `latest_verdict`, `score_gauge` e o bloco do detector usam.
- **Correção:** adicionar essas colunas a `weeks`, ou adicionar `score_df` e `detector_df` a `ReplayResult`.

#### style-r1-5: o schema de colunas da série diária não está declarado
- **Revisor:** style (M6)
- **Linhas:** 759, 770, 793, 806, 855, 897
- **Discrepância:** os itens 11 e 14 usam `price, mc, mvrv_ratio, iss_usd, hashrate`. Os itens 16, 22 e 23 usam `PriceUSD`. O item 10 não diz o que `fetch_coinmetrics` retorna.
- **Correção:** o item 10 renomeia a saída para os nomes curtos, e os itens 16, 22 e 23 passam a usar `price`.

#### style-r1-6: sensibilidades duplicadas e `DataConfig` inflado (E5-12)
- **Revisores:** style (M9), implementation-readiness (N3)
- **Linhas:** 729, 730, 929, 986
- **Discrepância:**
  - `reserve_sensitivity`, `late_entry_start` e o lag 2 aparecem em `BacktestConfig` e também em `SENSITIVITIES`.
  - O ttl aparece no config e fixo no item 32.
  - URL e lista de métricas estão no config, mas são constantes de código.
- **Correção:** uma única fonte para as sensibilidades, ttl lido do config, e URL e métricas como constantes em `coinmetrics.py`.

#### style-r1-7: `validate_for_panel` tem lista incompleta, não é chamado e não é testado (E5-5)
- **Revisores:** style (M10), implementation-readiness (N2)
- **Linhas:** 733, 746, 983–997
- **Discrepância:**
  - "Qualquer valor de comparação" é coberto por só 4 chaves; `ladder_only`, `det_sma20`, `floor40` e `floor60` passariam.
  - O item 32 não chama a função.
  - O item 8 não a testa.
  - Não diz se vale para o config do benchmark (`buys.mode = uniform`).
- **Correção:**
  - Lista exata das chaves e valores rejeitados.
  - O item 32 chama a função só no config do veredito.
  - Testes de rejeição no item 8.

#### style-r1-8: a lista de testes técnicos que bloqueiam a publicação aparece de três formas
- **Revisores:** style (M21), implementation-readiness (N8)
- **Linhas:** 976, 1087–1091 (contra L394)
- **Discrepância:**
  - O §7 lista determinismo, conservação, sem informação futura, paridade e cumprimento das regras.
  - S6 lista determinismo, conservação, sem informação futura e paridade.
  - O Verification Plan lista no_lookahead, parity, cycle e golden. Deixa de fora `test_backtest.py` (conservação), e "precedência" não corresponde a nenhum teste com nome.
- **Correção:** uma lista única de arquivos de teste no Verification Plan, referenciada pelo §7 e por S6.

#### style-r1-9: valores de regra do detector e chaves de override sem vocabulário definido
- **Revisores:** style (M8, em parte), implementation-readiness (N7)
- **Linhas:** 721, 725, 928
- **Discrepância:** não está dito se `levels.rule` (`trigger`, `below_sma50w_2w`, …) é um enum executável ou só um rótulo, nem a semântica de `apply_overrides` (merge profundo? listas substituídas?). Isso afeta `thr_±5` sobre `sell_ladder` e `tiers`.
- **Correção:**
  - Declarar que as regras ficam fixas no código e que `levels` configura só `pct`, ou definir o enum.
  - Definir `apply_overrides`: dicionários com merge profundo, listas substituídas, revalidação no fim.

### 🟢 Nits

| Id | Linhas | Achado | Correção |
| --- | --- | --- | --- |
| N1 (style) | 707–708 | `(:52-54)` sem nome de arquivo; a referência vai ficar velha. | Citar `tests/test_indicators.py` e o nome do teste. |
| N2 (style) | 701 | `puell(iss_usd)` contra `iss` na fórmula. | Usar um nome só. |
| N3 (style) | 834–836 | Item 19: `cycle_start` contra `cycle_start_date` do §6; `v_esc` contra `V_esc`. | Escolher uma grafia e aplicá-la no §6 e no item 19. |
| N4 (impl-readiness) | 826–827 | O item 18 repete o §5 (coerente hoje, mas pode divergir depois). | "Implementa o §5" e a assinatura. |
| N5 (style) | 725, 729 | `(0,20)` com vírgula decimal ao lado de `0.10`. | Ponto decimal em todo valor de config. |
| N6 (style) | item 6 | `SellLadder` sem o sufixo `Config`; o mapeamento modelo→bloco YAML (`BuyConfig`→`buys`) não está dito. | Uma linha de mapeamento. |
| N7 (style) | 761, 787, 808 | "Rótulo do intervalo mantido" é obscuro; `Divergence` não está definido; `ath` contra `reference_ath_usd`. | Redigir explicitamente e unificar os nomes. |
| N8 (style) | 848–850 | Lista "Sai:" num item de S4, seguida de "a remoção acontece em S8". | Mover a lista para o item 36. |
| N9 (style/cd) | 880 | "20 datas aleatórias" sem seed; `history[:t]` não funciona num dataclass congelado. | Seed fixa e `MarketHistory.truncate(t)`. |
| N10 (cd/style) | 932, 937 | O teste que confere `VARIANTS` contra a tabela do §7 não tem arquivo; ler o design dentro de um teste é frágil; "40% … por queda de 0%" diverge do §7. | `tests/test_variants.py` com lista fixa de nomes; corrigir a redação. |
| N11 (style/cd) | 986 | `ttl=6h` não é sintaxe válida; falta o cache de 15 min do yfinance (§8); `model()` é um nome genérico. | `ttl="6h"`, cache de 15 min no item 12/32, `cached_model`. |
| N12 (cd) | 1052 | `DUNE_QUERY_ID` não está em `.env.example` hoje, então é "Adicionar"; `LOG_LEVEL` não é tratado. | Corrigir a ação. |
| N13 (cd/style) | 1076–1079, 1022, 1041 | `SITEMAP.md:7` já lista o design (Modify, não Create); as entradas substituídas (`SITEMAP.md:5-6`) não mudam de status; "na ordem segura" não diz a ordem; o comando `ui` não está definido. | Ações concretas. |
| N14 (cd) | 721 | O novo `load_config` convive com `cli.load_config` (`cli.py:59-63`). | O item 37 remove o antigo. |
| N15 (cd) | 862 | "2,10 não aparece em lugar nenhum" não é verificável. | Teste tipo grep sobre `bitsignal/`, ou remover a frase. |
| N16 (cd) | 1086 | As metas de cobertura não têm `--cov-fail-under` em `pyproject.toml:42-44`. | Adicionar a configuração. |
| N17 (cd/ir) | 848, 1027, 753, 900 | `NormalizedMetricScore` (`models.py:91-95`) fica fora da lista de remoção; apagar `normalizer.py` quebra `probe.py`; `DataUnavailable` e `Divergence` não têm módulo; a taxa de compra não está definida (`min(alvo, caixa/(1+fee))`); o estado inicial do replay não está dito. | Completar cada ponto no item correspondente. |

**Nota de conferência:** o style-M11 apontava que a remoção dos blocos em S2 quebraria o painel. O codebase-details refutou isso com evidência: `weekly_evaluator.py:146-152` tem defaults para todo `strategy.*`. Por isso o ponto foi descartado. O destino de `system` e `metrics` ficou no codebase-details-r1-5.

---

## Contagem por severidade

| Severidade | Quantidade |
| --- | --- |
| 🔴 Blocker | 4 |
| 🟡 Major | 25 |
| 🟢 Nit | 17 |

## Veredito

As regras do modelo (§2–§6) estão maduras, e quatro dos onze itens pedidos foram resolvidos. O plano ainda falha em três frentes:

- **Ordem das etapas:** CLI, golden e paridade aparecem em etapas posteriores às que precisam deles.
- **Golden do detector:** não pode ser gerado offline como está descrito.
- **Decisões abertas:** variantes, arquivo congelado, `simulate`, benchmark, diagnósticos, `min_periods` e YAML alvo ainda têm pontos que o implementador teria de decidir sozinho.

Quase todas as correções são mecânicas e não mexem em parâmetros financeiros nem nas decisões Q1–Q9. A validação financeira da estratégia continua não demonstrada, como é esperado antes de S6, e isso não pesou no veredito.

**Pronto para implementar: NÃO**
