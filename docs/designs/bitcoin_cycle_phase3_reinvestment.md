# Fase 3 — Reinvestimento do caixa (modelo v2)

*   **Autor:** @burizinho
*   **Data:** 2026-11-09
*   **Status:** Approved (2026-11-09) — E1–E5 aprovadas pelo dono com as recomendações
*   **Depende de:** [Fase 1](bitcoin_unified_cycle_model.md) (modelo v1, publicado e congelado) e
    [Fase 2](bitcoin_cycle_phase2_variants.md) (diagnóstico)

## O problema

O modelo v1 vende nos topos, mas o dinheiro das vendas nunca volta para o bitcoin. As compras são
2% / 4% por semana de uma reserva-base fixa de US$ 219,56 (0,5 BTC em 2014), mesmo quando o caixa
chega a US$ 30 mil. Na janela de desenvolvimento (2019+), o patrimônio termina em 0,325 do comprar e
segurar.

## O que a Fase 2 mostrou, e o quanto isso vale

| Variante | ×B&H calibração (até 2018) | ×B&H desenvolvimento (2019+) | ΔDD 2019+ |
| :--- | ---: | ---: | ---: |
| v1 (padrão) | 1,883 | 0,325 | 31,3 |
| `leftover_buy` (pré-registrada) | 1,883 (igual) | 0,761 | 15,2 |
| `proceeds_dca` (pós-resultado) | 1,697 (pior) | 1,160 | 20,5 |
| `ladder_only` (sem detector) | 1,634 (pior) | 0,537 | 22,5 |

**Críticas que este design precisa encarar:**

1.  **A evidência é de um ou dois ciclos.** O ganho do reinvestimento só aparece quando há caixa num
    reinício. Na calibração, o único reinício (2015) aconteceu antes de qualquer venda, então
    `leftover_buy` não muda nada; `proceeds_dca` chega a piorar. Na prática, o ganho vem quase todo
    do caixa das vendas de 2017–2018 recomprado em 2019–2022.
2.  **Tudo já foi visto.** Qualquer regra escolhida agora foi escolhida conhecendo o resultado. Por
    isso o v2 não pode ser aprovado com dados passados: ele só é avaliado com dados futuros (E4).
3.  **Mais de uma mudança ao mesmo tempo esconde o efeito de cada uma.** Mudar a compra e o detector
    juntos impediria saber qual das duas funcionou.
4.  **Reinvestir aumenta a exposição.** Com o caixa de volta no bitcoin, a queda máxima melhora menos
    (31,3 → 15,2 p.p. em `leftover_buy`). O critério 2 da Q1 (≥ 10 p.p.) ainda passa, mas por pouco.

## Objetivo

Um modelo v2 que muda **só a regra de compra**, para que o dinheiro das vendas volte ao bitcoin, com:

*   congelamento próprio (arquivo novo, `model_hash` novo);
*   o v1 preservado e congelado, para comparação;
*   avaliação **só com dados futuros**, com critério escrito agora, antes de existir resultado.

**Não é objetivo:** mexer na escada de venda, nos limiares, na normalização ou no piso (a Fase 2
mostrou que não ajudam); recalibrar qualquer parâmetro do v1; alertas; registro de operações.

## Decisões (aprovadas em 2026-11-09)

*   **E1. Regra de compra do v2.**
    *   (a) **Compra no reinício (`leftover_buy`)**: tudo igual ao v1 e, na semana em que um ciclo novo
        começa, compra todo o caixa restante. Pré-registrada na Fase 1; resultado 0,761 em 2019+.
        Risco: uma compra única concentrada numa data.
    *   (b) **DCA sobre o caixa (`proceeds_dca`)**: as compras de 2% / 4% passam a ser sobre o caixa
        disponível, não sobre a reserva fixa. Resultado 1,160 em 2019+, mas escolhida depois de ver os
        dados e pior na calibração. Nunca termina de investir o caixa (cada compra é % do que sobrou).
    *   (c) **As duas:** DCA sobre o caixa durante ACUMULAR e o restante no reinício. Sem nenhum
        resultado medido: seria uma terceira regra escolhida agora.
    *   **Recomendação: (a).** É a única pré-registrada, a menor mudança, e não depende do período em que
        foi medida para fazer sentido (o caixa das vendas volta ao bitcoin quando o ciclo recomeça).
        (b) e (c) parecem melhores no papel justamente porque foram escolhidas olhando 2019+.
*   **E2. Detector no v2.** (a) igual ao v1; (b) sem detector. **Recomendação: (a)**: uma mudança
    por vez (crítica 3). O detector é o que mais protege a queda máxima, e o critério 2 já fica justo
    com o reinvestimento.
*   **E3. O que o painel mostra durante a avaliação.**
    *   (a) O painel passa a mostrar o v2, marcado como experimental. O v1 continua congelado e
        registrado só para comparação.
    *   (b) O painel continua no v1; o v2 só aparece no registro semanal.
    *   **Recomendação: (a).** A falha do v1 é estrutural (nunca reinveste); seguir a compra dele na vida
        real repete o erro já diagnosticado. As vendas do v1 e do v2 são idênticas, então o que muda na
        tela é só a linha de compra no reinício.
*   **E4. Critério de avaliação futura (pré-registrado agora).**
    *   Janela: da data de congelamento do v2 até a primeira das duas datas: o primeiro reinício de
        ciclo depois de uma fase DISTRIBUIR, ou 2030-12-31.
    *   Carteira simulada nova na data de congelamento (1 BTC + 0,5 BTC em USD), com herança de estado,
        como na Fase 1.
    *   Critérios: os três da Q1 (≥ 0,90 do comprar e segurar; queda máxima ≥ 10 p.p. menor; ≥ DCA
        uniforme) **e** patrimônio do v2 ≥ patrimônio do v1 na mesma janela.
    *   Antes do fim da janela, os números podem ser exibidos, mas nenhuma conclusão é registrada.
    *   **Recomendação: aprovar como está.** Um ciclo completo é o mínimo para testar uma regra que só
        age no reinício.
*   **E5. Registro semanal.** (a) um segundo arquivo, `data/verdicts/weekly_verdicts_v2.csv`, com o
    mesmo formato, gravado pelo mesmo workflow; o arquivo do v1 continua igual. (b) uma coluna `model`
    no arquivo atual. **Recomendação: (a)**: não muda o formato de um arquivo que só recebe linhas
    novas.

## Arquitetura (depois das decisões)

*   **Chave nova no bloco `buys`:** `on_reset: none | all_cash` (v1 = `none`). Como `buys` entra no
    `model_hash`, o v2 ganha um hash próprio. Para o v1 continuar batendo com o arquivo congelado de
    2026-11-09, `model_payload` omite campos novos quando estão no valor que reproduz o v1 (hash
    compatível); um teste garante que o hash do v1 continua `15d1e484…`.
*   **Dois configs:** `config/config.yaml` passa a ser o v2 (o painel); `config/config_v1.yaml` guarda o
    v1 exatamente como foi congelado.
*   **Simulação:** a regra `all_cash` reaproveita a lógica de `leftover_on_reset` da Fase 2, agora como
    regra do modelo (no backtest e no painel), não só como comparação.
*   **Painel:** na semana do reinício, a linha de compra diz "comprar com todo o caixa disponível
    (inclui o produto das vendas)". Nas demais semanas, nada muda. O painel não sabe o caixa real do
    usuário: o percentual é aplicado na planilha.
*   **Congelamento do v2:** `freeze-params` grava `config/frozen/params_v2_<data>.yaml` com
    `approval: null`. O `--record` sobre 2019+ **não** é usado no v2 (todas as janelas já foram vistas);
    o campo `approval` só é preenchido pela avaliação futura de E4.
*   **Registro semanal:** `record-verdict --config config/config_v1.yaml --out weekly_verdicts.csv` e
    `record-verdict --out weekly_verdicts_v2.csv` no mesmo workflow.
*   **Comando de avaliação futura:** `bitsignal forward-eval` calcula E4 com os dois modelos a partir da
    data de congelamento; só exibe, até o fim da janela.

## Plano de implementação (resumo; detalhar depois das decisões)

1.  `config.py`: `buys.on_reset`; `model_payload` compatível com o hash do v1; `--config` nos comandos.
2.  `engine/cycle.py`: marcar a compra de reinício no veredito; `backtest/portfolio.py`: `all_cash`.
3.  `config/config_v1.yaml` (cópia fiel do v1) e `config/config.yaml` (v2).
4.  Painel: linha de compra no reinício; selo "v2 experimental".
5.  `record-verdict --config`; workflow grava os dois arquivos.
6.  `forward-eval` (CLI), só exibição.
7.  Congelar o v2 (commit próprio).
8.  Testes: hash do v1 inalterado; `all_cash` com caso sintético; v1 pelo `config_v1.yaml` reproduz o
    golden; painel com o v2; `forward-eval` sem rede.

## Implementação (2026-11-09)

*   `buys.on_reset` com `HASH_COMPAT_DEFAULTS` em `config.py`: o v1 continua com o hash `15d1e484…`
    (teste em `tests/test_v2.py`); o v2 tem `dc9ea76f…`, congelado em
    `config/frozen/params_v2_2026-11-09.yaml` com `approval: null`.
*   O v2 reproduz exatamente a variante `leftover_buy` da Fase 2 (teste compara as curvas).
*   O registro semanal escolhe o arquivo pelo config (`data.verdict_log_path`) e recusa gravar um
    modelo num arquivo de outro. Na semana de reinício do v2, `buy_pct` = `all_cash`.
*   Painel: com `approval: null`, a aba de backtest mostra só a janela de calibração e o aviso de que
    a aprovação vem dos dados futuros. `backtest --window development` do v2 imprime o mesmo aviso.
*   `--record` é recusado no v2. `forward-eval` só exibe; gravar a conclusão de E4 fica para quando a
    janela fechar (comando a definir nessa data, sem mudar o critério).

