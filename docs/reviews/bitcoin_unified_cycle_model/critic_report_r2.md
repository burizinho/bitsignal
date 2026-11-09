# Relatório de Revisão Goldfish — Rodada 2 (re-auditoria após correções)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md` (linhas 1–701, até antes de "## Detailed Implementation Plan"; o plano detalhado não foi revisado)
**Estágio:** 7 (Critic Review), egm-review-loop, rodada 2
**Padrão:** `C:/Users/gsame/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/feature-spec-standard.md` (design e estrutural); padrão padrão da persona (estilo, aplicado como prosa técnica em português)
**Relatório da rodada 1:** `D:/Projetos Gui/BitSignal/critic_report.md` (mantido intacto; usado só para checar a situação de B1 e M1–M18)

## Situação dos revisores

| Revisor | Situação | Achados brutos |
| --- | --- | --- |
| `egm-design` | completed | 0 Blocker, 6 Major, 9 Nit |
| `egm-structural` | completed | 0 Blocker, 3 Major, 7 Nit |
| `egm-style` | completed | 0 Blocker, 3 Major, 32 Nit |

Depois da deduplicação ficaram **0 🔴 Blocker, 10 🟡 Major e 27 🟢 Nit**.

**Veredito:** PRECISA DE REVISÃO. Não há Blocker. Todas as seções obrigatórias do padrão agora existem: Problem Statement (l. 51), Goals (l. 68), Non-Goals (l. 99), Proposed Architecture (l. 303), Alternatives Considered (l. 492) e Risks & Mitigations (l. 677).

---

## Contradições NOVAS introduzidas pelas correções

1. **IDs de revisão inseridos no texto, dois deles errados** (structural-r2-1). A l. 183 rotula Q5b como "M5" e a l. 481 rotula a linha do topo como "M11". Na rodada 1, esses temas eram outros achados.
2. **Q9 aparece como "Decidido" e como "em aberto"** (design-r2-2). A sobra de caixa está sob "Decisões", mas as l. 16, 146 e 235 dizem que está aberta. "Ainda abertas" (l. 238) não a lista.
3. **Três conjuntos de nomes para as metas de venda** (style-r2-1). A l. 150 usa `V_escada`/`V_detector`, a l. 419–421 usa `V_esc`/`V_det`/`V_det_eff` e a l. 563 usa `V_C`/`V_D`.
4. **CUJ 3 contra §8 sobre o que a aba de backtest calcula** (design-r2-5). A l. 286–290 diz "todas as variantes"; a l. 488 diz "só a padrão + benchmarks".
5. **Q2 contra §8 sobre como a compra é exibida** (design-r2-n1). A l. 154 diz "linha separada"; a l. 481 põe venda e compra numa linha só.
6. **CUJ 3 "por janela" contra Q1** (structural-r2-n1). Na l. 142, a aprovação usa só a janela 2019+.
7. **"Aprovado" com dois sentidos** (design-r2-n3). Na l. 14 é um rótulo de decisão de projeto; nas l. 135, 288, 301 e 477 é o status do backtest.

---

## Achados priorizados

### 🔴 Blocker

Nenhum.

### 🟡 Major

#### design-r2-1 — A carteira contínua começa no meio de um ciclo e não há regra de herança da catraca
* **Lente:** `egm-design`
* **Linhas:** 140, 144, 353, 441, 460
* **Discrepância:** O replay começa em 2010-07-18 (l. 353). A carteira contínua começa só na primeira semana com os seis insumos válidos, por volta de mai/2014 (l. 140, 441). No início de 2014, o detector já pode estar armado pela ATH de 2013 e ter disparado, com a catraca em 10–50% num `cycle_id` anterior à carteira. O documento não diz se a carteira vende `catraca × posição-base` na primeira semana ou se herda a catraca sem executá-la. A regra `max(0, catraca_t − catraca_na_entrada)` existe só para o cenário de entrada em 2019 (l. 144).
* **Justificativa:** A carteira de aprovação é normalizada em 2019-01-01 (l. 142), mas o caminho BTC/caixa de 2014 a 2018 alimenta essa carteira. Essa escolha não declarada muda os critérios 1–3.
* **Correção sugerida:** Aplicar à carteira contínua a regra da l. 144: na entrada, herda a catraca sem executar e vende só os incrementos. A alternativa é iniciar a carteira no primeiro reset efetivo depois de ~mai/2014. Registrar a escolha em Q1 e no §7.

#### design-r2-2 — A sobra de caixa (Q9) continua aberta, sem critério de decisão pré-registrado, e ficou fora de "Ainda abertas"
* **Lentes:** `egm-design` (D2), `egm-structural` (S2-3), `egm-style` (Nit 28)
* **Linhas:** 16, 146, 235, 238–240, 435, 461, 687
* **Discrepância:** A tabela de riscos (l. 687) depende de uma "variante padrão pré-registrada". Porém o destino da sobra de caixa no reset (comprar tudo ou manter) está "em aberto (experimento)" (l. 235) e precisa ser fechado "antes do teste definitivo" (l. 146). Não há métrica, janela nem prazo para essa decisão. O item está sob "Decisões", e "Ainda abertas" lista só Q8.
* **Justificativa:** Se a escolha for feita olhando os resultados de 2019+, os critérios de aprovação passam a ser escolhidos a posteriori, que é o overfitting que o próprio documento diz evitar (l. 106, 138). A lista de questões abertas está incompleta, e o problema de M15 volta em outra forma.
* **Correção sugerida:**
  - Fixar a regra agora, por exemplo: "decidido apenas na janela de calibração ≤ 2018-12-31 pelo patrimônio final em USD; em empate, manter a sobra". A alternativa é congelar uma opção como padrão e rodar a outra só como comparação.
  - Incluir essa regra nos "Limites fixos" de Q1.
  - Adicionar a "Ainda abertas": "**Q9b — Destino da sobra de caixa ao fim de ACUMULAR.** Em aberto; decidido por experimento (regra acima) antes do teste definitivo."
  - Na l. 235, remeter ao item novo em vez de repetir o texto.

#### design-r2-3 — A evidência de Q5b não pode ser reproduzida, e a regra de fim de episódio pode impedir o N3
* **Lente:** `egm-design`
* **Linhas:** 182, 191, 193, 195, 392
* **Discrepância:**
  - As l. 182, 193 e 195 citam números da política congelada: falsos positivos parados em N1; N3 atingido em 2018, 2022 e depois de 2025; N3 a ~56% da máxima de 52 semanas em 2022; quedas de −57% e −38%. O `probe.py` não implementa o detector N1–N3; tem só EMA21w/SMA50w com armação por score (probe.py, l. 47–60).
  - O §5 (l. 392) acrescenta duas regras que Q5a/Q5b não citam: o episódio termina após 2 fechamentos acima da SMA30w, e um novo episódio exige uma nova ATH. Com essas regras, um rali de bear market (por exemplo, mar–abr/2022) encerraria o episódio antes de N2/N3 e bloquearia o N3 até a próxima ATH, contradizendo a l. 193.
  - O documento não diz se a escalada para N2/N3 continua exigindo armação válida quando a ATH tem mais de 52 semanas.
* **Justificativa:** A severidade do detector é uma decisão central, e hoje se apoia em números sem fonte revisável.
* **Correção sugerida:** Versionar em `docs/reviews/bitcoin_unified_cycle_model/` o script que gerou os números de Q5b, já com as regras de episódio do §5, ou marcar as l. 193/195 como "não verificado". Repetir em Q5b as regras de fim de episódio e de expiração da armação.

#### design-r2-4 — Não há modo de falha para uma fonte que responde mas parou de atualizar
* **Lente:** `egm-design`
* **Linhas:** 197–198, 252, 351–352, 681; `config/config.yaml` l. 40–44
* **Discrepância:**
  - O §3 diz que, enquanto a linha de domingo não existe, "o modelo usa a semana anterior", sem limite. Se a CoinMetrics continuar respondendo mas parar de publicar, o painel mostra um veredito de semanas atrás como atual, com estado `ok`.
  - Q6 e a tabela de riscos não cobrem esse caso.
  - O `config.yaml` ainda tem `fresh_threshold_hours: 36`, `expired_threshold_hours: 48` e `imputed_neutral_score: 50.0`. O último contradiz Q6 diretamente, e o documento não diz o destino desse bloco.
* **Justificativa:** Um veredito velho exibido como válido é o pior modo de falha para o usuário.
* **Correção sugerida:**
  - Definir o limite de defasagem, por exemplo: "se a última semana W-SUN completa for mais de 8 dias anterior a agora (UTC), estado = `desatualizado`, sem veredito".
  - Incluir esse estado em Q6, no CUJ 2 e na tabela de riscos.
  - Declarar o destino do bloco `integrity:` (remover, ou reinterpretar para a cadência semanal).

#### design-r2-5 — CUJ 3 e §8 divergem sobre o que a aba de backtest calcula
* **Lente:** `egm-design`
* **Linhas:** 286–290, 461–471, 488, 695
* **Discrepância:** O CUJ 3 diz que a aba mostra todas as variantes do §7, inclusive a mínima e os limiares ±5. O §8 (l. 488) diz que a aba calcula ao vivo só a variante padrão e os benchmarks. São mais de 15 execuções, e o NFR (l. 695) orça cerca de 1 s para uma única execução.
* **Justificativa:** É uma contradição nova sobre escopo, com impacto no cold start.
* **Correção sugerida:** No CUJ 3, escrever "CLI: todas as variantes; aba do painel: padrão + benchmarks (§8)". A alternativa é dar à aba um orçamento de desempenho e um plano de cache para todas as variantes.

#### design-r2-6 — O backtest executa a um preço que o usuário não consegue obter
* **Lente:** `egm-design`
* **Linhas:** 248, 350–352, 445, 675
* **Discrepância:** As operações são executadas "no fechamento da semana do sinal", isto é, no mesmo fechamento de domingo que gera o sinal. Pelo §3, essa semana só fica utilizável na segunda-feira, por causa da defasagem de ~1 dia da CoinMetrics.
* **Justificativa:** O preço de execução otimista alimenta os critérios 1 e 3 e a afirmação de paridade (l. 675).
* **Correção sugerida:** Executar no próximo `PriceUSD` diário disponível depois que a semana fica utilizável (fechamento de segunda). A alternativa é manter o domingo e exigir uma rodada de sensibilidade com execução em t+1.

#### structural-r2-1 — IDs de achados da revisão (M3, M5, M11, M12…) vazaram para o texto, e alguns estão errados
* **Lentes:** `egm-structural` (S2-1, S2-10), `egm-style` (S2-3)
* **Linhas:** 138, 139, 154, 183, 198, 280, 436, 441, 481, 489, 681
* **Discrepância:**
  - "(M12, abaixo)", "(revisão, M5)", "(Q6, M3)" e "formato único, M11" apontam para o `critic_report.md`, não para o documento. Não existe nenhuma seção "M12" (l. 138).
  - A l. 183 atribui Q5b a "M5", mas na rodada 1 o M5 tratava de calibração com um só topo e do preenchimento com 50.
  - A l. 481 atribui o formato da linha do topo a "M11", mas esse tema era o M6. O M11 tratava da semântica de ACUMULAR.
* **Justificativa:** Um leitor novo não consegue resolver essas referências, e elas amarram a especificação a um artefato de revisão que não é versionado com ela.
* **Correção sugerida:**
  - Remover todas as tags M#.
  - Na l. 138, escrever "(ver 'Carteira e capital', abaixo)".
  - Na l. 139, escrever "**Carteira e capital (decidido em 2026-11-08):**".
  - Na l. 481, escrever "**Linha do topo (formato único):**".
  - Se a rastreabilidade importar, acrescentar uma linha no cabeçalho: "Revisão de 2026-11-08 incorporada; ver `critic_report.md`."

#### structural-r2-2 — Nível de título pulado no glossário
* **Lente:** `egm-structural`
* **Linhas:** 1, 18
* **Discrepância:** "### Glossário" (H3) vem logo depois do H1, sem H2 entre eles.
* **Justificativa:** Pular nível de título quebra a hierarquia e a navegação, e é um critério de auditoria da persona estrutural.
* **Correção sugerida:** Promover a "## Glossário", ou criar "## Contexto e glossário" contendo a nota de reconciliação e o glossário.

#### style-r2-1 — Três conjuntos de nomes para as variáveis da meta de venda, um deles com as letras C/D aposentadas
* **Lentes:** `egm-style` (S2-1), `egm-design` (D7), `egm-structural` (S2-6)
* **Linhas:** 150, 419–421, 563
* **Discrepância:** A l. 150 usa `V_escada`/`V_detector`, o pseudocódigo usa `V_esc`/`V_det`/`V_det_eff`, e A8 (l. 563) usa `min(50%, max(V_C, V_D))` com teto fixo de 50%, quando a l. 150 diz que o teto é `cap`.
* **Justificativa:** O problema voltou durante a correção de M14. O leitor não sabe se são as mesmas variáveis.
* **Correção sugerida:**
  - L. 150: "A meta de venda é `V_alvo = min(cap, max(V_esc, V_det))`."
  - L. 563: "Ficou o piso de 50% com teto compartilhado `min(cap, max(V_esc, V_det))`."

#### style-r2-2 — Dois nomes para a função principal: `run_model` e `replay`
* **Lentes:** `egm-style` (S2-2), `egm-design` (D8), `egm-structural` (S2-7)
* **Linhas:** `run_model`: 70, 310, 323. `replay()`: 201, 207, 214, 396, 429, 445, 522, 634, 695
* **Discrepância:** G1 e o §1 definem `run_model(history, config) -> ReplayResult`. O restante do documento usa `replay()` e nunca diz como as duas se relacionam. O N7 da rodada 1 mudou de lugar mas não foi corrigido.
* **Justificativa:** O contrato público da arquitetura fica ambíguo.
* **Correção sugerida:** Escolher uma das duas formas e aplicá-la ao documento inteiro:
  - Usar um nome único (`run_model()`), deixando "replay" só como termo coloquial.
  - Ou definir uma vez no §1: "`run_model()` chama `replay()`, a máquina de estados semanal do §6."

### 🟢 Nit

| ID | Linhas | Discrepância | Correção sugerida |
| --- | --- | --- | --- |
| design-r2-n1 | 154, 481, 90, 252 | Q2 diz que a compra aparece em "linha separada"; o §8 põe venda e compra na mesma linha, separadas por "·". Não está definido o que o campo de compra mostra fora de ACUMULAR ou com score `indisponível`. | Alinhar o texto ao §8 e definir o campo como "—" nesses casos. |
| design-r2-n2 | 410–412, 225–229, 430 | A regra "semanas `indisponível` não contam nem zeram" existe só em comentário; as atribuições zeram `arm_count`/`confirm_count` sempre. A tabela de Q9 usa "Score semanal", enquanto o pseudocódigo usa `score_max`. A l. 430 diz "score ≥ 85". (D10, S2-5, style 7–8) | Envolver as atribuições em `se status != indisponível:`. Renomear a coluna para "`score_max` semanal". Na l. 430, escrever "`score_min` ≥ 85". |
| design-r2-n3 | 14, 135, 288, 301, 477 | "Aprovado (decisão de projeto)" colide com o "APROVADO" do backtest. (D15, S2-8, style 3) | Renomear o rótulo para "**Decidido**". |
| design-r2-n4 | 191 | Não está claro se o N3 é avaliado na mesma semana que o N2 ou só numa semana posterior. Essa regra precisa coincidir entre painel e backtest. (D11, style 15) | Declarar "no máximo um nível por semana" ou "todos os níveis avaliados em ordem na mesma semana". |
| design-r2-n5 | 342, 370 | O mapeamento razão SMA30/SMA60 → estados BUY_RECOVERY/CAPITULATION/NORMAL não está especificado. No `probe.py`, BUY_RECOVERY dura um dia e quase nunca cai num domingo. Na tabela, o mapeamento está na coluna "0 em" e "—" na coluna "100 em". (D12, style 19, 31) | Definir cada estado e sua duração. Pôr o mapeamento numa nota abaixo da tabela. |
| design-r2-n6 | 267 | O exemplo "Hash Ribbon em aquecimento" do CUJ 2a não ocorre ao vivo, porque o HashRate existe desde 2009. | Trocar por "SMA200w antes de mai/2014 (backtest)" ou "série X sem linha na semana". |
| design-r2-n7 | 199, 683 | "Ignorando o cache que falhou" não descreve o `st.cache_data`, que não guarda exceções. Cliques repetidos podem estourar o limite de 10 req/6 s. (D14, style 20) | Escrever "um botão que limpa o cache da busca e refaz a consulta", com cooldown. |
| structural-r2-n1 | 288, 142, 477 | O CUJ 3 relata os critérios "por janela", mas a aprovação usa só a janela 2019+. (S2-4, style 16) | Escrever "na janela de aprovação 2019+ (Q1); as demais janelas aparecem só como relatório". |
| structural-r2-n2 | 674–675 | "Metas de exposição" é o termo anterior a Q2. "Rejeitada só em parte" continua no campo de rejeição (N24 da rodada 1). (S2-8, style 2) | Escrever "metas de venda acumulada". Renomear o campo para "**Decisão:** Aceita com restrição…". |
| structural-r2-n3 | 634 | "Desde ~2011" contradiz 2010-07-18 (N16 parcial). | Escrever "desde 2010-07-18". |
| structural-r2-n4 | 654 | "Honesto sobre a amostra pequena" é linguagem subjetiva que restou do M18. | Escrever "Não depende de limites fixados com amostra pequena." |
| structural-r2-n5 | 494, 512 | A nota "números citados em A4–A15 são exploratórios" deixa de fora os múltiplos exploratórios de A2. | Escrever "A2–A15". |
| structural-r2-n6 | 36, 691, 700, 482, 316–326, H2s | Réguas horizontais irregulares (N6 parcial). Há espaço sobrando no fim da l. 482. Só um H2 está em português ("Decisões registradas e questões abertas"). O mermaid usa caminhos relativos ao pacote e a prosa usa `bitsignal/…` (N2 parcial). | Adotar uma convenção única para réguas, idioma dos H2 e caminhos. Remover o espaço sobrando. |
| style-r2-n1 | 40 | "Recomenda ter vendido" contradiz a l. 154, que diz que o painel nunca usa "vendido". | Escrever "a venda acumulada-alvo do ciclo, em % da posição-base". |
| style-r2-n2 | 90, 198, 201, 280, 310, 324, 481, 681 | A mesma saída tem cinco nomes: veredito, recomendação, linha de ação, linha do topo e ação da semana. | Usar "linha do topo" para o elemento de UI e "veredito" para a saída do modelo. Incluir "Veredito" no glossário. |
| style-r2-n3 | 106, 294, 300 | "Faixa" sobrou do vocabulário antigo; o glossário usa limiar/degrau. | Título do CUJ: "CUJ 4: Ajustar um limiar". Na l. 106, escrever "Otimizar os limiares". |
| style-r2-n4 | 177, 187–192, 356, 390–391 | Três rótulos para a máxima de 52 semanas. | Definir na l. 192 e usar só "máxima de 52 semanas". |
| style-r2-n5 | 629 | "CoinMetrics de reserva" volta ao sentido de "reserva" que o M13 aposentou. | Escrever "como contingência". |
| style-r2-n6 | 340 | As siglas MC e RC não são definidas. | Escrever "MVRV Z = (`CapMrktCurUSD` − realized cap) / desvio-padrão expansivo de `CapMrktCurUSD`". |
| style-r2-n7 | 541 | O rótulo "(D2)" não é definido. (D7) | Remover, ou escrever "(D2 do brief)". |
| style-r2-n8 | 16, 220, 685, 697 | O uso comercial é descrito de quatro formas diferentes. | Usar em todas a redação da l. 685 ("bloqueado até haver licença"). |
| style-r2-n9 | 66, 206, 455, 529 | Trechos ambíguos ou não mensuráveis:<br>• l. 66: "sobre dados" pode ser lido como "informação sobre os dados".<br>• l. 206: "quase equivale a congelar" não é mensurável.<br>• l. 455: N23 não resolvido.<br>• l. 529: em "7% do pico", não fica claro se é nível de preço ou distância. | • L. 66: "sem dados sintéticos e sem informação futura".<br>• L. 206: "o intervalo tem 10 pontos de largura, o que bloqueia novos degraus em 85–93".<br>• L. 455: "% vendida a preço ≤ 2/3 da máxima posterior (venda prematura)".<br>• L. 529: "a 7% do preço do pico". |
| style-r2-n10 | 153 | "Guarda" colide com "Nada é gravado" (l. 396, 429). | Escrever "Mantém em memória o estado simulado das vendas em cada execução." |
| style-r2-n11 | 63, 254, 559 | Expressões coloquiais. | • L. 63: "Com os limites atuais".<br>• L. 254: "O painel não mostra valores em BTC nem em R$".<br>• L. 559: "reduz a exposição num topo que o score não detecta". |
| style-r2-n12 | 64 | "Tende a ser bloqueada" é vago. | Escrever "a API da Binance responde HTTP 451 a IPs dos EUA". |
| style-r2-n13 | 85, 138, 147 | Três problemas de redação:<br>• l. 85: "≥ 10 p.p." mistura símbolo com prosa.<br>• l. 138: "qual carteira decide" soa estranho.<br>• l. 147: repete G4. | • L. 85: "pelo menos 10 p.p.".<br>• L. 138: "a carteira que decide a aprovação".<br>• L. 147: remover a repetição de G4. |
| style-r2-n14 | 460 | A lista de eventos mistura topos e fundos fora de ordem. | Ordenar cronologicamente: fundo 2015, topo dez/2017, fundo 2018, topo abr/2021, topo nov/2021, fundo 2022, topo out/2025. |

---

## Situação dos achados da rodada 1

| Item | Situação | Evidência (uma linha) |
| --- | --- | --- |
| B1 | Resolvido | A l. 217 define o `HashRate` da CoinMetrics como fonte e remove o Mempool. A l. 331 declara fonte única, e as l. 333 e 344 trazem "5 séries" e o teste de paridade. |
| M1 | Resolvido | "Risks & Mitigations" está nas l. 677–689, com Risco/Impacto/Mitigação/Onde. Falta uma linha para fonte desatualizada (design-r2-4). |
| M2 | Resolvido | A l. 197 trata o caso com preço presente (o detector segue) e a l. 198 o caso da CoinMetrics fora do ar (sem score nem detector). Q7 e o CUJ 2b concordam. |
| M3 | Resolvido | As l. 198–204 e 489 usam `st.session_state` só para gráficos, sem veredito. |
| M4 | Resolvido | Três janelas consistentes (l. 81, 128, 473–476). Sem walk-forward (l. 476). Lista de eventos única (l. 460). |
| M5 | Resolvido | 2013 é declarado não avaliável e 2017 o único topo (l. 460). Os números exploratórios estão rotulados (l. 61, 234, 494). Nova lacuna sem probe: design-r2-3. |
| M6 | Resolvido (resíduo) | Formato único na l. 481, citado nas l. 90 e 252. Resta o "linha separada" da l. 154 (design-r2-n1). |
| M7 | Resolvido | O CUJ 2a/2b (l. 265–281) usa só ok/intervalo/indisponível. |
| M8 | Resolvido (resíduo) | As l. 288–290 trazem critérios → diagnósticos → variantes, sem "acerto". Restam o "por janela" (structural-r2-n1) e o conflito com o §8 (design-r2-5). |
| M9 | Resolvido | `config/frozen/` com verificação de hash (l. 285, 301, 488). Edição depois do congelamento invalida a aprovação. |
| M10 | Resolvido (resíduo) | As l. 405–426 trazem a ordem de avaliação, `V_det_eff`, `score_min`/`score_max` e `cap`. A guarda de `indisponível` existe só em comentário (design-r2-n2). |
| M11 | Resolvido | Semântica nas l. 154, 436 e 482, e CUJ 1b nas l. 256–263. |
| M12 | Resolvido | As l. 138–145 fixam data, reserva, carteira decisora e sensibilidade. A referência "(M12, abaixo)" está quebrada (structural-r2-1), e a herança da catraca falta (design-r2-1). |
| M13 | Resolvido | "Reserva-base" está no glossário (l. 28) e "valor fixo de contingência" nas l. 60 e 205. Há uma recaída na l. 629 (style-r2-n5). |
| M14 | Parcial | O glossário (l. 18–34) substituiu as letras, mas `V_C`/`V_D` continuam na l. 563 e "(D2)" na l. 541 (style-r2-1, style-r2-n7). |
| M15 | Parcial | Houve a divisão entre Decisões e Ainda abertas, e Q4 está marcado como superado (l. 166). A sobra de caixa de Q9 falta em "Ainda abertas" (design-r2-2). |
| M16 | Resolvido | A l. 336 define `source` ∈ {`coinmetrics_live`, `coinmetrics_frozen`} e remove `fixed_fallback`. |
| M17 | Resolvido | ATH e máxima de 52 semanas são definidas sobre o fechamento semanal (l. 161, 175, 192, 356, 389–391). |
| M18 | Parcial | As l. 55, 64, 134 e 528 foram corrigidas; "Honesto" permanece na l. 654 (structural-r2-n4). |

**Resumo (19 itens):**
- **16 resolvidos:** B1, M1–M13, M16 e M17. Três deles (M6, M8 e M10) ainda têm um resíduo de nível Nit.
- **3 parciais:** M14, M15 e M18.
- **Nenhum não resolvido.**

**Nits da rodada 1 ainda pendentes:**
- N23 (l. 455)
- N24 (l. 675)
- N16, parcial (l. 634)
- N6 e N2, parciais
- N7, agora coberto por style-r2-2
