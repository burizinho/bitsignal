# Relatório de revisão Goldfish: Zoom Out intermediário (Etapa 8)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md` (linhas 1–1136; FeatureRange 1..711, DetailedRange 712..1136)
**Padrão:** `zoom-out-standard.md`
**Base de comparação:** `D:/Projetos Gui/BitSignal/zoom_out_report.md` (Etapa 5). Os relatórios das rodadas anteriores servem só como histórico. Eles não são autoridade sobre o design.

## Situação dos revisores

| Revisor | Situação |
| --- | --- |
| `egm-zoom-out` | concluído (uma instância) |

## Veredito

O design ainda não está pronto para aprovação.

O documento agora é honesto sobre a evidência que tem:
- a janela de desenvolvimento aparece como contaminada;
- o topo de 2013 é declarado não avaliável;
- a Q5b virou política fixa;
- a S6 virou um passo de congelamento;
- os Objetivos e as CUJs foram reescritos.

Por outro lado, o documento cresceu de 1010 para 1136 linhas. Os registros de decisão Q1–Q9 repetem regras normativas das §4–§7. Essa duplicação já gerou contradições reais na política do detector, justamente a parte que esta rodada diz ter congelado (veja A2). Os achados de simplicidade da Etapa 5 seguem abertos ou só foram corrigidos em parte.

**Contagem dos achados novos:** 0 🔴 Blocker, 6 🟡 Major, 6 🟢 Nit.

---

## Situação dos achados da Etapa 5

| # | Achado da Etapa 5 (severidade original) | Situação | Evidência no documento atual |
| --- | --- | --- | --- |
| 1 | A calibração promete uma evidência que os dados não dão; a S6 não tem como ser decidida (🔴) | **Parcial** | Ver detalhe 1 abaixo. |
| 2 | Os números não são reproduzíveis; o probe mede outro modelo (🟡) | **Parcial** | Ver detalhe 2 abaixo. |
| 3 | Duas entregas de natureza diferente no mesmo design (🟡) | **Não resolvido** (em parte aceito via A22) | Ver detalhe 3 abaixo. |
| 4 | A alternativa mais simples foi prometida e depois abandonada (🟡) | **Parcial** | Ver detalhe 4 abaixo. |
| 5 | Variantes rejeitadas entram no config e no engine de produção (🟡) | **Não resolvido** | Ver detalhe 5 abaixo. |
| 6 | Modo `intervalo` e fonte de hashrate contraditória (🟡) | **Parcial** | Ver detalhe 6 abaixo. |
| 7 | Objetivos e CUJs descrevem o brief, não as decisões (🟡) | **Resolvido** | Ver detalhe 7 abaixo. |
| 8 | O painel antigo continua mostrando ordens erradas durante S1–S6 (🟡) | **Não resolvido** | Ver detalhe 8 abaixo. |
| 9 | Dune como "conferência" é código mantido sem efeito nas decisões (🟡) | **Aceito como decisão**, mas sem resposta ao argumento de custo | Ver detalhe 9 abaixo. |
| 10 | "Questões em aberto" parece ata de reunião; a Q4 já estava respondida (🟢) | **Parcial** | Ver detalhe 10 abaixo. |
| 11 | yfinance só para mostrar o "preço agora" (🟢) | **Aceito como decisão** | Ver detalhe 11 abaixo. |
| 12 | Constantes de implementação no YAML do usuário; retry escrito à mão (🟢) | **Não resolvido** | Ver detalhe 12 abaixo. |
| 13 | A ordem das regras aparece duas vezes (🟢) | **Não resolvido, e piorou** | Ver detalhe 13 abaixo. |
| 14 | Pequenas imprecisões (🟢) | **Parcial** | Ver detalhe 14 abaixo. |

### Detalhes por achado

**1. Calibração e S6 (Parcial)**
- Resolvido:
  - A G3 tem três janelas, e a de desenvolvimento aparece como "não é amostra independente" (L86).
  - A Q1 marca a janela como contaminada (L133).
  - O topo de 2013 é declarado não avaliável (L469).
  - A Q5b virou política fixa (L187–201).
  - A S6 virou congelamento (L722, L1010–1017).
  - O acompanhamento prospectivo é a única evidência independente (L141, L200, L698).
- Não resolvido: o backtest não foi reduzido.
  - A §7 ainda lista cerca de 11 famílias de variantes (L470–480).
  - `VARIANTS` tem 14 entradas (L966–975).
  - A Q1 acrescenta sensibilidades: reserva 0/0,5/1,0 (L148), entrada tardia (L149) e execução na terça (L454).

**2. Números e probe (Parcial)**
- Resolvido:
  - Os números estão marcados como exploratórios (L66, L503) e a Q9 manda refazê-los (L241).
  - O `sev.py` está versionado (L198).
  - Os valores de nov/2021 estão delimitados (L68, L546, L559).
- Não resolvido:
  - O `sev.py` roda o `probe.py`, então herda dele a imputação de 50 para insumos ausentes e a semana aberta de `resample("W-SUN").last()`. Mesmo assim, a Q5b diz que ele usa "as mesmas regras" (L198).
  - O degrau de 93 não foi reconferido em amostragem semanal sem imputação (L24, L388).
  - O `sev.py` não implementa o N3 do documento (ver A2).

**3. Duas entregas no mesmo design (Não resolvido, em parte aceito via A22)**
- A A22 (L680–684) aceita um painel "experimental" sem passar pelos critérios financeiros.
- A limpeza do painel ainda espera o pipeline de pesquisa (S4–S5) antes da S7.
- Não existe divisão em Fase 1 e Fase 2 (L712–725).

**4. Alternativa mais simples (Parcial)**
- Resolvido: a variante mínima aparece no glossário (L38), na §7 (L476), na CUJ 3 (L297) e na A2 (L522).
- Não resolvido:
  - Ela não está em `VARIANTS` (L966–975).
  - Ela não tem limiares definidos.
  - Não há a cláusula "se o modelo completo não vencer a regra simples, fica a regra simples".
  - O critério 3 continua com um nome enganoso, porque só avalia compras (L91, L128).

**5. Variantes rejeitadas na produção (Não resolvido)**
- Opções rejeitadas continuam no config de produção:
  - `arming` B e C (L773);
  - `reset_mode: drawdown_60` (L775);
  - `buys.mode`/`leftover` (L776);
  - o enum `fixed | d2 | percentile` (L975), embora o percentil tenha sido descartado na Q5 (L173).
- O teste das "três regras de armamento" continua previsto (L915).
- A meta de cobertura de 90% (L1124) acaba cobrindo ramos rejeitados.

**6. Modo `intervalo` e hashrate (Parcial)**
- Hashrate: resolvido, com o `HashRate` da CoinMetrics (L224, L338).
- O score de três estados continua em L97, L213, L272–279, L390–394 e L863.
- Agora esse estado é inalcançável (ver A1).

**7. Objetivos e CUJs (Resolvido)**
- G1 (L75), G5 (L97), CUJ 1/1b (L259–270), CUJ 2a/2b (L272–288), CUJ 3 (L295–297) e CUJ 4 (L304).
- Pendência pequena: o estado `desatualizado` não aparece na G5 (N4 abaixo).

**8. Painel antigo durante S1–S6 (Não resolvido)**
- Seguem a regra "o painel continua funcionando em cada commit" (L102, L708, L714) e o paliativo `created_at` (L758–761).
- A S0 não traz banner nem oculta a aba "Plano Nacional" (L729–739).

**9. Dune (Aceito como decisão, sem resposta ao custo)**
- Está decidido (L15, L109, L225).
- Mesmo sem efeito nas decisões, continua presente em:
  - módulo (L828–834);
  - secrets (L706, L1090);
  - `python-dotenv` (L1099);
  - README (L1108);
  - E2E (L1134).

**10. Seção de questões (Parcial)**
- Resolvido: a seção foi renomeada (L115), só a Q8 continua aberta (L245–247) e a Q4 foi fechada (L170).
- Não resolvido: cerca de 130 linhas de decisões (L117–243) repetem regras normativas (ver A5).

**11. yfinance (Aceito como decisão)**
- Ver L15, L341, L676 e L826.
- O uso na tela de indisponibilidade (L206) ajuda a justificá-lo.

**12. Constantes no YAML e retry (Não resolvido)**
- `DataConfig` com URL, lista de métricas e `page_size` (L778).
- `CapConfig` com um campo só (L774).
- Caminho padrão `parents[1]` (L769).
- Loop escrito à mão no lugar de `tenacity` (L1099), embora `ingestion.py:8` já use `tenacity`.

**13. Ordem das regras duplicada (Não resolvido, e piorou)**
- As duas cópias continuam: §6 (L416–436) e S4 (L881–887).
- A cópia da S4 está incompleta. Faltam:
  - as guardas de `indisponível`;
  - a regra de que semanas indisponíveis não contam;
  - a regra de que a semana de reinício pula a escada e o detector (L427).

**14. Pequenas imprecisões (Parcial)**
- A referência `indicators.py:45` foi corrigida.
- A frase "trava 15% do peso do score em 0" (L62) ainda exagera. Isso acontece em cerca de 75% dos dias, não sempre.

---

## Achados priorizados (Blocker → Major → Nit)

### A1. Os estados `intervalo` e "indisponível com preço" não podem ocorrer pela regra semanal do próprio documento - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:** L358 e L852, contra L203, L213, L272–279, L360, L390–394, L863 e L910–911.
* **Descrição da discrepância:**
  * Duas regras descartam semanas incompletas:
    * L358: a semana só entra quando a linha do domingo existe para **todas** as séries;
    * L852: `to_weekly` "só mantém semanas cujo domingo tem todas as colunas não nulas".
  * Então a falta de `HashRate` ou de MVRV/Puell num domingo (o exemplo da CUJ 2a, L274) apaga a semana. Ela nunca gera `intervalo`.
  * Já a L360 diz que, no aquecimento, o insumo "conta como ausente pela Q6", o que pressupõe que a semana é mantida.
  * Resultado: o mecanismo de três estados e o caminho "detector segue só com preço" ficam inalcançáveis, ou existem só no aquecimento de 2010–2014. O comportamento fica indefinido.
* **Justificativa e recomendação:**
  * Adotar a regra que o documento já tem: uma semana só conta se todos os insumos forem válidos, e o modelo começa na primeira semana totalmente válida.
  * Reduzir o status a `ok | sem veredito` (mais `desatualizado`).
  * Isso permite remover:
    * a CUJ 2a;
    * `score_min`/`score_max`;
    * o parágrafo de "ausência secundária" da Q6 (L213);
    * o ramo "indisponível com preço" (L203, L286);
    * `ScoreStatus.interval` e os testes dele (L910–911).

### A2. A política do detector da Q5b, descrita como "congelada", tem três definições diferentes - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:** L193, L197, L201, L400–401, L773, L871, L918, `sev.py`.
* **Descrição da discrepância:**
  * **Novo episódio:**
    * a Q5b (L197) e a §5 dizem que um novo episódio "exige só armamento válido de novo, não um ATH novo";
    * a S4 (L871) diz que "um episódio novo exige um ATH novo depois do fechamento do anterior";
    * o teste da L918 verifica "episódio novo só depois de ATH novo".
  * **Condição do N3:**
    * a Q5b (L193) e a §5 (L400) definem "N2 ativo e fechamento ≤ 60%". Como o nível é pegajoso dentro do episódio, isso permite disparar com o fechamento acima da SMA50w;
    * o config (`below_sma50w_2w_and_le_60pct_high52`, L773) e o `sev.py` (`below50&(w<=0.6*hi52)`) exigem as duas condições na mesma semana;
    * o custo citado, "N3 veio a ~56%" (L201), vem da semântica do `sev.py`, não da tabela da Q5b.
* **Justificativa e recomendação:**
  * O teste golden (L1003–1006) vai congelar a versão que for implementada. Por isso, essa questão precisa ser decidida antes da S4.
  * Escolher uma definição para cada regra e escrevê-la uma única vez, na §5.
  * Alinhar L871, L918 e L773 a essa definição.
  * Rodar o `sev.py` de novo e atualizar a L201.

### A3. As variantes da §7, o `VARIANTS` e as sensibilidades não batem - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:** L470–480 contra L966–975; L148, L149, L454, L777, L935, L1017.
* **Descrição da discrepância:**
  * A variante mínima está na §7 (L476), mas não em `VARIANTS`, e não tem regras definidas (L38, L516).
  * A §7 cita SMA20w e SMA30w (L479); `VARIANTS` só tem `sma20`.
  * `leftover_keep`/`leftover_buy` (L974) aparecem como variantes, mas o descarte da sobra já foi decidido (L242).
  * As sensibilidades de reserva (L148), de entrada tardia (L149) e de execução na terça (L454, L935) não estão no catálogo.
  * `execution_lag_days` (L935) e `frozen_params` (L1017) não estão em `BacktestConfig` (L777).
* **Justificativa e recomendação:**
  * Fazer da §7 a lista única e deixar `VARIANTS` apenas referenciá-la.
  * Incluir a variante `minimal` com limiares pré-registrados antes da S6.
  * Cortar as entradas de baixo valor: `C+D_B`, `C+D_C`, `normB`, `D2` e `reset_dd60`. Isso também resolve os itens 1 e 5 da Etapa 5.

### A4. Herança da catraca e carteira de entrada tardia: um segundo mecanismo que o problema não pede - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:** L145, L149, L450, L941, L1000.
* **Descrição da discrepância:**
  * O replay começa em 2010, mas a carteira contínua começa no meio do ciclo (~mai/2014). Para compensar a catraca já elevada pelo topo de 2013, o documento cria `baseline_ratchet` e a fórmula `max(0, ratchet_t − ratchet_at_start)`.
  * A entrada tardia repete o mesmo mecanismo para 2019.
  * A aprovação já usa a curva contínua rebaseada em 100 em 2019-01-01 (L147). A carteira tardia responde quase à mesma pergunta e não decide nada (L149).
* **Justificativa e recomendação:**
  * Começar o replay na primeira semana totalmente válida, o que decorre de A1. Assim a carteira principal não herda estado.
  * Remover o diagnóstico de entrada tardia, ou deixá-lo como uma nota de uma linha, sem teste próprio (L1000).
  * Com isso, o parâmetro `baseline_ratchet` e dois parágrafos saem do documento.

### A5. Regras normativas duplicadas entre os registros de decisão e as seções técnicas - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:**
  * Q1 (L119–151) contra G4 (L88–93), §7 (L449–486) e CUJ 3;
  * Q5a/Q5b (L179–201) contra §5 (L396–401);
  * Q2/Q3 (L152–169) contra §6 (L403–445);
  * §6 (L416–436) contra S4 (L881–887).
* **Descrição da discrepância:**
  * A2, o item 13 da Etapa 5 e o conflito do campo do cap (N5) são falhas de sincronia causadas por essa duplicação.
  * A maior parte das 126 linhas acrescentadas desde a Etapa 5 está nesses registros.
* **Justificativa e recomendação:**
  * Cada registro de decisão deve guardar só a decisão, a data, o motivo e um link para a seção que define a regra.
  * A regra fica num lugar só, nas §4–§7.
  * A S4 deve referenciar a §6 em vez de repetir a ordem dos passos.
  * Isso deve cortar cerca de 100 linhas e eliminar toda uma classe de contradições.

### A6. Tela de indisponibilidade complexa demais para um painel de um usuário, só de leitura - Severidade: 🟡 Major
* **Lente do revisor:** `egm-zoom-out`
* **Escopo afetado:** L204–210, L287, L498, L1033.
* **Descrição da discrepância:**
  * O documento acrescenta:
    * um histórico obsoleto em `st.session_state`, usado só nos gráficos de contexto;
    * um botão de nova tentativa que limpa o cache;
    * um intervalo mínimo de 30 s entre cliques;
    * a regra de que esse histórico nunca alimenta o `replay()`.
  * Nada disso é necessário. O `st.cache_data` não guarda exceções, então recarregar a página já tenta de novo. O limite da CoinMetrics já é tratado na §2.
* **Justificativa e recomendação:** quando a fonte estiver indisponível, mostrar a mensagem, o horário da tentativa e o preço do yfinance. Remover o histórico em `session_state`, o botão e o throttle.

### N1. O título da S6 contradiz o conteúdo - Severidade: 🟢 Nit
* **Escopo:** L1008 contra L722.
* **Descrição:** o título "Ponto de decisão do dono e congelamento" conflita com "Não há escolha pendente".
* **Recomendação:** renomear para "Congelamento".

### N2. A janela de "calibração" não calibra nada - Severidade: 🟢 Nit
* **Escopo:** L86, L168, L482, L485, L777 (`calibration_end`), L980.
* **Descrição:** todos os parâmetros são política fixa e nada é ajustado na S6 (L1015).
* **Recomendação:** renomear para "período pré-2019 (só relatório)", ou eliminar a janela e manter os diagnósticos por evento.

### N3. "Desempenho histórico aprovado" vem de uma janela que o próprio documento chama de contaminada - Severidade: 🟢 Nit
* **Escopo:** L140, L147.
* **Descrição:** o rótulo pode ser lido como validação independente.
* **Recomendação:** usar na tela um rótulo com a ressalva, por exemplo "aprovado na validação de desenvolvimento (não independente)".

### N4. A G5 não tem o estado `desatualizado` - Severidade: 🟢 Nit
* **Escopo:** L97 e L390 contra L211.
* **Descrição:** a G5 e a §4 listam só `ok | intervalo | indisponível`, mas a Q6 cria `desatualizado`.
* **Recomendação:** incluir `desatualizado`. O ponto perde o sentido se A1 for adotado.

### N5. Conflito no nome do campo do cap - Severidade: 🟢 Nit
* **Escopo:** L774 contra L153, L414, L477, L970.
* **Descrição:** `CapConfig.max_sell = 0.50` convive com `cap = 1 − floor` "do config" e com as variantes `floor40`/`floor60`.
* **Recomendação:** manter um único campo (`floor` ou `max_sell`) e eliminar a classe `CapConfig` (item 12 da Etapa 5).

### N6. Reuso: a classificação do Hash Ribbon e o retry já existem - Severidade: 🟢 Nit
* **Escopo:** L749, L1099; `bitsignal/ingestion.py:8` e `:182–186`; `bitsignal/models.py:8`.
* **Descrição:**
  * O documento cria um novo `hash_ribbon_state`, mas a classificação já existe em `ingestion.py:182–186`, e `HashRibbonState` existe em `models.py:8`.
  * O documento troca `tenacity`, já usado em `ingestion.py:8`, por um loop escrito à mão.
* **Recomendação:** dizer que a nova função em série reaproveita a lógica existente, e manter o `tenacity`.

---

## Resumo de escopo e complexidade

**O que cortar ou fundir, em ordem de retorno:**
1. Reduzir o status do score a `ok | sem veredito` e começar o modelo na primeira semana totalmente válida (A1, A4). Isso remove a CUJ 2a, o intervalo, o `baseline_ratchet` e os casos especiais de aquecimento.
2. Deixar nos registros de decisão só a justificativa (A5).
3. Enxugar `VARIANTS` e os enums de produção, deixando só o caminho escolhido (item 5 da Etapa 5, A3).
4. Remover o histórico em `session_state` e o botão com throttle (A6).
5. Remover o módulo Dune, ou registrar explicitamente por que o custo dele compensa (item 9 da Etapa 5).

**O que deve ficar:**
- o glossário;
- a tabela de reconciliação (L9–17);
- a tabela de Riscos e Mitigações (L686–699);
- a regra de 9 dias para `desatualizado` (L211);
- a defasagem de execução com a sensibilidade de terça (L454);
- a decisão de manter o caixa que sobra (L242), que é simples e foi tomada antes do teste.
