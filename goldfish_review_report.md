# Goldfish Annotated Review Report

**Status:** resolved (2026-11-08). Foi aplicado o "auto accept" (B1, M1, M2, M4, M6–M10, M13–M18 e os Nits aceitos; recusados N6, N18, N23 e N24). O dono decidiu, nesta ordem: M5 = política de severidade com SMA50w; M11 = venda acumulada-alvo; M3 = sem veredito, com contexto em memória; M12 = carteira contínua decide e entrada tardia em 2019 só como diagnóstico, com reserva de 0,5 BTC em USD fixa. B1: `HashRate` verificado no catálogo Community (diário desde 2009-01-09). Pendente: reauditoria da Etapa 7 (rodada 2).

**Target:** `docs/designs/bitcoin_unified_cycle_model.md` (linhas 1–591, FeatureRange). Etapa 7, rodada 1.
**Fonte dos achados:** [critic_report.md](critic_report.md). Alguns achados também aparecem em [zoom_out_report.md](zoom_out_report.md) e [comprehension_report.md](comprehension_report.md).

**Resumo das classificações:**
- **PROPOSE FIX:** 1 Blocker, 14 Major e 18 Nit.
- **PROPOSE FIX que precisa de escolha do dono:** 4 Major (M3, M5, M11, M12). Ficam fora do "auto accept".
- **DECLINE:** 6 Nit.
- **CONTEST:** 0.
- **ESCALATE:** 0.

---

## Prioritized Findings & AI Suggestions

### [B1] [`egm-design`, `egm-style`] - Severity: High
*   **Affected Scope:** linhas 172, 262–274 (§2 Dados), 580
*   **Discrepância:** o §2 diz que o hashrate vem do Mempool.space, que só cobre 3 meses. O backtest usa o `HashRate` da CoinMetrics. O replay do painel ficaria sem Hash Ribbon no histórico, e a paridade quebra.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justificativa:*** o achado procede. O texto sobrou de antes da Q7 e da decisão de fonte de preço. Pelas duas decisões, todo insumo do modelo deve vir da CoinMetrics, e o S3 (item 10) já busca `HashRate`.
*   ***Proposed Edit:***
    *   §2: trocar o item "Hashrate: vem do Mempool.space…" por "Hashrate: `HashRate` da CoinMetrics, na mesma chamada. **Todo insumo do modelo vem exclusivamente da CoinMetrics Community.**"
    *   O Mempool.space sai do design por completo (nem conferência), por YAGNI.
    *   Na l. 172, deixar "as 5 séries" explícitas: PriceUSD, CapMrktCurUSD, CapMVRVCur, IssTotUSD, HashRate.

### [M1] [`egm-structural`, `egm-design`] - Severity: Medium
*   **Affected Scope:** documento inteiro; nova seção entre Alternatives e NFR
*   **Discrepância:** falta a seção Risks & Mitigations.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** criar `## Risks & Mitigations` com a tabela `Risco | Impacto | Mitigação | Onde`. Linhas da tabela:
    1. CoinMetrics como ponto único de falha.
    2. CoinMetrics revisando o histórico: diff contra o CSV congelado e aviso de reconstrução.
    3. Limite de requisições (429) em IP compartilhado do Streamlit Cloud: backoff e cache.
    4. Métricas saindo do plano Community: `check_catalog`.
    5. Licença CC BY-NC.
    6. Yfinance não oficial: só exibição.
    7. Sobreajuste por muitas variantes numa janela contaminada: variante padrão pré-registrada, as outras só para comparação.
    8. Calibração com um único topo (ver M5).
    9. Usuário executando sem saber a posição-base (ver M11).

### [M2] [`egm-design`] - Severity: Medium
*   **Affected Scope:** l. 157, 171 contra 263
*   **Discrepância:** a Q6 e a Q7 dizem que D continua se a CoinMetrics falhar; o §2 diz o contrário.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justificativa:*** procede. Depois da decisão de fonte de preço, D depende de `PriceUSD`.
*   ***Proposed Edit:*** separar dois casos na Q6, na Q7 e no §2:
    *   (a) falta MVRV ou Puell, mas `PriceUSD` está presente: score indisponível, **D continua**;
    *   (b) a CoinMetrics caiu ou falta `PriceUSD`: **score e D indisponíveis**.

### [M3] [`egm-design`] - Severity: Medium — **precisa de escolha do dono**
*   **Affected Scope:** l. 157, 213, 394, 87
*   **Discrepância:** "mostrar o último valor válido" não é viável com `st.cache_data` (ttl de 6 h) e sem persistência. Se a CoinMetrics estiver fora do ar no refresh, não sobra nada para mostrar.
*   ***AI Suggestion:*** PROPOSE FIX, com escolha. Opções:
    *   (a) cópia "último bom" em memória, sem expiração. Se perde quando o app reinicia.
    *   (b) usar o CSV congelado do repositório como reserva, com o selo "histórico congelado até dd/mm". As semanas depois do congelamento ficam indisponíveis.
    *   (c) aceitar a tela sem veredito e dizer isso no CUJ 2.
*   ***Proposed Edit:*** reescrever a Q6 ("último score válido") e o CUJ 2 conforme a opção escolhida.

### [M4] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Medium
*   **Affected Scope:** l. 63, 70, 88, 105, 108, 136, 220, 310, 380–382
*   **Discrepância:** a G3 diz "calibra até 2017, testa fora da amostra". O §7 calibra até 2018 e chama 2019+ de validação de desenvolvimento. O "walk-forward" não tem folds definidos, e as listas de eventos divergem entre seções.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    *   G3: usar o texto do §7, com as três janelas.
    *   L. 88 e 136: trocar "fora da amostra" por "antes da validação".
    *   Trocar "walk-forward" por "calibração → congelamento → validação de desenvolvimento → validação prospectiva", sem folds.
    *   Lista única de eventos de diagnóstico: topo 2017, topo abr/2021, topo nov/2021, fundo 2022, topo 2025.

### [M5] [`egm-design`; também `zoom_out` Blocker 1] - Severity: Medium — **precisa de escolha do dono**
*   **Affected Scope:** l. 43–45, 157–159, 283, 380, S6; números das alternativas A4, A5, A7, A13 e da Q9
*   **Discrepância:**
    *   A SMA200w só fica válida em ~mai/2014. Em 2013 a escada C não chega a 85, então a calibração tem **um** topo (2017).
    *   Os números do documento vieram de um script que preenche dado ausente com 50 e mede o score diário.
    *   A S6 pede para escolher a Q5b olhando só ≤ 2018, mas nenhum dos casos que motivaram a Q5b está nessa janela.
*   ***AI Suggestion:*** PROPOSE FIX.
    *   **Parte sem escolha:** rotular no texto os números de 4.1, Q5, Q5a, Q9 e A4–A13 como "exploratórios: score diário, ausente = 50". Declarar no §7 os eventos avaliáveis depois do aquecimento: topos de 2017, abr/2021, nov/2021 e 2025; fundos de 2015, 2018 e 2022. O de 2013 não é avaliável.
    *   **Parte com escolha** (como decidir a Q5b em S6):
        *   (a) fixar os níveis de D como política de risco, sem calibração (10/25/50% com critérios escolhidos agora). O backtest só mede.
        *   (b) calibrar com ≤ 2018 mesmo assim (um topo), aceitando que é fraco.
        *   (c) escolher olhando 2019+ e rebaixar o rótulo para "parâmetros escolhidos com a janela de validação", e a janela prospectiva vira a única evidência independente.
*   ***Proposed Edit:*** rótulos nas seções citadas; texto do S6 e da Q5b conforme a opção escolhida.

### [M6] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Medium
*   **Affected Scope:** l. 22, 48, 72, 201, 387
*   **Discrepância:** a linha do topo do painel aparece em três formatos, e o CUJ 1 mostra uma ordem incremental, o que contraria a Q2.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** formato único no §8, citado pelas demais linhas: "Semana fechada em dd/mm · FASE · Venda acumulada-alvo no ciclo: X% da posição-base (ciclo iniciado em dd/mm/aaaa) · Compra desta semana: Y% da reserva-base · Motivo: …". A forma final depende de M11.

### [M7] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Medium
*   **Affected Scope:** l. 74, 207–213
*   **Discrepância:** o CUJ 2 descreve a arquitetura antiga (Dune com reserva fixa) e usa os selos "estimado" e "indicativo", que não existem mais.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** dividir em CUJ 2a (insumo secundário ausente: estado `intervalo`, mostrando `score_min` e `score_max`) e CUJ 2b (MVRV/Puell ausente, ou CoinMetrics fora: `indisponível`, com os casos de M2 e o modo de M3). Na G5, usar o vocabulário `ok` / `intervalo` / `indisponível`.

### [M8] [`egm-design`, `egm-structural`] - Severity: Medium
*   **Affected Scope:** CUJ 3 (l. 217–223)
*   **Discrepância:** o CUJ 3 promete "acerto sim/não" por evento e deixa de fora os critérios da Q1.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** o Then lista primeiro os 3 critérios APROVADO / NÃO APROVADO da variante padrão contra comprar-e-segurar e contra o DCA uniforme completo; depois os diagnósticos por evento; depois as variantes do §7. Remover "acerto". Definir "variante mínima" como A2 e incluí-la na lista de variantes.

### [M9] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Medium
*   **Affected Scope:** CUJ 4 (l. 225–231), l. 393
*   **Discrepância:** o CUJ 4 incentiva editar faixas, o que conflita com o congelamento. O artefato pré-calculado do backtest não está definido. O bloco `bands:` não existe.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    *   A aba de backtest **calcula ao vivo** a variante padrão e os benchmarks a partir do CSV congelado, com `st.cache_data`. Assim não existe artefato pré-calculado.
    *   O painel compara o hash do config em uso com o do arquivo `config/frozen/params_*.yaml` e mostra o aviso "parâmetros diferentes dos congelados: status aprovado não se aplica" quando forem diferentes.
    *   CUJ 4: editar depois do congelamento invalida o status aprovado e a trilha prospectiva.
    *   Trocar `bands:` por `sell_ladder:` e remeter à S2 para a lista de blocos.

### [M10] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Medium
*   **Affected Scope:** pseudocódigo do §6 (l. 327–337)
*   **Discrepância:** o pseudocódigo ignora `reset_pending` para V_D, `score_min`/`score_max`, o estado `indisponível` e o teto configurável. "Detector desligado" não tem definição, e a ordem de avaliação na semana do reinício não é dada.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** reescrever o pseudocódigo com esta ordem:
    1. calcular status, `score_min` e `score_max`;
    2. atualizar os contadores de armar e efetivar, ignorando semanas `indisponível`, que não contam nem zeram;
    3. se o reinício for efetivado nesta semana, zerar a catraca e **não** aplicar V_C/V_D nesta semana;
    4. senão: `v_d_eff = 0 se reset_pending senão V_D`; `ratchet = min(cap, max(ratchet, V_C(score_min), v_d_eff))`, com `cap = 1 − floor` vindo do config;
    5. compras se `reset_pending`.

    Trocar "detector desligado" por "sem episódio ativo do detector (`level == 0`)".

### [M11] [`egm-design`] - Severity: Medium — **precisa de escolha do dono**
*   **Affected Scope:** l. 127, 134–135, 341–345, 387
*   **Discrepância:** durante ACUMULAR, o painel manda comprar e ao mesmo tempo mostra "manter X% da posição do início do ciclo". Depois da compra, o BTC do usuário fica acima do alvo, o que parece uma ordem de venda.
*   ***AI Suggestion:*** PROPOSE FIX, com escolha. Opções:
    *   (a) o número exibido passa a ser **venda acumulada-alvo** sobre a posição-base do ciclo ("vender no total X% da posição-base"), e não "manter". O BTC comprado em ACUMULAR não entra nessa conta até o próximo ciclo.
    *   (b) manter "exposição-alvo" e escondê-la durante ACUMULAR.
    *   (c) manter "exposição-alvo" e somar o BTC comprado na fase. Isso exige que o painel saiba quanto foi comprado, o que ele não sabe.
*   ***Proposed Edit:*** texto da Q2, §6 (fase exibida), §8 e CUJ 1 conforme a escolha, mais um CUJ curto da tela em ACUMULAR.

### [M12] [`egm-design`] - Severity: Medium — **precisa de escolha do dono**
*   **Affected Scope:** l. 97, 101–103, 118, 351, 355
*   **Discrepância:** os critérios dependem do tamanho da reserva e da data de início, e nenhum dos dois está congelado.
*   ***AI Suggestion:*** PROPOSE FIX, com valores a confirmar:
    *   data de início de cada janela = primeira semana com todos os seis insumos válidos (~2014-05). A validação de desenvolvimento começa em 2019-01-01, com a carteira reiniciada (1 BTC + reserva) nessa data;
    *   reserva-base = 0,5 BTC em USD na data de início de cada janela, com sensibilidade obrigatória 0 / 0,5 / 1,0 BTC;
    *   os dois entram na lista de "Limites fixos" da Q1 e no arquivo congelado.
*   ***Proposed Edit:*** Q1, §7 e S6.

### [M13] [`egm-structural`, `egm-style`, `egm-design`] - Severity: Medium
*   **Affected Scope:** l. 42, 158, 207, 266, 300, 387
*   **Discrepância:** "reserva" tem dois sentidos, e a l. 387 usa "reserva do ciclo", que é a alternativa rejeitada A15.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** "reserva-base" fica só para o caixa de compras. O valor de fallback passa a se chamar "valor fixo de contingência". Na l. 387: "Y% da reserva-base".

### [M14] [`egm-style`; também comprehension 1] - Severity: Medium
*   **Affected Scope:** l. 15–16, 95–97, 142–147, 153, 185, 359–374
*   **Discrepância:** as letras A/B/C/D são reutilizadas para conceitos diferentes.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** glossário logo após a tabela de reconciliação. Nomes únicos:
    *   **Escada de venda** (antiga "C");
    *   **Detector de reversão** (D);
    *   **Armamento por ATH / por score ≥ 60 / por score > 35**;
    *   **Compra pelo score / Compra uniforme / Compra por queda do ATH**;
    *   **Normalização fixa / por limites altos / por percentil / híbrida (D2)**.

    Substituir as letras no texto. As opções originais ficam como "(opção C na Q5)" só onde é histórico de decisão.

### [M15] [`egm-structural`, `egm-style`, `egm-design`] - Severity: Medium
*   **Affected Scope:** Open Questions (l. 92–189), tabela da l. 12–16
*   **Discrepância:** a seção "Open Questions" contém quase só decisões, e a Q4 está superada mas continua aberta.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    *   Renomear a seção para "Decisões registradas e questões abertas", com a subseção "Decisões (Q1–Q3, Q5, Q5a, Q6, Q7, Q9)" e a subseção "Ainda abertas (Q5b, Q8)".
    *   Q4: "Superada pela Q5a e pelo §6".
    *   Pôr a Q8 antes da Q9 (N1).
    *   Atualizar a tabela do topo.

### [M16] [`egm-style`, `egm-structural`] - Severity: Medium
*   **Affected Scope:** l. 266
*   **Discrepância:** os exemplos de `source` citam fontes que não alimentam mais o modelo.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** `source` ∈ {`coinmetrics_live`, `coinmetrics_frozen`}; `fixed_fallback` deixa de existir; Dune e yfinance têm selos próprios só na UI.

### [M17] [`egm-style`, `egm-design`] - Severity: Medium
*   **Affected Scope:** l. 133, 149, 308–309
*   **Discrepância:** ATH e máxima de 52 semanas são definidos ora sobre o diário, ora sobre o semanal.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** `reference_ath_usd`, o armamento e a máxima de 52 semanas usam o **fechamento semanal**. Texto: "novo máximo do `cummax` do fechamento semanal".

### [M18] [`egm-style`] - Severity: Medium
*   **Affected Scope:** l. 37, 43, 46, 48, 57, 71, 161, 427, 433, 559, 580
*   **Discrepância:** linguagem subjetiva, como "honesto" e "escolhidos a dedo".
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** usar as substituições sugeridas no critic_report (M18).

---

## Nits

| # | Sugestão | Justificativa / Edição |
|---|---|---|
| N1 | PROPOSE FIX | Q8 antes da Q9 (feito junto com M15). |
| N2 | PROPOSE FIX (parcial) | Corrigir `indicators.py:44` → `:45`. Recusado padronizar todos os caminhos: ganho baixo. |
| N3 | PROPOSE FIX | `../../bitsignal/ingestion.py#L216`. |
| N4 | PROPOSE FIX | Citar "Technical Plan (Architecture), §7" e incluir as variantes da Q5b no §7. |
| N5 | PROPOSE FIX | Recuar a tabela e acrescentar "vale o maior degrau atingido". |
| N6 | DECLINE | Os títulos H2 seguem o template EGM em inglês. Réguas e o termo "drawdown" não afetam a leitura. |
| N7 | PROPOSE FIX | Nome único: `replay(history, config) -> ReplayResult`. |
| N8 | PROPOSE FIX | Intervalo usa o domínio real de cada insumo (Hash Ribbon ∈ {10, 20, 50}). |
| N9 | PROPOSE FIX | CUJ 1: semana disponível na segunda-feira, como no §3. |
| N10 | PROPOSE FIX | "a preços entre 7% e 47% do valor do pico". |
| N11 | PROPOSE FIX | Especificar a base de cada indicador no §3. |
| N12 | PROPOSE FIX | Listar só as Q decididas na tabela do topo. |
| N13 | PROPOSE FIX | Q9: "Decidido como hipótese experimental". |
| N14 | PROPOSE FIX | Q8: "Correção definida (§8); confirmar no app publicado". |
| N15 | PROPOSE FIX | Definir STOP_2, C0, "gauge" e "variante mínima" no primeiro uso. |
| N16 | PROPOSE FIX | Padronizar em 2010-07-18 e explicar o aquecimento à parte. |
| N17 | PROPOSE FIX | "Simulação da carteira com saldos de BTC e caixa". |
| N18 | DECLINE | "100%" é a forma numérica de "≥ DCA uniforme". Ambiguidade baixa. |
| N19 | PROPOSE FIX | "atual (até 2026-11-07): 1,17×". |
| N20 | PROPOSE FIX | "≤ 10 s" e repetir o valor nos NFRs. |
| N21 | PROPOSE FIX | Remover o tom coloquial. |
| N22 | PROPOSE FIX | Título "Benchmarks (Q1) e variantes de compra (Q9)". |
| N23 | DECLINE | A definição de venda prematura é intencional (+50% depois da venda). Basta manter "subir mais 50% depois da venda". |
| N24 | DECLINE | "Reason for Rejection" é campo do template. |

Recusas adicionais: N6, N18, N23, N24. Total de DECLINE: 4 Nits integrais + 2 parciais (N2 e N6 parcial).

---

## Rodada 2 (critic_report_r2.md): resolução

Situação: 0 Blocker, 10 Majors. Todos foram corrigidos no documento em 2026-11-08, sem nova reauditoria da Etapa 7 (limite de 1 reauditoria). A conferência fica com a Etapa 8.

- **design-r2-1:** a carteira contínua herda a catraca sem executá-la e só vende incrementos.
- **design-r2-2:** a sobra de caixa da Q9 foi decidida pelo dono: **manter o caixa**, como política experimental fixada antes do teste. O DCA uniforme segue a mesma regra, e a compra da sobra fica só como comparação. A S6 não tem mais escolha pendente.
- **design-r2-3:** os números da Q5b vêm de `docs/reviews/bitcoin_unified_cycle_model/sev.py`. As regras de episódio foram alinhadas ao script: um episódio novo exige armamento válido, não um ATH novo, e o episódio não termina quando o armamento expira.
- **design-r2-4:** novo estado `desatualizado` (última semana completa com mais de 9 dias) e remoção do bloco `integrity:` do config.
- **design-r2-5:** a aba mostra a variante padrão e os benchmarks; as demais variantes ficam no CLI.
- **design-r2-6:** a execução usa o `PriceUSD` de segunda-feira, com sensibilidade na terça.
- **structural-r2-1:** as tags M# foram removidas do texto; uma linha de rastreabilidade foi adicionada no cabeçalho.
- **structural-r2-2:** "## Glossário" passou a ser H2.
- **style-r2-1:** nomes únicos `V_esc` / `V_det`.
- **style-r2-2:** `run_model()` chama `replay()`, e o G1 diz isso.
- **Nits:** n1–n7, structural-n1 a n5 e style-n1 a n7, n9 a n14 foram aplicados. structural-n6 (convenção de réguas e idioma dos H2) e style-n8 (redação do uso comercial, parcial) ficaram como estão.

---

## Etapa 8 (intermediate_zoom_out_report.md): resolução antes da reauditoria

- **A1 (corrigido):** a semana entra no modelo quando há `PriceUSD` no domingo; as outras séries podem faltar e viram insumo ausente (§3, §4). "Aquecimento" e "ausente" passam a ser estados separados.
- **A2 (corrigido):** o §5 passa a ser a fonte única do detector. Episódio novo exige um disparo armado, não um ATH novo. O episódio não fecha quando o armamento expira. N3 exige N2 atingido antes ou na mesma semana. O `sev.py` foi reescrito com exatamente essas regras (versão 2026-11-08); os níveis por episódio ficaram idênticos aos da versão anterior. Os itens 18 e 22 foram alinhados.
- **A3 (corrigido):** a tabela única de variantes do §7 coincide com o `VARIANTS` (item 26), incluindo `minimal` (item 26b novo). As sensibilidades ficam separadas. O `BacktestConfig` ganhou `execution_lag_days` e `frozen_params`. O enum de normalização tirou `percentile` (descartada).
- **A5 (corrigido):** as Decisões Q1–Q9 registram só a decisão, o motivo, os limites e o § da regra. As regras operacionais ficam só no Technical Plan (§2–§8), que prevalece em caso de divergência.
- **A4 (CONTESTADO):** a herança do estado do modelo é decisão do dono (Q1, "Carteira e capital"). Começar o replay em ~mai/2014 perderia o armamento do detector pelo ATH de nov/2013 e faria o replay do painel diferir do do backtest. O §7 deixa claro que herdar o estado não executa vendas retroativas.
- **A6 (CONTESTADO em parte):** a tela sem veredito com histórico em memória e o botão de nova tentativa são decisão do dono (opção c+). O intervalo de 30 s virou parâmetro técnico configurável (`retry_cooldown_s`), sem efeito nas regras financeiras.

---

## Etapa 8, reauditoria (intermediate_zoom_out_report_r2.md): resolução

A Etapa 8 já usou sua única reauditoria. As correções abaixo serão conferidas pela Etapa 9. Erro de contagem no relatório: o A5 foi contado duas vezes. A contagem certa é Resolvido 5, Parcial 6, Contestado 5, Pendente 4.

**Majors:**
- **M1:** o `model_hash` (SHA-256 do JSON canônico) cobre só os blocos de modelo. `data`, UI/rede, caminhos, `frozen_params` e o próprio hash ficam fora (§7, itens 6, 31 e 32).
- **M2:** agregação semanal do Hash Ribbon no §2. O cruzamento usa `≥` e vale de segunda a domingo; o estado é calculado só depois que a semana fecha (itens 3 e 16).
- **M3:** novo arquivo esperado `tests/golden/detector_episodes.json`, gerado pelo `sev.py --csv` só com semanas fechadas; o teste roda offline (itens 22 e 22b).
- **M4:** tabela de variantes com regra completa (`arm_score60`/`35`, `thr_±5`, `minimal`, `floor40`/`60` → cap, `leftover_buy`). A `reset_dd60` saiu do conjunto executável por falta de regra de saída e fica registrada como pendente.

**Nits:**
- N1 (ordem e janela do N2 no §5), N2 (atraso remete ao §3), N3 (`retry_cooldown_s` no `DataConfig`; item 32 remete ao §8), N4 (A8 remete ao §6; item 19 implementa o §6 com nomes únicos), N5 (rótulo "detector A" removido; híbrida tirada das hipóteses) e N6 (Q3 remete ao §6; cabeçalho completo) foram aplicados.

**Itens herdados:**
- **E5-5:** `validate_for_panel` recusa no painel opções que só servem para o backtest.
- **E5-8:** aviso fixo no painel antigo na S0, e linha nova na tabela de riscos.
- **E5-12:** `CapConfig` passou a ter só `floor`.
- **E5-13:** o item 19 deixou de repetir as regras e implementa o pseudocódigo do §6.
- **A4:** o motivo foi escrito na Q1.

---

## Etapa 9 (implementation_readiness_report.md): classificação e resolução

Decisão do dono (2026-11-08): resolver com o agente e **dividir a entrega em duas fases**. A Fase 1 tem o modelo padrão, o painel e o backtest essencial com os testes técnicos, o congelamento e os critérios da Q1. A Fase 2 tem as variantes de comparação. As decisões Q1–Q9 não mudam. O Plano de Implementação foi reescrito para a Fase 1 (itens 1–45, etapas S0–S9 com dependência e critério de aceite por etapa).

**Blockers (4): todos são defeitos reais, corrigidos com a nova ordem das etapas**
- codebase-details-r1-1: `fetch-history` entra no S3 (item 16); `backtest` novo no S5 (item 33); `freeze-params` e `--record` no S6 (item 35); `evaluate` no S7 (item 38). O S8 só remove.
- codebase-details-r1-2: o golden do detector é gerado e testado no S5 (item 27). O S4 testa o detector só com séries sintéticas.
- codebase-details-r1-3: o `sev.py` reescrito é independente (não usa `probe.py` nem `bitsignal`), funciona offline com `--csv`, usa só semanas fechadas e tem schema JSON definido. A conferência é feita contra os 6 casos da Q5b.
- style-r1-1: o teste de paridade foi para o S4 (item 25), antes do congelamento.

**Majors (25)**
- **Corrigidos no plano da Fase 1 (defeito real):**
  - ir-r1-1: antes do S6 só a janela de calibração; o `approval` é gravado uma única vez.
  - ir-r1-5: schema `FrozenParams`/`Approval`, serialização do `model_hash`, `load_frozen` e o selo na UI.
  - ir-r1-6: `simulate` com preço diário, curva diária, fallback de 7 dias e `ratchet_at_start`.
  - ir-r1-7: `uniform_complete` definido.
  - ir-r1-8: fórmulas de todos os diagnósticos.
  - cd-r1-5: YAML literal completo, com `extra="forbid"` e nomes canônicos.
  - cd-r1-6: `data_status` com chamador e testes de 8 e 10 dias.
  - cd-r1-7: `BacktestReport` e as assinaturas.
  - cd-r1-8: `min_periods` igual à janela, calendário sem ffill, `rsi_wilder` sem `fillna(50)` e primeira semana sem ATH.
  - cd-r1-9: funções vetoriais nomeadas.
  - cd-r1-10: `cmd_ui` aponta para `streamlit_app.py` no S0.
  - cd-r1-11: `sys.path` mantido até o S9, que testa no Cloud; empacotamento decidido (extra `ui`, `-e .[ui]`).
  - cd-r1-12: o Dune é copiado, não movido.
  - style-r1-2: nomes do Hash Ribbon unificados e agregação testada.
  - style-r1-3: tabela de enums código → rótulo.
  - style-r1-4: colunas de `weeks` completas.
  - style-r1-5: convenção de colunas diárias e semanais.
  - style-r1-6: sensibilidades com fonte única no config; URL e métricas viraram constantes.
  - style-r1-7: `validate_for_panel` com lista exata, chamado no item 37 e testado nos itens 10 e 39.
  - style-r1-8: lista única de testes que bloqueiam.
  - style-r1-9: as regras do detector ficam fixas no código, e o config só tem os percentuais; `apply_overrides` definido.
- **Transferidos para a Fase 2:**
  - ir-r1-2 (`ladder_only`);
  - ir-r1-3 (`norm_high`/`norm_hybrid`);
  - ir-r1-4 e cd-r1-4 (`minimal`).

  As questões ficam listadas em "Fase 2" no plano e marcadas como Fase 2 no §7.

**Nits (17):** N1–N17 foram incorporados na reescrita do plano (nomes, decimais, seed fixa, `MarketHistory.truncate`, SITEMAP com Modify/Superseded, `.env.example`, `--cov-fail-under`, remoção do `load_config` antigo, `NormalizedMetricScore`, cabeçalho do `probe.py`, regra de compra com taxa).

**Riscos aceitos:** nenhum novo. **Limitações históricas:** continuam as da Etapa 8 (E5-1, um topo de calibração; E5-2, números exploratórios).

---

## Etapa 9, reauditoria (implementation_readiness_report_r2.md): resolução final

Decisão do dono (2026-11-08): **corrigir e concluir**. Não haverá nova rodada EGM; esta é a conferência interna do autor. O status continua *Proposed*, e a Fase 1 **não** recebeu aprovação independente da Etapa 9 depois destas correções.

**Rodada 1 (situação após a reauditoria):** 21 resolvidos, 4 parciais (ir-r1-5, ir-r1-8, cd-r1-5 e style-r1-9, fechados abaixo pelos achados da rodada 2 correspondentes) e 4 transferidos para a Fase 2.

**Blockers (2): corrigidos**
- **ir-r2-1:** a invariante virou identidade exata, com a taxa descontada do valor bruto (compra `−fee·usd`; venda `−fee·q·preço`). Conferida com dois exemplos numéricos, que estão no item 28 e são cobertos por teste no item 34.
- **ir-r2-4:** a aba Backtest só mostra a janela 2019+ quando há arquivo congelado com hash igual. Sem isso, mostra a calibração com aviso, sem erro. O selo vem só do `approval` gravado. "Critérios gravados uma única vez; recálculos são só exibição" (§7, CUJ 3, §8, Verification Plan).

**Majors (16): corrigidos**
- **ir-r2-2:** `to_weekly(..., cfg)`, colunas `trend_sma`/`n2_sma`; `picycle_bottom` usa o fator do config; os números do detector vêm do config.
- **ir-r2-3:** regra da semana do fechamento no §5, mais testes.
- **ir-r2-5:** sensibilidades sem checagem de hash, "não aplicável" fora da janela, data → primeira semana W-SUN ≥ data, `base_btc` definido.
- **ir-r2-6:** o S8 ajusta `tests/test_indicators.py`; `is_picycle_bottom_triggered` sai no S8; nome correto do teste.
- **ir-r2-7:** o teste de reserva foi para `test_backtest.py`; `test_cycle.py` testa `buy_pct` independente de `cycle_id`.
- **ir-r2-8:** tabela de eventos e regra do `reason`.
- **ir-r2-9:** `per_cycle`, unidade de venda falsa e exclusão de janelas futuras incompletas.
- **ir-r2-10:** critérios de aceite do S4/S5 com os itens corretos.
- **ir-r2-11:** URLs, parâmetros e caminho JSON do catálogo.
- **cd-r2-6:** pontos de injeção do painel e patches do teste.
- **cd-r2-7:** `tests/test_cli.py` (recusas do S6) e `tests/test_dune.py`.
- **cd-r2-8:** `.github/workflows/ci.yml` e sem `addopts` de cobertura; `freeze-params` com `--no-cov`.
- **cd-r2-9:** `compare_histories` no `fetch-history`.
- **st-r2-3:** padrão `calibration` e exibição lado a lado depois do S6.
- **st-r2-7:** `MODEL_BACKTEST_FIELDS` e `model_payload`.
- **st-r2-8:** RSI com NaN nas posições 0–13 (conferido com pandas) e preço constante → NaN.

**Nits (33):** 26 aplicados. Os 7 restantes (cd-r2-23, st-r2-14, st-r2-15, st-r2-25a/b/d/e) estão no "Checklist de implementação" do documento.
