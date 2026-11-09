# Etapa 9: teste de prontidão para implementação, reauditoria (rodada 2)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md`, linhas 675–1147 ("## Detailed Implementation Plan"). As linhas 1–674 serviram como especificação normativa.
**Escopo:** só a Fase 1. A Fase 2 (variantes de comparação) fica fora. Nenhum achado pede mudança de parâmetros financeiros nem das decisões Q1–Q9. Validação financeira não pesou no veredito.
**Padrão:** `C:/Users/gsame/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/implementation-readiness-standard.md` (readiness e codebase-details); persona padrão (style).
**Histórico consultado (sem autoridade):** `D:/Projetos Gui/BitSignal/implementation_readiness_report.md` e a seção "Etapa 9" de `D:/Projetos Gui/BitSignal/goldfish_review_report.md`.

## Status dos revisores

| Revisor | Status | Achados brutos (B/M/N) |
| --- | --- | --- |
| `egm-implementation-readiness` | completed | 1 / 10 / 16 |
| `egm-codebase-details` | completed | 0 / 9 / 19 |
| `egm-style` | completed | 1 / 7 / 17 |

Nenhum revisor falhou e nenhum precisou de nova tentativa. Depois da deduplicação ficaram **2 Blockers, 16 Majors e 33 Nits**. O id principal de cada achado é o do revisor que o descreveu melhor; os ids equivalentes aparecem entre parênteses.

Conferi pessoalmente os dois Blockers no texto (L990 e L1020 × L1063).

---

## 1. Situação dos Blockers e Majors da rodada 1

| Id r1 | Sev. r1 | Estado | Evidência (linhas atuais) |
| --- | --- | --- | --- |
| ir-r1-1 | Blocker | Resolvido | A calibração vai só até `calibration_end` (L1019). `development` exige o arquivo congelado com o hash igual (L1020). `approval` é gravado uma única vez, em commit separado (L1046–1047). |
| ir-r1-2 | Major | Transferido para Fase 2 | L413 e L1128. O `detect()` não recebe score (L944). |
| ir-r1-3 | Major | Transferido para Fase 2 | L1129. |
| ir-r1-4 | Major | Transferido para Fase 2 | L424 e L1130. |
| ir-r1-5 | Major | Parcial | `FrozenParams`, `model_hash` e `load_frozen` estão definidos (L768–771). Mas a aba Backtest quebra sem arquivo congelado (ir-r2-4), o subconjunto do hash não tem nome (st-r2-7), e a L409 contradiz a L769. |
| ir-r1-6 | Major | Resolvido | Preço diário, fallback de 7 dias e `ratchet_at_start` em L984–986. A invariante nova está errada, mas isso é um defeito novo (ir-r2-1). |
| ir-r1-7 | Major | Resolvido | L997. Sobra só a posição da regra (ir-r2-26). |
| ir-r1-8 | Major | Parcial | Fórmulas em L1006–1010, mas ainda faltam as saídas "por ciclo" do §7 L412 (ir-r2-9). |
| cd-r1-1 | Blocker | Resolvido | Comandos chegam em S3, S5, S6 e S7 (L900, L1032, L1045–1046, L1070). O S8 só remove (L1081). |
| cd-r1-2 | Blocker | Resolvido | Detector testado com séries sintéticas no S4 (L964); o golden fica no S5 (L976–979). |
| cd-r1-3 | Blocker | Resolvido | `sev.py --csv` funciona offline e tem schema (L974); os 6 casos da Q5b estão em L979. Sobra uma frase contraditória (st-r2-23). |
| cd-r1-4 | Major | Transferido para Fase 2 | L424 e L1130. A L958 limita a "única porta" à Fase 1. |
| cd-r1-5 | Major | Parcial | O YAML literal está em L780–848, com `extra="forbid"` (L761). Mas a L764 valida `levels.pct`, e o YAML tem uma lista simples (L804). Também faltam o modelo de `sell_ladder` como lista e `hash_ribbon` sem `min`/`max` (ir-r2-12). |
| cd-r1-6 | Major | Resolvido | L952, L965 e L1064. |
| cd-r1-7 | Major | Resolvido | L1016–1021 e L1032. |
| cd-r1-8 | Major | Resolvido | L696–698, L742 e L929. |
| cd-r1-9 | Major | Resolvido | L742–743. A remoção no S8 abre um problema novo (ir-r2-6). |
| cd-r1-10 | Major | Resolvido | L727 e L732. |
| cd-r1-11 | Major | Resolvido | L717, L1060 e L1106–1109. |
| cd-r1-12 | Major | Resolvido | L892 ("copia, adaptado"). |
| style-r1-1 | Major | Resolvido | `test_parity.py` no S4 (L960, L967). |
| style-r1-2 | Major | Resolvido | L742, L750, L930 e L962. |
| style-r1-3 | Major | Resolvido | Tabela de enums em L699–708. |
| style-r1-4 | Major | Resolvido | L951. |
| style-r1-5 | Major | Resolvido | L696 e L868. |
| style-r1-6 | Major | Resolvido | L827–831, L845 e L868. |
| style-r1-7 | Major | Resolvido | L772, L855, L1062 e L1075. |
| style-r1-8 | Major | Resolvido | Lista única em L1140, citada em L398 e L1045. |
| style-r1-9 | Major | Parcial | `apply_overrides` está definido (L767). Mas a L764 ainda cita `levels.pct`, e a L765 diz que as condições "não são configuráveis", enquanto o YAML expõe as janelas do detector (ir-r2-2). |

**Resumo:** 21 Resolvidos, 4 Parciais (ir-r1-5, ir-r1-8, cd-r1-5, style-r1-9), 0 Não resolvidos, 4 Transferidos para Fase 2 (ir-r1-2, ir-r1-3, ir-r1-4, cd-r1-4). Os quatro Blockers da rodada 1 estão resolvidos.

---

## 2. Ordem das etapas

| Etapa | Dependências | `pytest -q` passa como escrito? | Painel antigo no ar? |
| --- | --- | --- | --- |
| S0 | ok | Sim, se o ambiente tiver `streamlit` e `plotly`. Esse pré-requisito só aparece no Verification Plan (cd-r2-14). | Sim |
| S1 | ok | **Não com certeza.** O teste do `rsi_wilder` espera 13 NaN, mas a fórmula dá 14 (st-r2-8). | Sim. A correção do Pi Cycle muda o score antigo de propósito. |
| S2 | ok | Sim. Só `cli.load_config` (`cli.py:59-63`) lê o YAML, e `weekly_evaluator.py:146-152` tem defaults. | Sim |
| S3 | ok | Sim, mas o aceite depende de `check_catalog`, que não tem URL (ir-r2-11). | Sim |
| S4 | ok | Sim, mas o critério de aceite cita o item errado (ir-r2-10). | Sim |
| S5 | ok | **Não.** A invariante do item 28 dispara em toda compra (ir-r2-1). A sensibilidade `late_entry_2019` também não roda na calibração (ir-r2-5). | Sim. `cli.py:13` e `engine.py` são trocados juntos. |
| S6 | ok | Sim, mas os controles de pré-registro não têm teste (cd-r2-7). | Sim |
| S7 | ok | **Não.** `test_app_smoke` exige o aviso sem arquivo congelado, e o painel chama `run_backtest(window="development")`, que falha nesse caso (ir-r2-4). | Entra o painel novo |
| S8 | ok | **Não.** `tests/test_indicators.py` importa as funções apagadas (ir-r2-6). O `ruff` também acusa imports sem uso (cd-r2-28). | — |
| S9 | ok | Não dá para verificar: o "CI" citado não existe (cd-r2-8). | — |

As dependências entre etapas estão corretas: nenhum item usa algo criado numa etapa posterior. O painel antigo continua funcionando até o S6.

**Dependência silenciosa da Fase 2:** não há. O único atrito é a validação `levels ≤ 1 − floor`, que vai rejeitar o `floor60` da Fase 2 (ir-r2-21).

## 3. Consistência entre YAML, modelos, convenções, regras e testes

**O que está coerente:**
- Os valores do YAML (L780–848) batem com o §3 ao §8.
- Os blocos do `Config` (L763) batem com as chaves do topo do YAML.
- `MODEL_FIELDS` (L768) bate com o §7 (L409).
- `data`, `ui` e `backtest.frozen_params` ficam fora do hash, como o teste da L855 exige.

**O que diverge:**
- `levels.pct` × lista simples; `SellLadderConfig` × lista; `hash_ribbon` sem `min`/`max` (ir-r2-12).
- Janelas configuráveis do detector × colunas fixas do `to_weekly` (ir-r2-2).
- Subconjunto de `backtest` no hash sem nome, e L409 × L769 (st-r2-7).
- Chaves dos critérios: `dd_improvement_pp`, `dd_improvement` e `*_ratio` (ir-r2-20).
- Tipo dos `cache_ttl_*` não declarado (st-r2-21).
- Caminhos relativos sem âncora (ir-r2-25).

---

## 4. Achados novos

### 🔴 Blockers

#### ir-r2-1: a invariante de conservação falha em toda compra
* **Revisor:** `egm-implementation-readiness`
* **Linhas:** L988 × L990 (item 28)
* **Problema:** numa compra, `Δcash = −usd` e `Δbtc × preço = usd × (1 − fee)`. A soma dá `−fee × usd`, mas o limite é `fee × |Δbtc × preço| = fee × usd × (1 − fee)`, que é menor. Com usd = 1000 e fee = 0,003, a soma tem módulo 3,0 e o limite é 2,991, então toda compra lança `AssertionError`. Por isso `test_backtest`, `test_golden` e o aceite do S5 não passam.
* **Correção:** escrever a identidade exata para cada tipo de operação:
  * compra: `Δcash + Δbtc × preço == −fee × usd`;
  * venda: `Δcash + Δbtc × preço == −fee × q × preço`;
  * tolerância `1e-9 × max(1, |notional|)`.

#### ir-r2-4: a aba Backtest do painel contradiz `run_backtest` (cd-r2-4, st-r2-1)
* **Revisores:** os três
* **Linhas:** L1063 × L1020, L1036, L1075. Contexto: CUJ 4 (L225–227), §8 L447, L399, L1147.
* **Problema:** o painel sempre chama `run_backtest(..., window="development", frozen=load_frozen(...))`, mas a L1020 manda essa chamada falhar sem arquivo congelado ou com hash diferente. São exatamente os casos em que a aba deveria mostrar o aviso, e o `test_app_smoke` (L1075) testa o caso sem arquivo. Há mais três lacunas:
  * o primeiro argumento está elidido, e o §8 fala em CSV congelado;
  * falta `sensitivities=False`;
  * recalcular `criteria` a cada carga contradiz "rodam uma única vez" (L399, L1147).
* **Correção:**
  * Na L1063, escrever a chamada completa: `F = load_frozen(cfg.backtest.frozen_params)`. Se `F` existe e `F.model_hash == model_hash(cfg)`, rodar `run_backtest(load_frozen_history(cfg.data.csv_path), cfg, window="development", frozen=F, sensitivities=False)`. Senão, rodar com `window="calibration"` e mostrar o aviso. O selo vem só de `F.approval`.
  * Nas L399 e L1147, trocar "rodam uma única vez" por "são gravados uma única vez (S6); os recálculos posteriores são só exibição".

### 🟡 Majors

#### ir-r2-2: `to_weekly` não recebe `cfg`, mas produz colunas que dependem dele (cd-r2-3; ir-r2-13)
* **Linhas:** L927–929, L697, L765, L790, L797–804. Contexto: CUJ 4 (L225).
* **Problema:** `sma30w`, `sma50w`, `high52w` e `picycle_bottom` saem com janelas e fator fixos, enquanto o YAML expõe `trend_sma_weeks`, `n2_sma_weeks`, `arming_weeks`, `confirm_weeks` e `picycle_bottom_factor`. Se o usuário mudar um desses valores, nada muda, o que contraria a CUJ 4. A L765 também diz que as condições "não são configuráveis", e não está dito a que regras o `confirm_weeks` se aplica.
* **Correção:** escolher uma das saídas:
  * `detect(weekly, cfg)` calcula as próprias médias a partir de `price`; ou
  * `to_weekly(daily_derived, as_of, cfg)`, com colunas `trend_sma` e `n2_sma`.

  Em qualquer caso:
  * calcular `picycle_bottom` com o `cfg` ou movê-lo para `derive_daily`;
  * declarar que `confirm_weeks` vale para o disparo, o fechamento e o N2;
  * reescrever a L765 como "a estrutura das regras é fixa; os números vêm do config".

#### ir-r2-3: o `level` na semana em que o episódio fecha não está definido (cd-r2-2)
* **Linhas:** L944, L950, L974, L979. Contexto: §5 L330–332, §6 L356.
* **Problema:** se `detect()` reportar o nível do episódio na semana do fechamento, o reinício (`level == 0`) só pode acontecer na semana seguinte; se reportar 0, pode acontecer na mesma semana. Isso muda a data de `CYCLE_START`, o golden e os critérios. Também falta a regra que converte as colunas em `start`, `n2`, `n3` e `end` para comparar com o `sev.py` (que grava `end` = semana do fechamento).
* **Correção:** escrever a regra explicitamente. Exemplo: "na semana do fechamento, `level` mantém o nível do episódio; o fechamento vale a partir da semana seguinte; `end` = semana do fechamento". Acrescentar um caso em `test_detector.py` e outro em `test_cycle.py`.

#### ir-r2-5: as sensibilidades em `run_backtest` estão incompletas (st-r2-4, cd-r2-19)
* **Linhas:** L831, L1018–1021, L1046.
* **Problema:**
  1. `late_entry_2019` começa depois de `calibration_end`, e a calibração é a janela padrão, usada no aceite do S5 e no golden.
  2. As sensibilidades `reserve_*` e `lag_2` alteram campos do hash. Se rodarem pelo caminho `development`, a checagem de hash falha.
  3. Não há regra para converter uma data em semana (2019-01-01 é terça-feira) nem para definir o instante de `base_btc`.
* **Correção:**
  * Sensibilidade cujo `start` cai depois do fim da janela é reportada como "não aplicável".
  * A checagem de hash vale só para o `cfg` base. Sensibilidades e benchmarks chamam `run_model`/`simulate` diretamente.
  * `start` = primeira semana W-SUN cujo domingo é ≥ a data.

#### ir-r2-6: o S8 apaga funções que `tests/test_indicators.py` ainda testa (cd-r2-5, st-r2-6; cd-r2-12, st-r2-13)
* **Linhas:** L740, L743, L749, L1081–1087. Código: `tests/test_indicators.py:5-12` e `:15-60`.
* **Problema:** o item 40 apaga `calculate_sma`, `calculate_ema`, `calculate_rsi`, `calculate_picycle_top_ratio` e `calculate_200w_sma_ratio`, mas não lista `tests/test_indicators.py`, que ainda as importa. O `pytest -q` do S8 falha com `ImportError`. O destino de `is_picycle_bottom_triggered` está ambíguo: a L740 diz "até o S8", mas a função não está na lista da L743. A L749 cita `test_pi_cycle_bottom`, que não existe; o teste real é `test_picycle_top_and_bottom` (`tests/test_indicators.py:46`).
* **Correção:**
  * Item 40: acrescentar `tests/test_indicators.py` (Modify) e remover os testes das funções apagadas.
  * Decidir o destino de `is_picycle_bottom_triggered` e incluí-la na L743 se for removida. Nesse caso, a tabela-verdade passa a testar `picycle_bottom()`.
  * Corrigir o nome do teste na L749.

#### ir-r2-7: um teste de `test_cycle.py` exige uma regra que o `replay()` não tem
* **Linhas:** L965 × L950. Contexto: §6 L368, L375.
* **Problema:** "dois ciclos não somam mais de 100% de compra" depende do caixa, mas o `replay()` não conhece caixa: `buy_pct` é um percentual fixo por semana.
* **Correção:**
  * Mover o caso para `test_backtest.py`: "total gasto ≤ reserva-base + produto das vendas; `CYCLE_START` não aumenta o caixa".
  * No `test_cycle.py`, testar só que `buy_pct` não muda com `cycle_id`.

#### ir-r2-8: falta a regra de emissão dos eventos e do "Motivo" (cd-r2-1)
* **Linhas:** L918–919, L950–953, L965, L1037. Contexto: §6 L377, §8 L436.
* **Problema:** os 5 `EventType` não têm gatilho nem campos definidos (`mechanism`, `threshold`, `before`, `after`). Também não está dito se `SCORE_UNAVAILABLE` sai em toda semana ou só na transição, nem se `DETECTOR_LEVEL` sai durante `reset_pending`. `Verdict.reason` não tem regra. O golden ("eventos de venda") e o painel dependem disso.
* **Correção:** acrescentar ao item 23 uma tabela por tipo:
  * `SELL_STEP` quando a catraca sobe;
  * `DETECTOR_LEVEL` quando `level` sobe, com nota se o nível foi neutralizado;
  * `RESET_ARMED` na transição de `reset_pending`;
  * `CYCLE_START` no passo 3;
  * `SCORE_UNAVAILABLE` só na transição para `UNAVAILABLE`.

  Acrescentar também a regra de `reason` por fase.

#### ir-r2-9: faltam os diagnósticos "por ciclo" do §7 (cd-r2-26; resto do ir-r1-8)
* **Linhas:** L1006–1010 × §7 L412.
* **Problema:** faltam "preço médio de venda como % do pico seguinte" e "preço médio de compra como múltiplo do fundo". Também não estão definidos a unidade de `false_sell_episodes` (operação ou episódio) nem o tratamento de vendas sem 180/365 dias de dados à frente.
* **Correção:**
  * Criar `per_cycle(trades, weeks, daily_price)`, com pico = máximo até o próximo `CYCLE_START` e fundo = mínimo da fase ACUMULAR.
  * Definir a unidade de `false_sell_episodes`.
  * Para janela futura incompleta: excluir a venda e reportar a exclusão.

#### ir-r2-10: os critérios de aceite do S4 e do S5 apontam para itens errados (st-r2-2)
* **Linhas:** L688–689.
* **Problema:** o S4 cita o "item 22", que é `detector.py`; os testes do S4 estão no item 25. O S5 cita os "itens 23–30", que são módulos; os testes do S5 estão nos itens 27 e 34. Como escrito, o portão das duas etapas não testa nada.
* **Correção:** S4 → "testes do item 25"; S5 → "testes dos itens 27 e 34 e todos os anteriores".

#### ir-r2-11: `check_catalog` não tem URL nem formato de resposta
* **Linhas:** L868, L871, L900, L1142.
* **Problema:** o valor de `CATALOG_URL` não está escrito, e o campo `community: true` é uma suposição. O aceite do S3 depende disso.
* **Correção:**
  * Fixar a URL `https://community-api.coinmetrics.io/v4/catalog-v2/asset-metrics?assets=btc`, o caminho JSON lido e o critério de sucesso.
  * Fixar os parâmetros da busca das séries (`assets`, `frequency=1d`, `start_time`, `page_size`), como em `probe.py:6`.

#### cd-r2-6: o `test_app_smoke` não tem pontos de injeção definidos
* **Linhas:** L1061, L1075.
* **Problema:** não está dito:
  * onde `cfg`, `load_history`, `cached_model` e `cached_spot` são definidos (no nível do módulo, o que permite `mock.patch`, ou dentro de `main()`);
  * como o teste injeta `buys.mode = uniform`;
  * como remove o arquivo congelado;
  * como isola `fetch_spot_usd` (yfinance) e o Dune, como exige a L1137.
* **Correção:**
  * `CONFIG_PATH` como variável de módulo; funções de cache no nível do módulo.
  * O teste aplica patch em `bitsignal.ui.app.load_config`, `load_history`, `bitsignal.data.spot.fetch_spot_usd` e `bitsignal.config.load_frozen`, e remove `DUNE_API_KEY` do ambiente.

#### cd-r2-7: não há testes para os controles de pré-registro do S6 nem para `dune.py`/`spot.py`
* **Linhas:** L886, L893–894, L1032, L1045–1046.
* **Problema:** não há teste para estas recusas, que sustentam a "validação única" da Q1:
  * `freeze-params` com testes falhando;
  * `--record` com `approval` já gravado;
  * `--record` sem `--window development`.

  `compare_with` (limiares 0,3 e 0,1) e `fetch_spot_usd` devolvendo `None` em caso de erro também não têm teste.
* **Correção:**
  * Criar `tests/test_cli.py`, com `subprocess` e `run_backtest` mockados, cobrindo as três recusas e o caminho feliz.
  * Criar `tests/test_dune.py`, cobrindo os limiares, datas que não coincidem e o `None` do spot.

#### cd-r2-8: o "CI" do S9 não existe e não está listado (ir-r2-22; parte do st-r2-25)
* **Linhas:** L692, L1107, L1139.
* **Problema:** o repositório não tem `.github/`, então a meta de cobertura ≥ 90% e o aceite do S9 não podem ser verificados. Além disso, `addopts --cov` com `fail_under = 70` faz falhar o `pytest` sobre um subconjunto de testes que o `freeze-params` roda.
* **Correção:** escolher uma das saídas:
  * criar `.github/workflows/ci.yml` (Create), com `pip install -e ".[ui,dev]"`, `ruff check bitsignal tests`, `pytest -q` e `pytest --cov=bitsignal/engine --cov=bitsignal/backtest --cov-fail-under=90`; ou
  * trocar "o CI" por um comando local obrigatório.

  Nos dois casos, o `freeze-params` roda com `--no-cov`.

#### cd-r2-9: a comparação entre o histórico ao vivo e o CSV congelado não está implementada
* **Linhas:** spec §2 L270 e risco L655; nenhum item do plano trata disso.
* **Problema:** a mitigação "CoinMetrics revisa dados históricos" não tem função, comando nem teste.
* **Correção:**
  * Criar `compare_histories(live, frozen) -> DataFrame` em `data/history.py`, com tolerância relativa fixa.
  * Testá-la sem rede.
  * Usá-la no `fetch-history` ou no painel.

  Se a mitigação for adiada de propósito, registrar isso na tabela de riscos.

#### st-r2-3: o padrão de `bitsignal backtest` contradiz a CUJ 3
* **Linhas:** L1017, L1032. Contexto: CUJ 3 (L212–214).
* **Problema:** a CUJ 3 promete mostrar primeiro os critérios 2019+, mas o padrão é `calibration`, que não calcula critérios. Também não está dito como o usuário vê os critérios gravados depois do S6.
* **Correção:**
  * Declarar na L1032 "padrão: `calibration`".
  * Acrescentar: "depois do S6, `--window development` sem `--record` mostra lado a lado os critérios de `approval` e o recálculo".
  * Qualificar a CUJ 3 da mesma forma.

#### st-r2-7: o subconjunto de `backtest` que entra no `model_hash` não tem nome (ir-r2-19)
* **Linhas:** L768–770, L855. Contexto: §7 L409.
* **Problema:** a segunda tupla não tem nome, e a L769, a L770 e a L855 falam só em `MODEL_FIELDS`. Lida ao pé da letra, a definição deixa `fee` e `criteria` fora do hash, o que enfraquece o aviso de "parâmetros diferentes". A L409 ("números como no YAML") contradiz `model_dump(mode="json")`.
* **Correção:**
  * Nomear a tupla `MODEL_BACKTEST_FIELDS`.
  * Definir `model_payload(cfg)` e usá-la nas L769, L770 e L855.
  * Alinhar a L409.

#### st-r2-8: o teste do `rsi_wilder` espera um número errado de NaN (cd-r2-11, ir-r2-15)
* **Linhas:** L742, L750.
* **Problema:** com `diff()`, `min_periods=14` e sem `fillna`, as posições 0–13 dão NaN, ou seja, 14 posições, e não 13. Escrito assim, o portão do S1 falha. Também faltam o caso de preço constante (0/0) e o `adjust` do `ema`.
* **Correção:**
  * Teste: "NaN nas posições 0–13; primeiro valor em `s.index[14]`".
  * Preço constante: "0/0 → NaN".
  * Fixar `ewm(span=n, adjust=False, min_periods=n)`.

### 🟢 Nits

| Id (equivalentes) | Linhas | Achado | Correção |
| --- | --- | --- | --- |
| ir-r2-12 (st-r2-12, resto do cd-r1-5) | L761–764, L788, L793, L804, L814 | A L764 valida `levels.pct`, mas `levels` é uma lista. `SellLadderConfig` também é declarado como modelo, mas o YAML é uma lista. `hash_ribbon` não tem `min`/`max`. `buys.tiers` não tem regra de validação nem de seleção. | `levels` estritamente crescente e ≤ `1 − floor`; `sell_ladder: list[tuple[float, float]]`; `InputConfig.min`/`max` opcionais só para `hash_ribbon`; `tiers` em ordem crescente, usando a primeira faixa com `score_max` ≤ limite. |
| ir-r2-14 | L696–698, L928 | Não está dito se as janelas semanais e o "seguidos" contam linhas ou semanas do calendário. | "Só semanas válidas; contagem por linha"; o `sev.py` segue a mesma regra. |
| ir-r2-16 (cd-r2-10) | L931, L938 | O mapeamento insumo → colunas e o estado do `picycle` antes da SMA471 não estão definidos. O valor de `score` fora de `OK` também não. | Tabela insumo → colunas → `state_*`; `picycle_bottom` dá NaN sem insumo; `score` = NaN fora de `OK`, ou outra regra escrita. |
| ir-r2-17 (cd-r2-22, st-r2-18) | L952, L965 | O instante em que a semana "terminou" não está definido. | "Fim = domingo + 1 dia, 00:00 UTC; `STALE` se `now − fim > max_staleness_days`." |
| ir-r2-18 | L1003–1005 | `rebase` não diz se corta as linhas anteriores a `d`, o que pode pôr 2018 dentro da queda máxima. | "Devolve só as linhas ≥ d." |
| ir-r2-20 (st-r2-15 parcial, cd-r2-17) | L770, L826, L1005, L1016 | As chaves de `Approval` não batem com as do config. O formato de `criteria()` não está definido, nem a origem de `csv_sha256`. | Usar as chaves do config; `criteria()` devolve `{criteria, values}`; `MarketHistory.csv_sha256`, lido do `.meta.json`. |
| ir-r2-21 | L764 × L426, L447 | A validação de `levels` vai rejeitar o `floor60` da Fase 2. A L447 diz "variantes no CLI". | Registrar na lista da Fase 2 (L1127); na L447, escrever "as sensibilidades ficam no CLI". |
| ir-r2-23 (cd-r2-27) | L1037 | `replay_summary.json` não tem schema, comando de geração nem tolerância. | Listar as chaves, o comando e `rel_tol=1e-9`. |
| ir-r2-24 (st-r2-24) | L979 | A conferência manual do golden não diz o que comparar nem o que fazer se algum caso da Q5b não se reproduzir. | Comparar com a exploração da Q5b; diferença só pela semana aberta vai para a mensagem do commit; qualquer outra diferença bloqueia o commit e volta para o design. |
| ir-r2-25 (cd-r2-16) | L840, L842 | `csv_path` e `frozen_params` são relativos ao diretório atual. | Resolver contra a raiz do repositório, como na L766. |
| ir-r2-26 (st-r2-5, cd-r2-20) | L950 × L997 | O item 23 diz "sem regra adicional", mas o modo `uniform` é um ramo do passo 5 do `replay`. Os três revisores apontaram; o style classificou como Major. Ficou Nit porque a regra está escrita no item 29. | Citar o ramo no item 23 e acrescentar o caso em `test_cycle.py`. |
| ir-r2-27 (st-r2-20) | L870, L910, L966, L1070 | Há chamadas incompletas: `run_model` sem `cfg`; `evaluate` sem `from_frame` e sem `now_utc`. Os testes de retry não mockam `time.sleep`. | Escrever as cadeias completas e mockar `time.sleep`. |
| cd-r2-13 (st-r2-23) | L974 | O modo sem `--csv` executa `probe.py`, o que contradiz a mesma linha, e deixa de funcionar no S8. | "Sem `--csv`: modo antigo, que deixa de funcionar no S8", ou tornar `--csv` obrigatório. |
| cd-r2-14 | L732, L1136 | O S0 precisa de `streamlit` e `plotly` instalados, e isso não está no aceite. | Escrever `pip install -e ".[ui,dev]"` no aceite do S0. |
| cd-r2-18 (st-r2-25) | L894 | `compare_with` compara com a linha semanal (domingo), e as datas quase nunca coincidem com a do Dune. | Comparar com a linha diária na data do Dune. |
| cd-r2-21 (st-r2-17) | L705, L952 | Nada produz `DataStatus.UNAVAILABLE`, e o rótulo colide com o do score. | Definir quem produz o valor ou removê-lo; usar o rótulo "fonte indisponível". |
| cd-r2-23 (st-r2-11) | L722, L732 | "No topo `st.warning`" é ambíguo, e a frase do `runpy` mistura ação com asserção. | "Logo depois de `st.set_page_config`, dentro de `main()`"; reescrever o teste com `runpy.run_path` duas vezes e a asserção separada. |
| cd-r2-24 | L1093 | `probe.py:3` também importa `calculate_rsi`, que sai no S8. | Citar os dois imports no item 41. |
| cd-r2-25 | item 7 | O paliativo do `created_at` não tem teste. | Acrescentar um caso de upsert em `tests/test_storage.py`. |
| cd-r2-28 | item 40 | Depois do S8 sobram `--db-path` (`cli.py:387`) e os imports `yaml`/`pandas` sem uso, e o `ruff` falha. | Incluí-los no passo (1) do item 40. |
| st-r2-9 | L683, L712 | O rótulo "Página em branco" se lê como uma entrega. | "Correção da página em branco (Q8)". |
| st-r2-10 | L679 | "Commits separados" contradiz etapas que têm vários commits. | "Uma etapa tem um ou mais commits e deixa o painel funcionando." |
| st-r2-14 | L771, L879–880, L1063, L690 | "Congelado" tem dois sentidos, e a janela 2019+ aparece com três nomes. | `load_frozen_params`/`write_frozen_params`; nome único "janela de desenvolvimento (2019+)". |
| st-r2-15 | L697, L919, L938, L951 | Nomes diferentes para o mesmo conceito: `ath` × `reference_ath_usd`; `cycle_start` × `cycle_start_date`; `status` × `score_status`; `sell_target` × `ratchet_sell`. | Escolher um nome para cada conceito, ou declarar as equivalências. |
| st-r2-16 | L772–773 | `ConfigError` é chamado com um argumento e definido com dois. | `ConfigError("buys.mode", "opção só para backtest")`. |
| st-r2-19 | L870 | "3 tentativas com espera 1/2/4 s" é ambíguo. | "Até 3 novas tentativas (4 chamadas no total)." |
| st-r2-21 | L845–846, L1061 | O tipo dos `cache_ttl_*` não está declarado. | `str`, repassado ao `st.cache_data`. |
| st-r2-22 | L987–988, L1010 | Há identificadores em português, `q` não é definido, e `reserve_usage(trades)` não recebe a fase. | `sold_in_cycle`/`reserve_usd`/`exec_price`; `q = min(target − sold, btc)`; passar `weeks` para `reserve_usage`. |
| st-r2-25a | L965 | "Reinício em duas etapas (15, 15, 35, 35)" é críptico. | "Armado na 2ª semana e efetivado na 4ª." |
| st-r2-25b | L951 | "Além das de entrada" é ambíguo. | "Além das colunas de `weekly`." |
| st-r2-25c | L1065 | "Sai `cli.cmd_run_daily`", mas a função só é apagada no S8. | "O painel deixa de chamar `cli.cmd_run_daily`." |
| st-r2-25d | L724 | "(Modify, aditivo)", mas o item muda o `cmd_ui`. | Tirar "aditivo". |
| st-r2-25e | L691 × L1138; L690; L1119 | O comando do `ruff` está diferente nas duas linhas; "checagens manuais" é vago; "quando a revisão terminar" é ambíguo. | Unificar o comando; citar as L1145–1146; escolher um marco. |

---

## 5. Contagem

| Severidade | Quantidade | Ids |
| --- | --- | --- |
| 🔴 Blocker | 2 | ir-r2-1, ir-r2-4 |
| 🟡 Major | 16 | ir-r2-2, ir-r2-3, ir-r2-5, ir-r2-6, ir-r2-7, ir-r2-8, ir-r2-9, ir-r2-10, ir-r2-11, cd-r2-6, cd-r2-7, cd-r2-8, cd-r2-9, st-r2-3, st-r2-7, st-r2-8 |
| 🟢 Nit | 33 | tabela acima |

**Rodada 1:** 21 Resolvidos, 4 Parciais, 0 Não resolvidos, 4 Transferidos para Fase 2.

## 6. Avaliação

O plano melhorou muito: os quatro Blockers da rodada 1 estão fechados, a ordem das etapas está certa e nenhum item da Fase 1 depende da Fase 2. Mesmo assim, como está escrito, o `pytest -q` não passa no S5 (ir-r2-1), no S7 (ir-r2-4) e no S8 (ir-r2-6), e provavelmente também no S1 (st-r2-8).

Além disso, o implementador ainda teria de tomar quatro decisões de comportamento sozinho:
* a regra dos eventos (ir-r2-8);
* o `level` na semana do fechamento (ir-r2-3);
* as janelas do detector (ir-r2-2);
* as sensibilidades (ir-r2-5).

Todas as correções são edições de texto de poucas linhas e não mexem em parâmetros financeiros nem nas decisões Q1–Q9.

**Fase 1 pronta para implementar: NÃO**
