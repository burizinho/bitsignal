# Relatório de Compreensão: Estratégia de Ciclo Macro com Gestão Tributária Nacional

**Documento Auditado:** [`docs/designs/bitcoin_national_execution_strategy.md`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md)  
**Escopo Avaliado:** FeatureRange (linhas 1..302) e DetailedRange (linhas 303..349)  
**Status do Teste de Compreensão:** ⚠️ Aprovado com Ressalvas (2 Bloqueadores, 5 Maiores, 5 Nits)

---

## 1. Paraphrase First

### What this proposes
O documento propõe expandir o BitSignal — originalmente um sentinela observacional — para uma plataforma de orquestração de estratégias de ciclo macro de 3 a 4 anos do Bitcoin, voltada para investidores pessoa física brasileiros com patrimônio até 0.5 BTC. O novo módulo isolado (`bitsignal.strategy`) automatiza regras determinísticas de acumulação escalonada em bear market (C1–C4), desova gradual em topos parabólicos (V1–V5) e trailing stops dominicais de emergência (21w EMA e 50w SMA). Crucialmente, integra um motor de conformidade fiscal brasileira que explora a isenção mensal de alienações de até R$ 35.000,00 da Receita Federal (com algoritmo de fracionamento intermensal no fechamento do mês), calcula Custo Médio Ponderado, apura DARF (código 4600) e despacha runbooks práticos via Telegram para liquidação no par BTC/BRL e off-ramp via PIX para renda fixa diária.

### How the existing system works, per this document
Conforme descrito no documento, o BitSignal existente funciona estritamente como um sentinela quantitativo macro analítico e passivo, agnóstico a jurisdições geográficas ou moedas fiduciárias locais. Ele ingere dados de mercado e métricas on-chain, computa indicadores técnicos e persiste séries temporais no banco SQLite em modo WAL (`data/bitsignal.db`), exibindo dados via dashboard Streamlit e disparando alertas analíticos no Telegram. Atualmente, o sistema não possui consciência de carteira real, não rastreia estoque ou transações do usuário, não realiza gestão fiscal e não emite diretrizes operacionais de execução bancária ou de custódia.

---

## 2. Findings & Discrepancies

### 🔴 Bloqueadores (Blockers)

#### 1. Snippet `evaluate_tax_strategy` com Variáveis Não Declaradas e Falha no Acúmulo Mensal
* **Severidade:** 🔴 Blocker
* **Escopo Afetado:** Linhas 148–161 ([`bitsignal/strategy/tax_br.py`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L148-L161))
* **Descrição da Discrepância:**
  1. No bloco `else:`, o código tenta calcular `capital_gain = alienation_brl - (quantity_sold * current_cmp)`, porém nem `quantity_sold` nem `current_cmp` constam na assinatura da função `evaluate_tax_strategy(alienation_brl: float, signal_date: datetime)`.
  2. O teste `if alienation_brl <= 35000.0:` avalia a ordem isolada e ignora o volume já alienado no mês civil corrente (`tax_monthly_ledger.total_alienated_brl`). Pela Lei 8.981/1995 (art. 35), o teto de R$ 35.000,00 é **agregado mensal**. Se o usuário já vendeu R$ 20.000,00 no dia 05 e vende R$ 20.000,00 no dia 20, a segunda venda NÃO é isenta, e todo o ganho de capital do mês deve ser tributado a 15%.
* **Recomendação:** Ajustar a assinatura e a lógica para receber o histórico do mês:
  ```python
  def evaluate_tax_strategy(
      alienation_brl: float,
      quantity_sold: float,
      current_cmp: float,
      month_accumulated_alienation: float,
      signal_date: datetime
  ) -> TaxExecutionPlan:
      total_month = month_accumulated_alienation + alienation_brl
      if total_month <= 35000.0:
          return TaxExecutionPlan(action="SELL_FULL", status="EXEMPT", darf_amount=0.0)
      elif month_accumulated_alienation == 0.0 and 35000.0 < alienation_brl <= 70000.0 and signal_date.day >= 25:
          ...
  ```

#### 2. Ausência de Gatilho de Agendamento para Execução do Split Intermensal
* **Severidade:** 🔴 Blocker
* **Escopo Afetado:** Linhas 152–155, 162–164, 198–200 ([`bitsignal/strategy/weekly_evaluator.py`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L152-L200))
* **Descrição da Discrepância:** O algoritmo prevê o fracionamento `SPLIT_MONTH_END` onde a parte 2 é agendada para o primeiro dia do mês subsequente, registrando `strategy_state.pending_split_btc` e `pending_split_scheduled_date`. Contudo, o módulo `weekly_evaluator` é documentado para rodar **exclusivamente aos domingos/segundas** (`weekday() == 0`). Se o dia 1º do mês cair em uma terça, quarta, quinta, sexta ou sábado, não há nenhum processo agendado que acione o alerta de venda da segunda parcela. O usuário ficaria exposto à oscilação do mercado por até 6 dias adicionais sem runbook de execução.
* **Recomendação:** Especificar no plano técnico que o orquestrador diário do BitSignal (`bitsignal.cli` / rotina diária) verificará diariamente na virada do mês (`signal_date.day == 1`) se há ordens em `strategy_state.pending_split_btc` com `status == 'PENDING'`, emitindo o alerta de liquidação da parte 2 imediatamente às 09h00 BRT do dia 1º.

---

### 🟡 Maiores (Major)

#### 3. Contradição na Definição Temporal da EMA de 21 Semanas
* **Severidade:** 🟡 Major
* **Escopo Afetado:** Linha 138 vs. Linha 313 ([`bitsignal/strategy/trailing_stops.py`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L138-L313))
* **Descrição da Discrepância:** Na linha 138, a EMA é descrita como "calculada sobre fechamentos semanais com $\alpha = \frac{2}{21+1}$" ($\alpha \approx 0.0909$). Na linha 313, a implementação descreve "$\text{EMA}_{21w}$ (147 dias)". Uma EMA de 147 períodos sobre barras diárias possui $\alpha = \frac{2}{148} \approx 0.0135$, reagindo de forma muito mais lenta e gerando valores substancialmente divergentes da EMA de 21 barras semanais.
* **Recomendação:** Padronizar a documentação deixando explícito que a série temporal deve ser reamostrada em velas semanais (fechamento domingo 21h BRT / 00h UTC) aplicando uma EMA de 21 períodos sobre os fechamentos semanais.

#### 4. Ambiguidade do Conceito de "DCA de 30% a -30%"
* **Severidade:** 🟡 Major
* **Escopo Afetado:** Linhas 13, 33 e 63 ([`Overview` / `Goals` / `CUJ 1`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L33-L63))
* **Descrição da Discrepância:** Na convenção financeira, DCA (*Dollar-Cost Averaging*) denota aportes contínuos e periódicos fracionados no tempo. No entanto, na linha 33 e no CUJ 1 (linha 63: *"O investidor já alocou os 30% de DCA (R$ 30.000) e os 15% de C1"*), o DCA é tratado como uma tranche única (lump sum) acionada quando o preço atinge -30% do ATH. Se for um aporte único, chamá-lo de DCA confunde o desenvolvedor e o usuário; se for contínuo, não foram documentados o intervalo (semanal/mensal) e o tamanho de cada sub-aporte.
* **Recomendação:** Renomear o estágio para `C0` ("Aporte de Desconto Inicial de -30%") ou descrever a regra de parcelamento temporal caso seja de fato um DCA periódico iniciado em -30%.

#### 5. Critério Indefinido de "Confirmação da 50w SMA" no Estágio C4
* **Severidade:** 🟡 Major
* **Escopo Afetado:** Linhas 13 e 33 ([`Goals`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L33))
* **Descrição da Discrepância:** O documento descreve o gatilho C4 como "15% + saldo restante na confirmação da 50w SMA". Não fica claro se a confirmação exige uma vela semanal fechando *acima* da média de 50 semanas após o mercado ter atingido o fundo, ou se exige rejeição/reteste. Além disso, se o ciclo inverter em C1 (-45%) e voltar a romper a 50w SMA sem ter atingido C2 e C3, a regra de "saldo restante" alocaria 15% + 40% (saldo de C2+C3) = 55% de uma só vez? Isso precisa estar estritamente formalizado.
* **Recomendação:** Definir matematicamente o gatilho C4: *"Acionado no primeiro fechamento semanal (domingo 21h BRT) acima da 50w SMA após ao menos um degrau de acumulação ter sido executado. O aporte corresponderá a 15% da reserva base somado a quaisquer saldos remanescentes de degraus anteriores (C1..C3) que não foram acionados"*.

#### 6. Falta de Diagrama e Regras de Transição de Estado do Ciclo
* **Severidade:** 🟡 Major
* **Escopo Afetado:** Linhas 196–197 ([`strategy_state`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L196-L197))
* **Descrição da Discrepância:** A tabela SQLite define `active_phase IN ('ACCUMULATION', 'DISTRIBUTION', 'COMPLETED')`. O documento não detalha em qual momento e sob quais condições exatas a máquina de estados migra de `ACCUMULATION` para `DISTRIBUTION`, ou o que ocorre se o Stop 1 for acionado em uma correção de meio de ciclo (a fase retrocede para `ACCUMULATION` ou permanece em `DISTRIBUTION`?).
* **Recomendação:** Incluir uma tabela ou diagrama de estados finitos no plano arquitetural especificando os eventos de transição entre as fases.

#### 7. Indefinição da Cadência de Execução das Vendas V1–V5 (Fechamento Semanal vs. Alvo Contínuo)
* **Severidade:** 🟡 Major
* **Escopo Afetado:** Linhas 14, 33–34, 109 ([`Technical Plan`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L109))
* **Descrição da Discrepância:** O documento deixa claro que os *Trailing Stops* avaliam fechamentos semanais dominicais às 21h00 BRT. No entanto, para as saídas V1–V5 em expansão parabólica ($1.0\times$, $1.3\times$, etc.), não é evidente se o investidor deve manter ordens limite pré-cadastradas na corretora (acionadas em tempo real) ou se a avaliação aguarda estritamente o candle dominical das 21h00 BRT. Em topos parabólicos, spikes repentinos podem tocar o múltiplo em uma terça-feira e recuar 30% antes do domingo, perdendo a realização de lucros.
* **Recomendação:** Explicitar a diretriz: se as vendas V1–V5 dependem exclusivamente da avaliação semanal dominical (para evitar pavios falsos), ou se o sistema deve emitir ordens limites prévias para serem posicionadas no livro.

---

### 🟢 Nits (Melhorias de Clareza e Documentação)

#### 8. Acrônimos Sem Expansão Inline na Primeira Menção
* **Severidade:** 🟢 Nit
* **Escopo Afetado:** Linhas 13, 15, 254, 275, 287
* **Descrição:** Termos como MVRV (Market Value to Realized Value), DARF (Documento de Arrecadação de Receitas Federais), GCAP (Ganhos de Capital), IOF (Imposto sobre Operações Financeiras) e FGC (Fundo Garantidor de Créditos) aparecem sem expansão, elevando a carga cognitiva de leitores novos.
* **Recomendação:** Expandir a sigla na primeira menção ou incluir um glossário no início do documento.

#### 9. "Emissão de Guia DARF" vs. Relatório de Dados para Preenchimento
* **Severidade:** 🟢 Nit
* **Escopo Afetado:** Linhas 15, 39, 210, 315
* **Descrição:** A expressão "emissão de guia DARF (código 4600)" pode fazer o leitor supor que o BitSignal gera o PDF/código de barras oficial do SicalcWeb via integração com a API da Receita Federal. Na verdade, o sistema calcula o valor e apresenta o relatório de apuração para preenchimento manual pelo usuário.
* **Recomendação:** Substituir "emissão de guia DARF" por "cálculo e emissão de relatório fiscal de DARF (código 4600)".

#### 10. Exclusão Explícita de Escopo para a IN RFB 1.888/2019
* **Severidade:** 🟢 Nit
* **Escopo Afetado:** Linhas 23 e 43–49
* **Descrição:** A IN 1888/2019 é citada no problema, mas a seção Non-Goals não esclarece que a geração de arquivos mensais para o portal e-CAC está fora de escopo (uma vez que operações em exchanges domiciliadas no Brasil são informadas diretamente pela própria exchange, dispensando o usuário, conforme art. 6º, I da IN 1888).
* **Recomendação:** Adicionar uma nota em Non-Goals frisando que a obrigação acessória da IN 1888 é suprida pela exchange nacional parceira.

#### 11. Arquivo Autoreferencial na Tabela de Implementação
* **Severidade:** 🟢 Nit
* **Escopo Afetado:** Linha 326 ([`Detailed Implementation Plan`](file:///c:/Users/gsame/projetos/bitsignal/docs/designs/bitcoin_national_execution_strategy.md#L326))
* **Descrição:** A tabela lista `docs/designs/bitcoin_national_execution_strategy.md` com a ação "Criar", sendo que este é o próprio documento em revisão.
* **Recomendação:** Alterar a ação para "Atualizar / Manter" ou remover a linha para evitar redundância circular.

#### 12. Fluxo de Confirmação Humana (*Human-in-the-Loop*)
* **Severidade:** 🟢 Nit
* **Escopo Afetado:** Linhas 68, 89, 319
* **Descrição:** O CUJ diz: "Após a confirmação da execução pelo operador, o sistema registra a transação...". Deve ficar evidente na arquitetura que a confirmação é manual via comando CLI (`bitsignal strategy-record-tx`) ou tela do Streamlit, confirmando que o Telegram é apenas um despachante unidirecional.
* **Recomendação:** Acrescentar uma breve menção no texto explicando que o feedback de confirmação é inserido pelo operador através da CLI ou da aba de estratégia no Streamlit.
