# Relatório de Revisão Goldfish: Zoom Out (Estágio 5)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md` (linhas 1–1010; FeatureRange 1–592, DetailedRange 593–1010)

**Padrão:** `zoom-out-standard.md`

## Status dos revisores

| Revisor | Status |
| --- | --- |
| `egm-zoom-out` (instância A) | concluído |
| `egm-zoom-out` (instância B) | concluído |

**Resumo:** 1 🔴 Blocker, 8 🟡 Major, 5 🟢 Nit (após deduplicação das duas instâncias).

**Veredito:** a direção está certa e deve ser mantida:
- um modelo puro e sem estado (`run_model` como porta única);
- uma fonte única de dados (CoinMetrics);
- a remoção de alertas, imposto, trailing stops e SQLite;
- testes de ausência de informação futura e de paridade entre painel e backtest.

O que bloqueia a aprovação é outra coisa:
- a máquina de calibração e de variantes é muito maior do que o histórico disponível consegue validar;
- vários números usados como justificativa não são reproduzíveis com o `probe.py` fornecido;
- o escopo mistura um saneamento barato com um projeto de pesquisa.

---

## 🔴 Blocker

### 1. A calibração promete uma evidência que os dados não podem dar, e a S6 não tem como ser decidida
* **Lente:** `egm-zoom-out` (A e B; A classificou como Major, B como Blocker. Fica como Blocker porque a S6, do jeito que está escrita, não pode ser executada.)
* **Escopo afetado:** L63, L108, L155, L283, L301, L369–383, L630, L843–853, L885–893
* **Problema:**
  - A G3 (L63) promete "calibra até 2017 e testa 2021 e 2022 fora da amostra". A Q1 (L108) e o §7 (L381) dizem o contrário: 2019+ é validação contaminada. Na prática, não existe teste fora da amostra.
  - A janela de calibração (L380, "topos de 2013 e 2017") tem, de fato, **um** topo só. A SMA200w começa em 2010-07-18 e só fica válida por volta de mai/2014 (regra de aquecimento, L283). Em 2013 o score fica em `intervalo`, com cerca de 20% do peso ausente. Como a escada C exige `score_min ≥ 85` (L301), o degrau é inatingível nesse período.
  - O "máx 85,0" de 2013 citado no brief só aparece porque o `probe.py` imputa 50 aos ausentes (`probe.py:25` → `normalizer.py:20–21`). É exatamente a imputação que o design proíbe (L60, Q6).
  - A S6 (L890) pede que o dono escolha a severidade de D (Q5b) e a política de sobra olhando só os dados até 2018. Mas todos os casos que motivam a Q5b são posteriores: falsos positivos de mai/2021 e set/2024, e proteção em jan/2022 e nov/2025 (L155). A escolha fica às cegas ou usa a janela contaminada.
  - O plano roda cerca de 15 variantes (L369–378, L843–852) sobre algo entre 20 e 40 parâmetros livres (pesos, limites, escada 85/90/93 → 5/15/30, detector, reinício, compras, teto). É o jardim de caminhos bifurcados que o próprio documento diz querer evitar (L88, L118).
* **Recomendação:**
  - Declarar explicitamente que a única evidência independente é a prospectiva.
  - Corrigir a G3 e a L380: a calibração útil começa por volta de 2014 e cobre um único ciclo completo.
  - Fixar agora, como política e não por experimento, os níveis de D (10/25/50%) e os critérios de agravamento, como já foi feito com os limites da Q1 (L118). Vale considerar também menos graus de liberdade: D com um ou dois níveis e escada com um ou dois degraus.
  - Reduzir o backtest a:
    - estratégia padrão (C + D_A);
    - os dois benchmarks da Q1;
    - a variante mínima (ver achado 4);
    - sensibilidade de ±5 pontos.
  - Transformar a S6 em um passo de congelamento de parâmetros, não em uma escolha do dono.

---

## 🟡 Major

### 2. Números usados nas decisões não são reproduzíveis com a evidência fornecida, e o probe mede outro modelo
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L39, L45, L148, L152, L154, L186, L434, L439–443, L455, L482, L491–495, L501, L509, L515, L521, L667
* **Problema:**
  - O `probe.py` calcula só três coisas:
    - o score diário com os limites atuais;
    - os primeiros cruzamentos de 75/80/85/90 e de ≤20;
    - uma saída por "score ≥ 80 em 17 semanas + EMA21w/SMA50w".
  - Isso sustenta apenas L39 e L44–45. O probe não testa o detector D (ATH em 52 semanas, SMA30w, −20%), o percentil, os limites B, a escada de compras nem o reinício.
  - Ficam sem fonte verificável, entre outros:
    - "única regra que pegou 2025" (L148);
    - falsos positivos de 2024-09 e 2025-03/04 (L152);
    - −57% e −38% (L154);
    - 1,36×, 1,30× e 1,17× (L186);
    - 1,88× e 1,82× (L509);
    - sobra de 46–77% (L515);
    - "score ≥ 60 sem falso positivo" (L491);
    - venda de mai/2021 a ~US$ 35 mil (L501);
    - −53% e −77% (L482);
    - os números de A4, A5, A11 e A12.
  - O valor de nov/2021 aparece de três formas que não batem entre si: 65,5 (L45), 48 (L442) e "48–69" (L455).
  - O probe também contradiz regras do próprio design:
    - imputa 50 aos ausentes, quando a Q6 e a A16 proíbem;
    - calcula o score diário e usa `resample("W-SUN").last()`, que inclui a semana em aberto (`probe.py:16`), quando o §3 exige candles fechados.
  - O degrau de 93 da escada C se apoia no máximo **diário** de abr/2021 (93,4, L45). Amostrado no fechamento semanal (L278), esse valor pode nunca chegar a 93.
* **Recomendação:**
  - Versionar em `docs/reviews/bitcoin_unified_cycle_model/` o script que gerou cada número.
  - Ou marcar esses números como "exploratório, não reproduzido" na tabela de status (L12–16) e retirá-los das razões de rejeição das alternativas.
  - Unificar o valor de nov/2021.
  - Refazer os cruzamentos 85/90/93 com amostragem semanal e sem imputação antes de chamá-los de "provisório aprovado" (L667).

### 3. Duas entregas de natureza diferente num único design
* **Lente:** `egm-zoom-out` (A; B levanta o risco relacionado no achado 8)
* **Escopo afetado:** L24–29, L576–580 (A22), L589, L595–606, L1010
* **Problema:**
  - O documento junta duas coisas:
    - um **saneamento** barato e de valor imediato: S0, S1, S2, migração para CoinMetrics e S8 (remoção de alertas, imposto, trailing stops e SQLite);
    - um **projeto de pesquisa**: detector D, catraca, reinício em duas etapas, DCA por score, D2 e cerca de 14 variantes.
  - Só o saneamento já resolve a raiz do problema descrito em L35–46:
    - o conflito entre os dois sistemas some quando `strategy/` sai;
    - o score fica certo com o Pi Cycle corrigido, candles fechados e o config lido.
  - O próprio documento diz que os critérios financeiros "não bloqueiam a publicação técnica" (L1010). Ou seja, toda a máquina de aprovação da Q1 só decide um rótulo.
* **Recomendação:** dividir em duas fases ou em dois designs.
  - **Fase 1:** correções, config único, CoinMetrics, remoção de código morto e um painel com o score corrigido e a fase, sem metas de venda. Isso entrega G2, G5, G6, G7 e parte da G1.
  - **Fase 2:** escada C, detector D, catraca, compras e backtest, com a Fase 1 já em produção.

### 4. A alternativa mais simples foi prometida e depois sumiu do plano
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L65–69, L96–97, L222, L369–378, L418, L826–827, L843–852
* **Problema:**
  - A A2 ("só preço") "continua como variante mínima no backtest" (L418), e o CUJ 3 exige essa comparação (L222). Mas ela não está nem no §7 nem em `VARIANTS` (S5).
  - O brief recomendava testar um score reduzido a 2–3 indicadores. Essa ideia desapareceu sem registro de rejeição.
  - O benchmark "DCA uniforme completo" usa as mesmas vendas C+D (L97, L827). Assim, o critério 3 avalia só a escada de compras e não diz nada sobre score, detector ou catraca.
  - Nenhum critério pergunta se o modelo completo supera uma regra trivial.
* **Recomendação:**
  - Adicionar ao catálogo `minimal` (fase por preço/SMA200w) e `score3` (3 indicadores), no lugar de variantes de baixo valor (D2, normB, armamentos B e C).
  - Declarar desde já que, se o modelo completo não superar a regra simples, fica a regra simples.
  - Renomear o critério 3 para deixar claro que ele avalia só as compras.

### 5. Variantes rejeitadas entram no config e no motor de produção
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L369–378, L650–659 (em especial L654, L656–657), L843–853
* **Problema:**
  - O `Config` de produção passa a carregar enums de alternativas já rejeitadas:
    - `arming: new_ath_52w | score_ge_60_26w | score_gt_35` (L654), sendo que B e C foram rejeitadas em A11 (L496);
    - `reset_mode: score_two_stage | drawdown_60` (L656), também rejeitado (L484);
    - `buys.mode` e `leftover` (L657);
    - `score.normalization: fixed | d2 | percentile` (L853), sendo que o percentil foi descartado (L141, A4) e a D2 deveria ser avaliada "separadamente" (L145, L450).
  - Cada alternativa vira um ramo permanente em `engine/`, com testes, a meta de 90% de cobertura (L998) e validação de config.
* **Recomendação:**
  - `engine/` e `config.yaml` devem conhecer só o caminho escolhido: armamento A, reinício em duas etapas, `score_dca` e normalização fixa.
  - As concorrentes, se ficarem, devem morar em `backtest/` ou em scripts de experimento fora do pacote.
  - Em `variants.py`, manter só overrides numéricos do mesmo algoritmo.
  - Retirar `percentile` e D2 deste design.

### 6. O modo `intervalo` é um terceiro estado para um caso que quase não existe, e a fonte do hashrate é contraditória
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L157–159, L265, L267, L274, L300–304, L686, L742–744, L763–765
* **Problema:**
  - O documento se contradiz sobre a origem do hashrate:
    - L265 diz que ele vem do Mempool.space;
    - L267 e L686 buscam `HashRate` na CoinMetrics.
  - Isso quebra a paridade entre painel e backtest prometida em L274.
  - Com fonte única, uma ausência "secundária" só acontece no aquecimento histórico. Se a CoinMetrics cair, cai tudo.
  - O próprio texto admite que, para vendas, o intervalo "quase equivale a congelar" (L159).
  - O custo é alto: três estados, `score_min`/`score_max`, regras diferentes para armar e para efetivar, e testes próprios.
* **Recomendação:**
  - Usar o `HashRate` da CoinMetrics nos dois caminhos e remover o Mempool.
  - Reduzir o status a `ok | indisponível`.
  - Começar o modelo na primeira semana em que todos os insumos estão válidos.

### 7. Goals e CUJs descrevem o escopo do brief, não o que foi decidido
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L52, L63, L72–74, L201, L205–213, L220, L228
* **Problema:**
  - **G1 (L52):** usa `avaliar(historico) -> Veredito`, mas o plano usa `run_model` + `latest_verdict` (L769, L774).
  - **G5 (L74):** fala em veredito "indicativo" quando algum insumo é estimado, estado que a Q6 eliminou.
  - **CUJ 1 (L201):** promete "VENDER Y% da posição", mas o §8 (L387) e a Q2 (L127) definem exposição-alvo.
  - **CUJ 2 (L207):** descreve a falha do Dune e de uma "reserva", mas o Dune não alimenta o modelo e não existe mais reserva. A falha relevante, da CoinMetrics, não tem CUJ.
  - **CUJ 3 (L220):** mede "acerto sim/não", critério que a Q1 e a A19 rebaixaram a diagnóstico.
  - **CUJ 4 (L228):** edita um bloco `bands:` que não existe no config proposto (L667).
* **Recomendação:** reescrever Goals e CUJs a partir das decisões Q1–Q9.
  - CUJ 1: exposição-alvo e compra em % da reserva-base.
  - CUJ 2: CoinMetrics fora do ar → score congelado e marcado como desatualizado, com o detector D seguindo só com preço.
  - CUJ 3: os três critérios da Q1 mais os diagnósticos.

### 8. O painel antigo continua mostrando ordens erradas durante S1–S6
* **Lente:** `egm-zoom-out` (B; A menciona o risco no achado 3)
* **Escopo afetado:** L79, L589, L595, L603, L639–642, L668
* **Problema:**
  - A regra "o painel continua funcionando em cada commit" mantém no ar, até o S7, as ordens contraditórias do STOP_2 e do C0, que motivaram o projeto (L37). Esse período inclui a S6, que é um ponto de decisão humano e pode levar semanas.
  - O S1 corrige o Pi Cycle e com isso muda as faixas que o painel antigo ainda exibe como ordem.
  - Para cumprir a regra, o plano cria um paliativo em `storage/db.py` (L639–642) que é apagado no S8.
* **Recomendação:**
  - No S0, colocar no painel antigo um aviso fixo ("em manutenção, não usar como ordem") ou esconder a aba "Plano Nacional".
  - Com isso, o paliativo do `created_at` deixa de ser necessário.

### 9. O Dune como "conferência" é código mantido sem efeito em decisão nenhuma
* **Lente:** `egm-zoom-out` (A: Major; B: Nit. Fica como Major por causa do custo em módulo, segredos e dependência.)
* **Escopo afetado:** L86, L170, L587, L704–715, L902, L964, L973
* **Problema:** o Dune não altera nada no modelo (L170), mas o design mantém para ele:
  - o módulo `dune.py`;
  - limites de divergência arbitrários (|ΔZ| > 0,3, |ΔPuell| > 0,1);
  - uma tabela na UI;
  - dois segredos;
  - a dependência `python-dotenv`.
* **Recomendação:** remover o Dune e registrar isso em Non-Goals (L86). Se algum dia for preciso conferir, roda um script avulso.

---

## 🟢 Nit

### 10. Open Questions funciona como ata de reunião, e a Q4 já foi respondida
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L8–17, L92–189, L138, L341
* **Problema:**
  - Cerca de 100 linhas da seção são decisões já fechadas, que repetem os §4–§7.
  - As perguntas realmente abertas (Q5b, sobra da Q9, Q8) ficam escondidas no meio.
  - A Q4 (L138) continua "aberta", mas o §6 (L341) já a respondeu.
* **Recomendação:**
  - Mover as decisões para um anexo "Registro de decisões".
  - Deixar em Open Questions só o que está pendente.
  - Fechar a Q4.

### 11. yfinance só para mostrar o "preço agora"
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L263, L394, L704–707
* **Problema:** é uma segunda fonte de preço, com cache de 15 min, para um número que não entra em nenhuma decisão. Além disso, não bate com o fechamento usado pelo modelo.
* **Recomendação:** mostrar o último `PriceUSD` da CoinMetrics com a data. Se o yfinance ficar, marcá-lo como opcional e explícito.

### 12. Constantes de implementação no YAML do usuário e retry escrito à mão
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L650–660, L686–687, L973
* **Problema:**
  - O `DataConfig` coloca no YAML do usuário URL, lista de métricas e `page_size`, que são constantes de implementação.
  - O `CapConfig` tem um único campo, e o caminho padrão é calculado com `parents[1]`, detalhe abaixo da altitude de design.
  - O plano troca o `tenacity`, já instalado, por um retry escrito à mão.
* **Recomendação:**
  - Deixar URL e métricas como constantes em `coinmetrics.py`.
  - Manter o `tenacity`, ou pelo menos não apresentar a troca como simplificação.

### 13. A ordem das regras aparece duas vezes
* **Lente:** `egm-zoom-out` (B)
* **Escopo afetado:** L320–338 e L762–768
* **Problema:** a mesma ordem de regras está descrita em dois lugares, e as duas versões precisam ficar sincronizadas.
* **Recomendação:** manter uma fonte só, no §6, e referenciá-la do outro lugar.

### 14. Pequenas imprecisões
* **Lente:** `egm-zoom-out` (A e B)
* **Escopo afetado:** L39
* **Problema:**
  - "Trava 15% do peso em 0" exagera: o probe mostra 75% dos dias desde 2019, não todos.
  - O bug do Pi Cycle está em `indicators.py:45`, não em `:44`.
* **Recomendação:** corrigir as duas referências.

---

## Reaproveitamento verificado (informativo)
- O Hash Ribbon já existe em `fetch_mempool_data` (`bitsignal/ingestion.py:147`). `hash_ribbon_state` deve ser extraído de lá, não reescrito.
- `pydantic` e `pyyaml` já estão em `requirements.txt` e `pyproject.toml`, então o `config.py` não traz dependência nova.
- `engine/indicators.py` (L702) e os gauges de `cycle_gauge.py` (L914) são reaproveitados corretamente.
