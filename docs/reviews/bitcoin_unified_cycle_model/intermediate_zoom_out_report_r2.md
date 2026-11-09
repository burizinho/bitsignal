# Goldfish Review Report: Etapa 8, reauditoria Zoom-Out (rodada 2)

**Alvo:** `D:/Projetos Gui/BitSignal/docs/designs/bitcoin_unified_cycle_model.md` (L1–1085; FeatureRange 1..656, DetailedRange 657..1085)
**Padrão:** `C:/Users/gsame/.claude/plugins/cache/egm/egm/0.1.0/resources/document_standards/zoom-out-standard.md`
**Histórico consultado (não é autoridade sobre o design):** `zoom_out_report.md` (Etapa 5), `intermediate_zoom_out_report.md` (Etapa 8, rodada 1) e a seção "Etapa 8 ... resolução antes da reauditoria" de `goldfish_review_report.md`.

## Situação dos revisores

| Revisor | Situação |
| --- | --- |
| `egm-zoom-out` | concluído (uma instância, sem nova tentativa) |

O sintetizador conferiu no documento as linhas L266, L324, L718, L817, L866 e L964–966, que sustentam os achados M1, M2 e o resíduo de A2. Elas conferem com o que o revisor relatou.

## Resumo

- 🔴 Blocker: 0
- 🟡 Major: 4 (M1–M4)
- 🟢 Nit: 6 (N1–N6)

Como foi a rodada 1:
- **Resolvidos:** A1 e A3.
- **Resolvidos só em parte:** A2 e A5. Cada um deixou uma divergência.
- **Contestados com base em decisões escritas no documento:** A4 e A6.

Continuam pendentes três achados da Etapa 5: o 5, o 8 e o 13.

---

## Achados novos (Blocker, depois Major, depois Nit)

### M1. O hash do config deixa de bater logo depois da S6. Severidade: Major
* **Lente do revisor:** `egm-zoom-out`
* **Trechos afetados:** L225, L436, L439, L722, L964 e L966.
* **O problema:**
  - O passo 2 da S6 (L964) copia o config efetivo para o arquivo congelado.
  - Depois, o passo 4 (L966) edita o `config.yaml` para gravar `backtest.frozen_params`.
  - A partir daí, o hash do config em uso (L436) nunca mais é igual ao do arquivo congelado. O painel passa a mostrar sempre "status aprovado não se aplica" (L225).
  - O mesmo acontece quando muda um campo que não afeta a decisão, como `retry_cooldown_s` (L439) ou o ttl do cache.
  - **Efeito:** o rótulo que o usuário vê muda e a trilha prospectiva deixa de valer.
* **Recomendação:** escolher uma das saídas abaixo.
  - Definir só no §7 que o hash cobre apenas os blocos que afetam o modelo: `score`, `sell_ladder`, `detector`, `cap`, `cycle`, `buys` e as regras de execução do `backtest`. Ficam fora `frozen_params`, `data` e a UI.
  - Ou fazer o painel ler os parâmetros direto do arquivo congelado. Nesse caso, o `config.yaml` só aponta para ele.

### M2. O estado semanal do Hash Ribbon (§2) se perde na implementação. Severidade: Major
* **Lente do revisor:** `egm-zoom-out`
* **Trechos afetados:** L266, contra L694 (item 3) e L800 (item 16). Também `ingestion.py:181–186` e `probe.py:23`.
* **O problema:**
  - O §2 define BUY_RECOVERY assim: SMA30 ≥ SMA60 e houve cruzamento para cima "em algum dia daquela semana".
  - O item 3 devolve estados diários, e o item 16 só amostra no domingo. Lido ao pé da letra, o plano só reconhece um cruzamento feito no próprio domingo.
  - A diferença no indicador é de 10 contra 50 pontos, com peso de 10%. Isso dá cerca de 4 pontos de score, o bastante para mexer nos limiares 10/20/30 de compra e de reinício.
  - Há ainda uma terceira regra no código atual: o `ingestion.py:183` usa `>` estrito e só olha o cruzamento no último dia.
* **Recomendação:**
  1. Escrever a agregação W-SUN no item 16 e cobri-la em `test_weekly.py`. A alternativa é simplificar o §2 para "estado no domingo".
  2. Fixar se a comparação é `≥` ou `>`.
  3. Reaproveitar a lógica de `ingestion.py:181–186`.

### M3. O "oráculo" `sev.py` do teste do detector não existe e depende de rede. Severidade: Major
* **Lente do revisor:** `egm-zoom-out`
* **Trechos afetados:** L145, L329 e L867. Também `sev.py:11` e `:16–17`, e `probe.py:9` e `:16`.
* **O problema:**
  - O item 22 manda reproduzir "os níveis por episódio registrados em `sev.py`". Mas o `sev.py` só imprime os níveis, não os registra.
  - O `sev.py` executa o `probe.py`, que busca dados na API.
  - O `probe.py` usa `resample("W-SUN").last()`. Isso inclui a semana ainda aberta, o que contradiz o §3 (L275).
  - O teste fica sem valor esperado e sem a garantia de rodar offline, que a L1071 exige.
* **Recomendação:** escolher uma das saídas abaixo.
  - Gravar uma fixture de episódios a partir do CSV congelado, só com semanas fechadas. Cada episódio leva a data de início, a do N2, a do N3 e a do fim.
  - Ou tirar esse ponto do item 22 e deixar a regressão para o `test_golden.py` (item 30).

### M4. Há variantes "pré-registradas" sem regra completa. Severidade: Major
* **Lente do revisor:** `egm-zoom-out`
* **Trechos afetados:** L405, L411, L415, L417, L419, L720 e L924.
* **O problema:** a L405 proíbe mudar as variantes depois de ver os resultados. Mas várias não têm regra completa:
  - **`reset_dd60`:** não diz como entra e sai de ACUMULAR, nem se compra.
  - **`arm_score35`:** não diz a janela, qual score usa nem o que fazer quando o score está indisponível.
  - **`thr_±5`:** não lista os limiares afetados. Se valer para o 93, ele vira 98.
  - **`minimal`:** não diz o gatilho das "vendas 15 + 15%". Também não define "Pi Cycle Top"; o §4 só define o spread.
  - **Efeito:** essas regras seriam decididas na implementação, o que enfraquece o pré-registro e aumenta o escopo (itens 1 e 5 da Etapa 5).
* **Recomendação:** especificar cada variante em uma linha antes da S6. A outra saída é cortar `reset_dd60`, `arm_score35` e `thr_±5`, ficando com `default`, `ladder_only` e `minimal`.

### N1. O §5 não diz a ordem dentro da semana nem a janela do N2. Severidade: Nit
* **Trechos afetados:** L315–328, contra `sev.py:39–49`.
* **O problema:** o §5 deixa duas regras em aberto, e hoje quem as decide é o `sev.py`:
  - se o nível sobe antes ou depois de o episódio fechar na mesma semana;
  - se os 2 fechamentos abaixo da SMA50w podem incluir a semana anterior ao disparo.
* **Recomendação:** escrever as duas regras no §5.

### N2. O critério de atraso aparece com redação diferente. Severidade: Nit
* **Trechos afetados:** L200 e L636, contra L277.
* **O problema:** L200 e L636 dizem "a última semana completa tem mais de 9 dias". Lida ao pé da letra, essa condição nunca dispara.
* **Recomendação:** nas duas passagens, só citar o §3.

### N3. `retry_cooldown_s` e a aba de backtest ficaram fora da parte detalhada. Severidade: Nit
* **Trechos afetados:** L439 contra L723 e L982; L436 contra L978.
* **O problema:**
  - `retry_cooldown_s` não está no `DataConfig`.
  - O item 32 não traz "só a variante padrão e os benchmarks", nem a comparação de hash do §8.
* **Recomendação:** incluir esses pontos nos itens 6 e 32, ou fazer o item 32 referenciar o §8.

### N4. A fórmula da catraca e os nomes de variáveis divergem. Severidade: Nit
* **Trechos afetados:** L517 (A8), L831 (item 19) e L28, contra L358.
* **O problema:**
  - A A8 omite `ratchet_sell` e `V_det_eff`.
  - O item 19 usa `v_c` e `v_d`, enquanto o resto do documento usa `V_esc` e `V_det_eff`.
* **Recomendação:** a A8 cita o §6 sem repetir a fórmula, e o item 19 passa a usar `v_esc` e `v_det_eff`.

### N5. Restam um rótulo antigo e um status inconsistente. Severidade: Nit
* **Trechos afetados:** L731 e L16.
* **O problema:**
  - A L731 ainda usa o rótulo antigo "detector A".
  - A L16 põe a normalização híbrida como hipótese do modelo, mas a Q5 (L136) e o §7 (L414) dizem que ela é só comparação.
* **Recomendação:** trocar o rótulo por "armamento por ATH" e tirar a híbrida da L16.

### N6. A Q3 é ambígua e o cabeçalho está incompleto. Severidade: Nit
* **Trechos afetados:** L131 e L7.
* **O problema:**
  - A Q3 permite entender que se exigem "2 semanas sem episódio". O §6 (L351) só exige `level == 0` na semana em que a mudança vale.
  - O cabeçalho "Revisão" não cita a rodada 1 da Etapa 8.
* **Recomendação:** reduzir a Q3 a "Regra: §6" e completar o cabeçalho.

---

## Matriz de rastreabilidade

### Etapa 8, rodada 1

| ID | Estado | Classificação | Evidência |
|---|---|---|---|
| A1 Estados intervalo e indisponível inalcançáveis | Resolvido | Defeito de especificação (corrigido) | L275–276 e L797–798 separam o aquecimento do dado ausente. L300–301 são alcançáveis. |
| A2 Três definições do detector | Parcialmente resolvido | Defeito de especificação a corrigir | O §5 é a fonte normativa e os itens 18 e 22 e o `sev.py` estão alinhados. Resíduo: o nome da regra na L718 (`below_sma50w_2w_and_le_60pct_high52`) não segue o §5, que na L324 diz "N2 atingido … e ≤ 60%". O oráculo também falha (M3) e há lacunas (N1). |
| A3 §7 × VARIANTS × sensibilidades | Resolvido | Defeito de especificação (corrigido) | 14 nomes iguais em L407–419 e L915. As sensibilidades estão separadas (L421 e L916). |
| A4 Herança da catraca e entrada tardia | Contestado. Apoia-se em decisão documentada: Q1 (L122) e §7 (L379, L421). O motivo do autor não está escrito no documento, e não existe um rótulo "Carteira e capital". | Risco conhecido e aceito | Ver L379, L421, L890 e L949. Recomenda-se uma linha de motivo na Q1. |
| A5 Regras duplicadas entre Decisões e técnico | Parcialmente resolvido | Defeito de especificação a corrigir | A precedência foi incluída (L117), mas as Decisões ainda repetem números. A cópia do §6 no item 19 (L826–831) diverge. |
| A6 Tela sem veredito complexa | Contestado. Apoia-se em decisão documentada: Q6 (L149). | Risco conhecido e aceito | L438–442. O cooldown não está no `DataConfig` (N3). |

### Etapa 5

| # | Título | Estado | Classificação | Evidência |
|---|---|---|---|---|
| 1 | Calibração com evidência impossível | Parcialmente resolvido | Limitação histórica que edição não elimina (e risco aceito) | A S6 virou congelamento (L959–966). Há um só topo avaliável (L403) e o catálogo continua com 14+4 itens (L405–421, aceito em L642). |
| 2 | Números não reproduzíveis | Parcialmente resolvido | Limitação histórica que edição não elimina | Os números estão marcados como exploratórios (L66 e L448). Faltam scripts para A5 e A11–A14, e o `sev.py` herda a semana aberta. |
| 3 | Duas entregas num design | Contestado. Apoia-se em decisão documentada: A22 (L625–629). | Risco conhecido e aceito | O plano não tem divisão em fases (L661–670). |
| 4 | Alternativa simples sumiu | Parcialmente resolvido | Defeito de especificação a corrigir | `minimal` existe (L415 e L924), mas falta definir o gatilho e o "Pi Cycle Top" (M4). |
| 5 | Variantes rejeitadas no config e no engine | Pendente | Defeito de especificação a corrigir | O config ainda traz `arming` com três valores, `reset_mode: drawdown_60`, `buys.mode` e normalização `high/hybrid` (L716–721). |
| 6 | Modo intervalo e fonte do hashrate | Parcialmente resolvido | Risco conhecido e aceito | O hashrate está resolvido (L255). O intervalo ficou por decisão da Q6 (L149). |
| 7 | Goals e CUJs fiéis ao brief | Resolvido | Defeito de especificação (corrigido) | L75–102 e L168–225. Resíduo: a G5 (L97) não cita `desatualizado`. |
| 8 | Painel antigo mostra ordens erradas em S1–S6 | Pendente | Defeito de especificação a corrigir | A S0 (L674–684) não tem aviso, e o risco não aparece na tabela de Riscos (L633–644). |
| 9 | Dune como conferência sem efeito | Contestado. Apoia-se em decisão documentada: Q7 (L153) e L259. | Risco conhecido e aceito | Itens 13, 39 e 40. |
| 10 | Questões abertas como ata; Q4 já respondida | Resolvido | Defeito de especificação (corrigido) | A Q4 foi fechada (L134). Só a Q8 continua aberta (L164). |
| 11 | yfinance só para exibição | Contestado. Apoia-se em decisão documentada: L15, L258 e A21 (L614–621). | Risco conhecido e aceito | O uso na tela sem veredito (L440) justifica manter. |
| 12 | Constantes no YAML e retry manual | Pendente | Defeito de especificação a corrigir (Nit) | `DataConfig` e `CapConfig` ainda inflados (L719 e L723). Atenuante: o `ingestion.py` é apagado na S8. |
| 13 | Ordem das regras duplicada | Pendente | Defeito de especificação a corrigir | No item 19 (L826) a escada vem em 1º; no §6 ela é o passo 4 (L356). O item 19 também omite L347 e L355. |
| 14 | Pequenas imprecisões | Resolvido | Defeito de especificação (corrigido) | L62 foi corrigida. |

**Totais da matriz (20 itens):**
- **Por estado:** Resolvido 6, Parcialmente resolvido 6, Contestado 5, Pendente 4. Os 5 contestados se apoiam em decisões escritas no documento. Na A4 o apoio é só parcial, porque o motivo do autor não está escrito.
- **Por classificação:**
  - Defeito de especificação: 11, dos quais 5 já corrigidos e 6 a corrigir;
  - Risco conhecido e aceito: 7;
  - Limitação histórica que edição não elimina: 2.

---

## Verificações pedidas

**a. O §5 é a única fonte normativa do detector, e os itens 18 e 22 e o `sev.py` batem com ele: FALHA, por resíduo.**
- **Passa:** a precedência (L117 e L311). Também batem com o `sev.py` (`sev.py:24–49`) as regras de armamento, disparo, fechamento, novo episódio, N1/N2/N3 e salto de nível (L313–328), e os itens 18 (L816–817) e 22 (L862–866).
- **Falha:**
  - O nome da regra do N3 no `DetectorConfig` (L718) carrega a semântica antiga.
  - O oráculo do item 22 (L867) não existe e depende de rede (M3).
  - O §5 deixa a ordem dentro da semana e a janela do N2 para o `sev.py` decidir (N1).

**b. A tabela de variantes do §7 bate com o `VARIANTS` do item 26: PASSA, com ressalvas.**
- **Passa:** os 14 nomes são iguais (L407–419 e L915). O mapeamento de `norm_*` (L917) e de `minimal` (L924) confere.
- **Ressalvas:**
  - Em `floor40` e `floor60`, a regra `cap = 1 − floor` não tem mapeamento escrito para o `CapConfig.max_sell` (L719).
  - Faltam parâmetros completos em `thr_±5`, `arm_score35` e `reset_dd60` (M4).

**c. As Decisões não repetem regras operacionais em conflito com §2–§8: PASSA quanto a conflito, FALHA quanto a não repetir.**
- **Sem conflito:** Q1, Q2, Q3, Q5, Q5a, Q5b, Q6 e Q9 repetem números iguais aos do §4, §5, §6 e §7. A Q3 é ambígua (N6).
- **Onde há divergência:** fora das Decisões, em A8 (L517), item 19 (L826–831), L200 e L636, e item 6 (L718).
- **Recomendação:** nas Decisões, deixar só a decisão, o motivo, os limites e "Regra: §x".
