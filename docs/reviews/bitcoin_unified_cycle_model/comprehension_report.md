# Relatório de Compreensão (Etapa 6): Modelo de Ciclo Unificado e Painel Só de Leitura

**Documento auditado:** [`docs/designs/bitcoin_unified_cycle_model.md`](docs/designs/bitcoin_unified_cycle_model.md)
**Data:** 2026-11-08
**Revisor:** `egm-comprehension` (contexto isolado). FeatureRange 1..592; DetailedRange 593..1010.
**Contexto Goldfish:** `config/config.yaml`, `bitsignal/ui/app.py`, `bitsignal/engine/normalizer.py`, `docs/reviews/bitcoin_unified_cycle_model/probe.py`.

---

**O que isto propõe**

Hoje o painel tem dois sistemas de decisão. O documento propõe trocá-los por uma única função pura e sem estado, `run_model`/`replay()`. Ela reconstrói desde 2010, semana a semana e só com semanas fechadas (W-SUN), o score de valuation, um detector de reversão por tendência de preço (D), o ciclo com catraca e as compras. Daí sai um veredito com fase (ACUMULAR/MANTER/DISTRIBUIR), exposição-alvo e % de compra sobre uma reserva-base. A venda acumulada tem teto de 50% por ciclo. Ela é dada pelo maior valor entre a escada do score (85/90/93 → 5/15/30%) e o nível do detector (10/25/50%). O ciclo reinicia em duas etapas pelo score (≤20 e depois ≥30). Painel e backtest usam só a CoinMetrics Community, sem persistência. O backtest simula a carteira contra "comprar e segurar" e "DCA uniforme completo", com três critérios cumulativos fixados antes de rodar. A implementação vem em 10 commits (S0–S9), e o dono decide a severidade de D e a política de sobra em S6.

**Como o sistema existente funciona, segundo este documento**

O app Streamlit tem a aba "Sentinela", com o Composite Score 0–100 e faixas de venda em 80/85/90. Tem também a aba "Plano Nacional", que compra e vende por distância a um ATH fixo de US$ 126 mil, com trailing stops. As duas não conversam e podem dar ordens contraditórias, e há três tetos de venda diferentes. O score tem erros: Pi Cycle Bottom invertido, candles abertos, `config.yaml` ignorado pelo motor e valores fixos de reserva apresentados como dado real. O backtest usa MVRV/Puell sintéticos e resultados fixos. Em produção, o pipeline roda a cada visita por causa do `created_at`, o SQLite se perde a cada reinício e a Binance é bloqueada nos EUA.

O revisor conseguiu parafrasear as duas partes. Os problemas abaixo são de coerência interna e de conceitos que o leitor não consegue fechar só com o documento.

---

## Achados

**Resumo:** 12 🟡 Major, 7 🟢 Nit.

### 🟡 1. As letras A/B/C/D querem dizer coisas diferentes em cada pergunta (l. 15, 95–97, 142–145, 153, 174, 185, 369–378, 845–846)

"C" é a escada de venda (Q5), a opção de compras por DCA proporcional (Q9), o armamento por score > 35 (Q5a) e o nome da variante "C". "B" é a normalização com limites altos (Q5), o armamento por score ≥ 60 (Q5a) e o DCA uniforme (Q9), como em "compras B" (l. 97). "A" é o percentil (Q5), o armamento por ATH (Q5a) e a escada por queda (Q9). "D" é o detector, e "D2" é uma normalização que não tem nada a ver com o detector. A tabela da l. 15 já usa "Escada C", "detector D" e "normalização D2" antes de qualquer definição, que só aparece nas l. 143–145.

Sem um glossário ou nomes próprios (ex.: "escada de venda", "armamento por ATH", "DCA uniforme"), o leitor precisa voltar a cada Q para descobrir o que cada letra quer dizer. As frases "C + D com armamento B e com armamento C" (l. 372) e "compras B" (l. 97) são as mais difíceis de ler.

### 🟡 2. A composição do score nunca é listada (l. 290 e 202, "seis insumos", §4)

O documento diz "seis insumos, com os pesos e limites atuais lidos do config", mas não diz quais são, nem os pesos, nem como a "normalização atual" funciona (mapeamento linear com corte entre mín. e máx.). O leitor só remonta a lista pelo `config.yaml` (MVRV Z 0,25; preço/SMA200w 0,20; Puell 0,20; Pi Cycle 0,15; RSI semanal 0,10; Hash Ribbon 0,10) ou pelo `normalizer.py`.

Também não fica explicado como o Pi Cycle entra no score: o spread SMA111/(2×SMA350), com o "fundo" forçando 0. O documento só dá a fórmula do Bottom (l. 290). Tudo depende do score (limiares 85/90/93, 20/30 e as regras de intervalo da Q6), e ele não é autocontido.

### 🟡 3. As janelas de calibração e validação se contradizem (l. 63 G3 contra l. 108, 380–381, 890)

G3 diz "calibra até 2017 e testa 2021 e 2022 fora da amostra". O §7 calibra até 2018-12-31. A Q1 afirma que 2019+ "não é amostra independente". Quem lê só os Goals sai com uma ideia de validação que o resto do documento nega.

### 🟡 4. A regra de escolha da Q5b briga com os casos citados (l. 155 e 890)

A Q5b define a severidade de D com casos de mai/2021, set/2024, jan/2022 e nov/2025. Em S6, o dono escolhe "olhando só a janela de calibração (≤ 2018)". O documento não explica como decidir critérios cujos casos de referência estão quase todos fora dessa janela, nem se os casos da Q5b servem só de diagnóstico.

### 🟡 5. A política para dado ausente se contradiz (l. 74, 207–213 G5 e CUJ 2 contra Q6 l. 156–165 e Q7 l. 166–171)

G5 e CUJ 2 falam em veredito "indicativo" quando um insumo é "estimado". Também falam em "a reserva também falhou" e em mostrar "o último valor bom em cache". A Q6/Q7 eliminou estimativas e a reserva fixa: o score passa a ter três estados (`ok`/`intervalo`/`indisponível`), e o Dune não alimenta o modelo. O CUJ 2 descreve o sistema antigo (Dune como fonte, com reserva). O leitor não sabe se "indicativo" corresponde a `intervalo`, nem o que ainda pode ser "estimado".

### 🟡 6. O comportamento do detector quando a CoinMetrics cai se contradiz (l. 171 contra l. 263)

A Q7 diz "Falha da CoinMetrics: … O detector D continua". O §2 diz que, se a CoinMetrics falhar, "score e detector ficam indisponíveis". Como o preço do modelo agora vem só da CoinMetrics (l. 262), a l. 171 parece desatualizada, mas o documento não resolve isso.

### 🟡 7. A fonte do hashrate e os valores de `source` não batem (l. 265–266 contra 267, 274, 686, 698)

O §2 diz que o hashrate vem do Mempool.space. Mas o backtest e `fetch_coinmetrics` buscam `HashRate` na CoinMetrics, e a l. 274 afirma que "painel e backtest usam a mesma fonte". Os exemplos de `source` na l. 266 (`dune`, `yfinance`, `fixed_fallback`) são justamente as fontes que o desenho tira do modelo. A l. 698 define `coinmetrics_live | coinmetrics_frozen`. O leitor não sabe qual é a fonte real do Hash Ribbon nem que valores o selo de origem pode mostrar.

### 🟡 8. O formato da linha do topo se contradiz (l. 127 e 201 contra l. 387)

A Q2 diz que o painel mostra a exposição-alvo, "não uma ordem incremental". O CUJ 1 mostra "VENDER Y% da posição / NADA", que é uma ordem incremental. O §8 mostra "Exposição-alvo: manter X%". O mesmo §8 fala em "Y% da reserva do ciclo", mas a Q9 e a A15 rejeitam explicitamente a reserva "do ciclo" (ela é da campanha e não se renova). São três versões da linha mais importante da tela.

### 🟡 9. Faltam definições de "campanha" e de "declarar" (l. 129, 175, 184, 522)

O documento não define "campanha": quando começa, quem define o valor da reserva-base e onde o usuário o informa. Diz que o caixa cresce "com novas entradas declaradas" ou com aportes declarados, mas o app não tem estado nem entrada de dados (G6, Non-Goals). Fica sem explicação onde e como alguém declara um aporte, tanto no painel quanto no backtest (o `BacktestConfig`, l. 658, não tem campo de aportes).

### 🟡 10. A Q4 continua aberta, mas o desenho já a respondeu (l. 138)

A Q4 pergunta se "a saída por tendência só vale dentro da fase DISTRIBUIR". O §6 já define que D é independente do score e que DISTRIBUIR é *consequência* de `ratchet_sell > 0`. Logo, a pergunta não se aplica mais. Ela não está marcada como decidida nem como obsoleta. O texto também usa ACUMULAR/MANTER/DISTRIBUIR antes de defini-las (definidas só na l. 343).

### 🟡 11. O benchmark "DCA uniforme completo" não é definido no escopo de funcionalidade (l. 97, 185, 512–516)

É o terceiro critério de aprovação, mas o documento não diz quanto se compra, com que frequência, nem se a compra é só na fase ACUMULAR. A frequência (`uniform_weekly = 1/52`) só aparece na l. 657. "Compras B" depende do achado 1 para ser entendido.

### 🟡 12. O que o backtest mostra se contradiz (CUJ 3 l. 217–223 contra Q1 e A19 l. 551–555)

O CUJ 3 promete "acerto sim/não" por evento para 2017/2021/2022, com "definições de acerto registradas no config". A Q1 e a A19 rebaixaram o critério por evento a diagnóstico, e a aprovação é por patrimônio. O CUJ também cita a "comparação com a variante mínima" (A2), que não aparece em nenhuma lista de variantes (l. 369–378, 843–853).

### 🟢 13. O bloco `bands:` não existe (l. 228, CUJ 4)

O S2 (l. 667) cria `sell_ladder`, não `bands:`.

### 🟢 14. Não fica claro se o backtest da aba é pré-calculado ou calculado ao vivo (l. 393, 905 e CUJ 3)

A aba mostra um "resultado pré-calculado do CSV congelado", mas nenhum arquivo do plano gera ou guarda esse resultado. A l. 905 diz que a aba "lê o CSV congelado", o que sugere cálculo na hora.

### 🟢 15. O diagrama cita `historical.py`, mas o plano cria `bitsignal/data/history.py` (l. 247 e 701)

### 🟢 16. "STOP_2" e "C0" são rótulos do código atual e não são explicados (l. 341 e 407)

O leitor deduz pelo contexto ("manda vender 80%" / "manda comprar"), mas uma frase de definição ajudaria.

### 🟢 17. A ordem das regras no pseudocódigo e no S4 é diferente (l. 327–337 contra 762–768)

O pseudocódigo atualiza a catraca antes de checar o reinício e não mostra a regra "com `reset_pending`, `v_d` é ignorado". A lista do S4 tem outra ordem. Na semana do reinício não fica claro se `ratchet_sell` termina em 0 ou em max(V_C, V_D).

### 🟢 18. As "11 divergências" em relação ao brief só são listadas pelo nome (l. 8)

O texto não diz o que cada uma era no brief. Quem não leu `concepts_brief.md` não entende o que mudou. Isso é aceitável como registro histórico, mas a frase pressupõe a leitura do brief.

### 🟢 19. O arquivo do item 42, marcado como "Create/Modify", já é este documento, no mesmo caminho (l. 988)

Parece sobra da etapa de rascunho.

---

**Arquivos lidos pelo revisor:** o documento auditado (1–1011), `config/config.yaml`, `bitsignal/engine/normalizer.py`, `docs/reviews/bitcoin_unified_cycle_model/probe.py`, `bitsignal/ui/app.py` (buscas pontuais) e `concepts_brief.md` (só os cabeçalhos e as seções citadas).
