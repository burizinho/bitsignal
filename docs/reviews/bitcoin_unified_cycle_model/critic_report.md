# Relatório de Revisão Goldfish — Stage 7 (Critic Review), rodada 1

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md`, linhas 1–591. A revisão vai do início do arquivo até antes de `## Detailed Implementation Plan`, que não foi revisado.
**Padrão:** `C:/Users/gsame/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/feature-spec-standard.md`. Vale para os revisores design e structural; o style usou o padrão da própria persona e avaliou o texto como prosa técnica em português.

## Status dos revisores

| Revisor | Status | Veredito do revisor |
| --- | --- | --- |
| `egm-design` | completed | NOT READY (1 Blocker, 12 Major, 6 Nit) |
| `egm-structural` | completed | NEEDS REVISION (7 Major, 8 Nit) |
| `egm-style` | completed | REVISÃO NECESSÁRIA (11 Major, 20 Nit) |

## Resumo

Depois de juntar os achados repetidos entre revisores, ficaram **1 🔴 Blocker, 18 🟡 Major e 24 🟢 Nit**.

Cada achado consolidado mantém os ids originais dos revisores. Onde os revisores deram severidades diferentes ao mesmo problema, usei a maior. A única exceção está indicada no próprio achado.

O tema que mais se repete: várias seções ainda descrevem a arquitetura anterior às decisões Q1–Q9. Isso aparece na G3, nos CUJs 1–4, no §8 linha 387, na linha 266 e no pseudocódigo do §6.

---

## 🔴 Blockers

### B1. A fonte do hashrate quebra a paridade entre painel e backtest
* **Ids:** `egm-design-r1-1`, `egm-style-r1-7`
* **Linhas:** 265, 267, 172, 274, 580
* **Discrepância:**
  * No painel, o hashrate vem do Mempool.space (linha 265). O endpoint configurado é `/mining/hashrate/3m` (`config/config.yaml:71`), então só cobre uns 3 meses.
  * No backtest, o hashrate vem da série `HashRate` da CoinMetrics, no CSV congelado (linha 267).
  * Mesmo assim, a linha 274 afirma: "Painel e backtest usam a mesma fonte e as mesmas funções".
  * A linha 172 diz "as 5 séries", mas o painel só consome 4 séries da CoinMetrics.
* **Por que importa:**
  * O `replay()` do painel reconstrói a catraca e os ciclos desde 2010.
  * Com só 3 meses de hashrate, o Hash Ribbon (peso de 10%) fica ausente em quase todas as semanas históricas.
  * Pela Q6, essas semanas caem no modo "intervalo". Nesse modo, a escada C só sobe se `score_min ≥ 85`.
  * Resultado: a catraca, os resets e o `cycle_id` do painel vão divergir dos do backtest.
  * Assim, o teste de paridade que a linha 580 exige antes de mostrar a exposição-alvo não tem como passar.
* **Correção sugerida:**
  * Usar o `HashRate` da CoinMetrics também no painel.
  * Manter o Mempool.space só como conferência de exibição, como já é feito com o Dune.
  * Ajustar as linhas 265–266 e 172, e declarar no §2 que todo insumo do modelo vem exclusivamente da CoinMetrics.

---

## 🟡 Major

### M1. Falta a seção obrigatória "Risks & Mitigations"
* **Ids:** `egm-structural-r1-1`, `egm-design-r1-12`
* **Linhas:** todo o escopo. Os riscos aparecem espalhados nas linhas 108, 152, 154, 157, 171, 172, 424, 586 e 588.
* **Discrepância:** o padrão exige que modos de falha, limites de escala e as mitigações de cada um sejam declarados explicitamente. Hoje há riscos sem mitigação e riscos que não aparecem em lugar nenhum:
  * a CoinMetrics é ponto único de falha, tanto para preço quanto para on-chain;
  * a CoinMetrics pode revisar dados históricos, e aí o replay ao vivo diverge do CSV congelado;
  * o Streamlit Cloud sai por IPs compartilhados, então o limite de 10 req/6 s por IP pode gerar erros 429;
  * o yfinance é um scraper não oficial;
  * comparar ~15 variantes numa janela contaminada leva a overfitting;
  * a licença CC BY-NC;
  * o catálogo gratuito da CoinMetrics pode perder séries;
  * o disco do Streamlit é efêmero.
* **Correção sugerida:**
  * Criar `## Risks & Mitigations` entre Alternatives Considered e Non-Functional Requirements, com uma tabela `Risco | Impacto | Mitigação | Onde é tratado (Q#/§#)`.
  * Incluir nas mitigações:
    * teste de paridade na janela sobreposta, com tolerância explícita;
    * diff de revisões contra o CSV congelado;
    * backoff para 429;
    * variante padrão pré-registrada (C + D armado por ATH), com as demais marcadas como só para comparação.

### M2. Contradição: o detector D continua rodando se a CoinMetrics falhar?
* **Id:** `egm-design-r1-2`
* **Linhas:** 157 e 171, contra 263
* **Discrepância:**
  * A Q6 (linha 157) e a Q7 (linha 171) dizem que "o detector D continua".
  * O §2 (linha 263) diz que, se a CoinMetrics falhar, "score e detector ficam indisponíveis".
  * A linha 262 define o `PriceUSD` da CoinMetrics como único preço do modelo. Logo, a linha 263 é a coerente: sem CoinMetrics, D não roda.
* **Correção sugerida:** separar dois casos e corrigir a Q6 e a Q7 conforme eles:
  * (a) falta parte do on-chain, mas o `PriceUSD` está presente: D continua;
  * (b) a CoinMetrics caiu inteira: score e D ficam indisponíveis.

### M3. O "último valor bom em cache" não é viável com o cache escolhido
* **Id:** `egm-design-r1-3`
* **Linhas:** 157, 213, 394, 87
* **Discrepância:**
  * O CUJ 2 e a Q6 prometem mostrar o último score válido junto com a idade dele.
  * Mas persistência é Non-goal (linha 87), e o único cache é `st.cache_data` com ttl de 6 h (linha 394).
  * O `st.cache_data` descarta a entrada quando o TTL vence e não guarda exceções. Além disso, o Streamlit Cloud reinicia ou suspende o processo, o que limpa a memória.
  * Ou seja: se a CoinMetrics estiver fora no momento do refresh, não sobra histórico nenhum para mostrar.
* **Correção sugerida:** escolher e documentar um modo degradado, e depois reescrever o CUJ 2 e a Q6 de acordo. Opções:
  * (a) uma cópia "último bom" em memória, sem expiração, separada do refresh de 6 h;
  * (b) usar o CSV congelado do repositório como reserva, com o selo "histórico congelado até dd/mm";
  * (c) aceitar a tela vazia e dizer isso no CUJ 2.

### M4. As janelas de calibração e validação estão incoerentes
* **Ids:** `egm-design-r1-4`, `egm-structural-r1-5`, `egm-style-r1-5`, `egm-structural-r1-13`
* **Linhas:** 63, 70, 88, 105, 108, 136, 220, 310, 380–382
* **Discrepância:**
  * A G3 (linha 63) diz "calibra até 2017 e testa 2021 e 2022 fora da amostra".
  * O §7 calibra até 2018-12-31.
  * A Q1 (linha 108) e o §7 classificam 2019+ como "validação histórica de desenvolvimento, não amostra independente". Mesmo assim, as linhas 88 e 136 ainda falam em "fora da amostra".
  * A linha 310 cita um "walk-forward" cujos folds não estão definidos em lugar nenhum.
  * A lista de eventos de diagnóstico muda conforme a seção:
    * G4 (linha 70): 2017/2021/2022/2025;
    * Q1 (linha 105): nov/2021, 2022 e pós-topo de 2025;
    * CUJ 3 (linha 220): 2017/2021/2022.
* **Correção sugerida:**
  * Reescrever a linha 63 com os termos do §7: "calibração até 2018-12-31; 2019 → congelamento é validação de desenvolvimento (não é amostra independente); validação prospectiva após o congelamento".
  * Nas linhas 88 e 136, trocar "fora da amostra" por "antes da validação".
  * Definir os folds do walk-forward ou tirar o termo da linha 310.
  * Usar uma única lista de eventos nas linhas 70, 105 e 220.

### M5. A calibração só tem um topo utilizável, e as evidências da probe usaram preenchimento com 50
* **Id:** `egm-design-r1-5`
* **Linhas:** 283, 380, 157–159, 43–45, e os números das alternativas A4, A5 e A7
* **Discrepância:**
  * A SMA200w só é válida a partir de ~2014-05, então está ausente no topo de 2013. Ela pesa 20%.
  * Com 20 pontos ausentes, o `score_min` chega no máximo a 80, e a escada C (que exige ≥ 85) nunca dispara em 2013.
  * Ao contrário do que diz a linha 380, só o topo de 2017 é utilizável para calibrar a venda.
  * A `probe.py` (linhas 25–27) calculou o score com funções que preenchem dados ausentes com 50: `normalize_linear(None)` retorna 50 (`normalizer.py:20–21`) e o RSI recebe `fillna(50)` (`indicators.py:31`). É exatamente o preenchimento que a G3 proíbe.
* **Correção sugerida:**
  * No §7, declarar quais eventos são avaliáveis depois do aquecimento, para C e para D.
  * Dizer explicitamente que a calibração de C se apoia em um único topo.
  * Refazer as evidências da probe sem o preenchimento com 50, ou rotular os números atuais como "calculados com preenchimento 50".

### M6. A linha do topo do painel tem três formatos diferentes, e o CUJ 1 contradiz a Q2
* **Ids:** `egm-design-r1-6`, `egm-structural-r1-4` (parte do CUJ 1), `egm-style-r1-2`
* **Linhas:** 22, 48, 72, 201, 387, contra 127
* **Discrepância:**
  * A Q2 decidiu que o painel mostra a **exposição-alvo** ("manter X% da posição…"), não uma ordem incremental.
  * Mesmo assim, as linhas 22, 72 e 201 descrevem uma ordem incremental. O CUJ 1, por exemplo, diz "COMPRAR X% da reserva / VENDER Y% da posição / NADA".
  * A linha 387 usa um terceiro formato, e sem a faixa.
* **Correção sugerida:** definir um modelo único da linha do topo no §8 (já com a correção de M13) e fazer as linhas 22, 48, 72 e 201 citarem esse modelo.

### M7. O CUJ 2 descreve um cenário de falha que não existe mais
* **Ids:** `egm-design-r1-7`, `egm-structural-r1-4` (parte do CUJ 2), `egm-style-r1-4`
* **Linhas:** 207–213, 74
* **Discrepância:**
  * O Given ("O Dune não respondeu… e a reserva também falhou") descreve a arquitetura antiga.
  * Pela Q7, o Dune não alimenta o modelo. Pela Q6, valores fixos contam como ausentes.
  * Os selos "estimado" e "indicativo" (linhas 74, 210 e 211) não existem no vocabulário da Q6 nem do §4 (linha 300), que só tem `ok`, `intervalo` e `indisponível`.
  * A linha 213 ("último valor bom em cache") diverge da Q6 ("último score válido, marcado como desatualizado").
* **Correção sugerida:**
  * Dividir o CUJ 2 em dois:
    * (a) falta um insumo secundário: estado "intervalo", mostrando `score_min` e `score_max`;
    * (b) falta MVRV ou Puell, ou a CoinMetrics caiu: estado "indisponível", com o comportamento definido em M2 e M3.
  * Alinhar o vocabulário da G5 (linha 74) com o da Q6.

### M8. O CUJ 3 mede "acerto" por evento, que a Q1 rebaixou a diagnóstico, e deixa de fora os critérios de aprovação
* **Ids:** `egm-design-r1-8`, `egm-structural-r1-4` (parte do CUJ 3)
* **Linhas:** 217, 220–222, contra 100–107, 383, 551–555
* **Discrepância:**
  * O CUJ 3 mostra "acerto sim/não" por evento.
  * A Q1 e a A19 tratam o resultado por evento só como diagnóstico.
  * O CUJ 3 não menciona os três critérios cumulativos APROVADO / NÃO APROVADO (linha 383), os benchmarks, nem as variantes da Q9.
  * O termo "variante mínima" (linha 222) só é definido dentro da A2 (linha 418).
* **Correção sugerida:**
  * O Then deve listar primeiro os três critérios da Q1 por variante, comparando com comprar-e-segurar e com o DCA uniforme, e depois os diagnósticos.
  * Remover "acerto".
  * Remeter ao §7 para a lista de variantes.

### M9. O CUJ 4 (editar uma faixa e reexecutar) conflita com o congelamento, e o bloco `bands:` não existe
* **Ids:** `egm-design-r1-9`, `egm-structural-r1-14`, `egm-style-r1-31`
* **Linhas:** 225–231, contra 88, 118, 381, 393
* **Discrepância:**
  * O CUJ 4 incentiva editar `bands:` e diz que painel e backtest passam a usar o novo valor.
  * Mas a linha 381 congela os parâmetros, e a linha 88 proíbe ajuste fino.
  * A aba de backtest lê um resultado pré-computado (linha 393), mas o documento não diz onde ele fica nem como é gerado. Se alguém editar o config, o painel ao vivo e o backtest exibido passam a divergir sem nenhum aviso.
  * O `config/config.yaml` atual não tem bloco `bands:`, e o layout do config-alvo não é descrito em nenhuma parte do escopo.
* **Correção sugerida:**
  * Nomear o artefato pré-computado, o caminho dele e o comando que o gera.
  * Gravar no artefato o hash do config, e mostrar um aviso quando esse hash diferir do config em uso.
  * O CUJ 4 deve declarar que qualquer edição depois do congelamento invalida o status "aprovado" e a trilha prospectiva.
  * Descrever os blocos do config-alvo (`metrics`, `bands`, `detector`, `cycle`, `purchases`, `backtest`) ou remeter à etapa S2.

### M10. O pseudocódigo do §6 não aplica as regras escritas logo ao lado
* **Ids:** `egm-design-r1-10`, `egm-structural-r1-6`, `egm-style-r1-6`, `egm-style-r1-10` (parte "detector desligado")
* **Linhas:** 327–337, contra 341, 300–304, 128, 132, 390
* **Discrepância:**
  * A linha 329 aplica `max(ratchet_sell, V_C, V_D)` sempre. Isso ignora a regra da linha 341: com `reset_pending` ligado, D não pode elevar a meta.
  * O pseudocódigo usa um `score` genérico, quando o §4 exige `score_max ≤ 20` para armar, `score_min ≥ 30` para confirmar e o estado `indisponível`.
  * O teto de 50% está fixo no código, mas o piso é configurável (40/50/60, linha 128).
  * "Detector desligado" (linhas 132 e 331) não é nenhum dos estados da linha 390.
  * Não está definida a ordem de avaliação quando o reset e um sinal de C ou D caem na mesma semana.
* **Correção sugerida:**
  * Reescrever o pseudocódigo com:
    * a ordem de avaliação explícita;
    * a condição "V_D só conta se não `reset_pending`";
    * `score_min` / `score_max`;
    * `cap = 1 − floor` lido do config.
  * Trocar "detector desligado" por "sem episódio ativo do detector".

### M11. A exposição-alvo não tem semântica definida durante ACUMULAR
* **Id:** `egm-design-r1-11`
* **Linhas:** 127, 134–135, 341–345, 387
* **Discrepância:**
  * Durante `reset_pending`, o painel manda comprar BTC e ao mesmo tempo mostra "manter X% da posição do início do ciclo", calculado sobre a base do ciclo antigo.
  * Depois de comprar, o BTC do usuário fica acima do alvo exibido, o que se lê como uma ordem implícita de venda.
  * É exatamente a contradição entre compra e venda que o design quer eliminar (linha 37).
* **Correção sugerida:**
  * Definir se o alvo é um teto só sobre a base original, excluindo o BTC comprado em ACUMULAR, ou se o alvo fica oculto durante ACUMULAR.
  * Acrescentar um CUJ para a tela em ACUMULAR.

### M12. O critério de sucesso depende de parâmetros que não estão congelados
* **Id:** `egm-design-r1-13`
* **Linhas:** 97, 101–103, 118, 351, 355
* **Discrepância:**
  * O critério 1 compara o patrimônio final com comprar-e-segurar.
  * O benchmark converte a reserva em BTC no primeiro dia. A estratégia, ao contrário, deixa a reserva parada em caixa até ACUMULAR.
  * Por isso o resultado depende muito do tamanho da reserva (padrão "0,5 BTC") e da data de "início da avaliação". Essa data é ambígua: pode ser 2010-07-18, o fim do aquecimento ou 2019-01-01.
  * A linha 118 congela os limites, mas não esses dois insumos.
* **Correção sugerida:**
  * Fixar, no arquivo de parâmetros congelados, a data de início de cada janela e o tamanho da reserva.
  * Incluir os dois na lista "Limites fixos" da Q1.
  * Tornar o tamanho da reserva uma dimensão obrigatória de sensibilidade.

### M13. "Reserva" tem dois sentidos, e a linha 387 usa a "reserva do ciclo", que o próprio documento rejeitou
* **Ids:** `egm-structural-r1-7`, `egm-style-r1-3`, `egm-design-r1-16`
* **Linhas:**
  * no sentido de valor fixo de fallback: 42, 158, 207, 266, 300;
  * no sentido de caixa de compras: 129, 175, 184, 351, 387;
  * a alternativa rejeitada: A15, linhas 518–522.
* **Discrepância:**
  * A linha 387 diz "Y% da reserva do ciclo", que é justamente o texto da alternativa A15, rejeitada.
  * A Q9 define a "reserva-base" como sendo da campanha, sem renovação a cada ciclo.
  * Na linha 207, "a reserva também falhou" pode ser lida nos dois sentidos.
* **Correção sugerida:**
  * Na linha 387, escrever "Compras: Y% da reserva-base".
  * Usar "reserva-base" só para o caixa de compras.
  * Renomear o outro sentido para "valor fixo de contingência" nas linhas 42, 158 e 300.

### M14. As letras A/B/C/D nomeiam coisas diferentes
* **Id:** `egm-style-r1-1`
* **Linhas:** 15–16, 95–97, 142–145, 147, 153, 185, 359–360, 370–374
* **Discrepância:**
  * "C" nomeia quatro coisas: a escada de venda (Q5), o armamento por score > 35 (Q5a), o DCA pelo score (Q9) e a variante "C comprando toda a sobra".
  * "B" nomeia três: os limites altos, o armamento por score ≥ 60 e o DCA uniforme.
  * A linha 97 usa "compras B" antes de B ser definido (linha 185).
* **Correção sugerida:**
  * Dar nomes únicos, como VENDA-C, DETECTOR-D, ARM-ATH/ARM-60/ARM-35 e COMPRA-SCORE/COMPRA-UNIFORME/COMPRA-ESCADA-ATH.
  * Reunir esses nomes num glossário logo depois da linha 17.

### M15. "Open Questions" contém quase só decisões, e a Q4 continua aberta mesmo já superada
* **Ids:** `egm-structural-r1-3`, `egm-style-r1-9`, `egm-design-r1-19` (parte Q4)
* **Linhas:** 92–189, 138, 12–16
* **Discrepância:**
  * Das 11 questões, 8 estão marcadas como "Decidido".
  * A Q4 pergunta se a saída por tendência só vale dentro de DISTRIBUIR. Mas a Q5a (linha 148), a A11 (linha 496) e o §6 (linha 341) já definiram D como independente do score e fixaram a precedência.
  * A tabela de triagem das linhas 12–16 não inclui a Q4 nem a Q8.
* **Correção sugerida:**
  * Separar a seção em "Decisões (Q1–Q9)" e "Open Questions" (Q5b, Q8).
  * Marcar a Q4 como "Superada pela Q5a e pelo §6", ou removê-la.
  * Atualizar a tabela das linhas 12–16.

### M16. Os exemplos de `source` citam fontes que não alimentam mais o modelo
* **Ids:** `egm-style-r1-8`, `egm-structural-r1-8`
* **Linha:** 266
* **Discrepância:**
  * Os exemplos são `dune`, `yfinance` e `fixed_fallback`.
  * O Dune agora é só conferência (Q7), o yfinance é só exibição, e valor fixo conta como ausente (Q6).
* **Correção sugerida:** usar `coinmetrics` e `mempool` (este só como conferência, se B1 for aceito), e declarar que `fixed_fallback` deixa de existir.

### M17. As definições de ATH e de máxima de 52 semanas são inconsistentes
* **Ids:** `egm-style-r1-10` (parte ATH), `egm-design-r1-17`
* **Linhas:** 133, 149, 308–309
* **Discrepância:**
  * Na linha 133, o ATH é o `cummax` do preço diário. Na linha 308, é o do fechamento semanal.
  * A linha 309 não diz qual série usa para a máxima de 52 semanas.
  * O texto "máximo de `cummax`" é redundante.
* **Correção sugerida:**
  * Definir `reference_ath_usd`, o armamento e a máxima de 52 semanas sobre o fechamento semanal, ou declarar outra base explicitamente.
  * Escrever "novo máximo do `cummax` do fechamento semanal".

### M18. Linguagem subjetiva ou que não dá para medir
* **Id:** `egm-style-r1-11`
* **Linhas:** 37, 43, 46, 48, 57, 71, 161, 427, 433, 559, 580
* **Discrepância:**
  * "Honesto" aparece seis vezes como juízo de valor.
  * Também há "não conversam", "teste rápido", "escolhidos a dedo", "gasta recursos sem necessidade" e "claramente identificado".
  * As propriedades verificáveis já estão listadas no documento: sem dado sintético, sem informação futura, critério fixado antes.
* **Correção sugerida:**
  * Trocar "honesto" pelo critério concreto, por exemplo "backtest sem dados sintéticos e sem informação futura".
  * Linha 37: "Dois sistemas independentes".
  * Linha 433: "Sem limites fixados manualmente".
  * Linha 46: "reexecuta o pipeline inteiro a cada visita".
  * Linha 580: "identificado na tela como 'experimental'".

---

## 🟢 Nits

| # | Ids | Linhas | Discrepância | Correção sugerida |
| --- | --- | --- | --- | --- |
| N1 | `egm-structural-r1-2`, `egm-style-r1-16` | 174, 189 | A Q9 vem antes da Q8. O structural classificou como Major; rebaixei para Nit porque é só reordenação, sem impacto no conteúdo. | Mover a Q8 para antes da Q9. |
| N2 | `egm-structural-r1-10`, `egm-design-r1-14` | 37, 39, 167, 246–247, 395 | Caminhos de código em estilos mistos, com e sem `bitsignal/`. `indicators.py:44` deveria ser `:45`. | Usar caminhos a partir da raiz do repositório e citar `:45` ou `is_picycle_bottom_triggered`. |
| N3 | `egm-structural-r1-11` | 167 | O texto do link diz "ingestion.py:216", mas o link não tem âncora. | Usar `../../bitsignal/ingestion.py#L216`. |
| N4 | `egm-structural-r1-12`, `egm-style-r1-19` | 155, 369–378 | "Plano Técnico, §7" não bate com o título real "Technical Plan (Architecture)". O §7 também não lista a variante Q5b. | Citar o título real e incluir "critérios de agravamento de D (Q5b)" no §7. |
| N5 | `egm-structural-r1-9`, `egm-style-r1-14` | 291–297 | A tabela da escada está fora do recuo da lista. As condições ≥85/≥90/≥93 se sobrepõem. | Recuar 4 espaços e acrescentar "vale o maior degrau atingido". |
| N6 | `egm-structural-r1-15`, `egm-style-r1-20` | 18, 67, 102, 312, 365, 399, 582, 591 | Réguas horizontais irregulares. "Deste draft". Mistura de "drawdown" e "queda máxima do patrimônio". Títulos H2 em inglês e H3 em português. | Escolher uma convenção para cada caso e usar "deste documento". |
| N7 | `egm-design-r1-15` | 52, 240, 253 | A G1 chama a função de `avaliar(historico) -> Veredito`; a arquitetura chama de `replay()`. | Usar um nome e uma assinatura só, ex.: `replay(history, config) -> DataFrame`. |
| N8 | `egm-design-r1-18` | 159 | O intervalo de um insumo secundário ausente usa limites 0–100, mas o Hash Ribbon só assume 10, 20 ou 50 (`config.yaml:35–38`). | Usar o domínio real de cada insumo. |
| N9 | `egm-design-r1-19` (parte CUJ 1) | 197 contra 281 | O CUJ 1 dá a semana como utilizável logo após o fechamento de domingo; o §3 diz segunda-feira. | Alinhar com o §3. |
| N10 | `egm-style-r1-12` | 45, 434, 439 | "a 7–47% do preço do pico" é ambíguo. | "a preços entre 7% e 47% do valor do pico". |
| N11 | `egm-style-r1-13` | 284 | "Indicadores diários" inclui a SMA200w, e "base diária ou semanal" fica em aberto. | Especificar a base de cada indicador. |
| N12 | `egm-style-r1-15` | 8 | "decididas nas Q1–Q9", mas a Q4, a Q5b e a Q8 estão abertas. | Listar só as Q decididas. |
| N13 | `egm-style-r1-17` | 174 | "Decidido… (provisório)" se contradiz. | Usar "Hipótese experimental". |
| N14 | `egm-style-r1-18` | 189 contra 395 | A Q8 está aberta, mas o §8 já define a correção. | "Correção definida; confirmar no app publicado". |
| N15 | `egm-style-r1-21` | 52, 222, 341, 407 | "gauge com constantes próprias", STOP_2, C0 e "variante mínima" são usados sem definição. | Definir no primeiro uso. |
| N16 | `egm-style-r1-22` | 59, 167, 264, 283 | A mesma série tem três datas de início: 2010-07-18, ~2011 e 2010. | Padronizar em 2010-07-18 e explicar o aquecimento à parte. |
| N17 | `egm-style-r1-23` | 62 | "Simulação real" se contradiz. | "Simulação da carteira com saldos de BTC e caixa". |
| N18 | `egm-style-r1-24` | 118 | "100%" não aparece na formulação da linha 103. | "(≥ DCA uniforme)". |
| N19 | `egm-style-r1-25` | 186 | "atual: 1,17×" não tem data. | Informar a data de corte. |
| N20 | `egm-style-r1-26` | 201, 586 | "Em até ~10 s" mistura limite com aproximação, e os NFRs só citam o tempo com cache. | "≤ 10 s" e repetir o valor nos NFRs. |
| N21 | `egm-style-r1-27` | 286, 589 | Tom coloquial ("e isso acaba", "basta"). | "essas diferenças deixam de existir" e remover "basta". |
| N22 | `egm-style-r1-28` | 356 | O título mistura benchmarks da Q1 com variantes da Q9. | "Benchmarks (Q1) e variantes de compra (Q9)". |
| N23 | `egm-style-r1-29` | 364 | "antes de o preço subir mais 50%" é ambíguo. | "% da posição vendida a preços ≤ 2/3 do pico seguinte". |
| N24 | `egm-style-r1-30` | 580 | O campo "Reason for Rejection" da A22 abre com "Rejeitada só em parte". | Renomear o campo para "Aceita com restrição". |
