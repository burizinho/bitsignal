"""Gera o manual do BitSignal em PDF (A4, português): docs/manual/Manual_BitSignal.pdf.

Uso: python docs/manual/build_manual.py
Requer reportlab e as fontes Segoe UI do Windows (C:/Windows/Fonts). Os números do exemplo
(seções 3 e 6) são da semana de 08/11/2026; atualize-os aqui para gerar uma versão nova.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = str(Path(__file__).resolve().parent / "Manual_BitSignal.pdf")
URL = "https://bitsignal-xg66updc23ul6o7jxdyzud.streamlit.app/"

pdfmetrics.registerFont(TTFont("UI", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", "C:/Windows/Fonts/segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-SB", "C:/Windows/Fonts/seguisb.ttf"))
pdfmetrics.registerFont(TTFont("UI-L", "C:/Windows/Fonts/segoeuisl.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI", boldItalic="UI-B")

ORANGE = colors.HexColor("#E8820C")
INK = colors.HexColor("#1F2328")
MUTED = colors.HexColor("#5B6470")
LINE = colors.HexColor("#D9DEE4")
SOFT = colors.HexColor("#F5F7F9")
GREEN = colors.HexColor("#1E7F4F")
BLUE = colors.HexColor("#2B5FA8")
RED = colors.HexColor("#B4372F")
WARN_BG = colors.HexColor("#FFF4E5")
INFO_BG = colors.HexColor("#EEF4FB")

body = ParagraphStyle("body", fontName="UI", fontSize=10.5, leading=15.5, textColor=INK, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=9, leading=12.5, textColor=MUTED)
h1 = ParagraphStyle("h1", fontName="UI-B", fontSize=19, leading=24, textColor=INK, spaceBefore=4, spaceAfter=10)
h2 = ParagraphStyle("h2", fontName="UI-SB", fontSize=13, leading=18, textColor=INK, spaceBefore=10, spaceAfter=5)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)
cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=13, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="UI-SB")
num = ParagraphStyle("num", parent=body, leftIndent=18, bulletIndent=0, spaceAfter=4)


def P(text, style=body):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(t, bullet, bulletText="•") for t in items]


def steps(items):
    return [Paragraph(t, num, bulletText=f"{i}.") for i, t in enumerate(items, 1)]


def box(content, bg=INFO_BG, border=BLUE, title=None):
    inner = []
    if title:
        inner.append(Paragraph(f"<font name='UI-SB'>{title}</font>", ParagraphStyle("bt", parent=body, spaceAfter=3)))
    inner += [c if not isinstance(c, str) else P(c) for c in content]
    t = Table([[inner]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def table(rows, widths, header=True):
    data = [[Paragraph(c, cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(st))
    return t


def phase_table():
    rows = [
        ("ACUMULAR", GREEN, "O preço está barato pelos indicadores e o modelo armou o recomeço do ciclo.",
         "Comprar aos poucos: 2% da reserva por semana (4% se estiver muito barato)."),
        ("MANTER", BLUE, "Nem caro nem barato, e nada foi vendido neste ciclo.",
         "Não fazer nada. É a fase mais comum."),
        ("DISTRIBUIR", ORANGE, "O preço ficou caro, ou o mercado começou a virar depois de um topo.",
         "Vender aos poucos, até a venda acumulada-alvo do ciclo (no máximo 50%)."),
    ]
    data = [[Paragraph("<font name='UI-SB'>Fase</font>", cell), Paragraph("<font name='UI-SB'>Quando aparece</font>", cell),
             Paragraph("<font name='UI-SB'>O que o modelo sugere</font>", cell)]]
    for name, col, when, what in rows:
        data.append([Paragraph(f"<font name='UI-B' color='white'>{name}</font>", cell), Paragraph(when, cell), Paragraph(what, cell)])
    t = Table(data, colWidths=[30 * mm, 70 * mm, 70 * mm])
    st = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, (_, col, _, _) in enumerate(rows, 1):
        st.append(("BACKGROUND", (0, i), (0, i), col))
    t.setStyle(TableStyle(st))
    return t


def cycle_strip():
    """Faixa simples: ACUMULAR -> MANTER -> DISTRIBUIR -> (novo ciclo)."""
    labels = [("ACUMULAR", GREEN), ("MANTER", BLUE), ("DISTRIBUIR", ORANGE), ("ciclo novo →\nACUMULAR", GREEN)]
    cells = [[Paragraph(f"<font name='UI-B' color='white'>{n.replace(chr(10), '<br/>')}</font>",
                        ParagraphStyle("c", parent=cell, alignment=TA_CENTER)) for n, _ in labels]]
    arrows = Table(cells, colWidths=[40 * mm] * 4, rowHeights=[16 * mm])
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEAFTER", (0, 0), (2, 0), 4, colors.white)]
    for i, (_, col) in enumerate(labels):
        st.append(("BACKGROUND", (i, 0), (i, 0), col))
    arrows.setStyle(TableStyle(st))
    return arrows


def on_page(canv, doc):
    if doc.page == 1:
        return
    canv.saveState()
    canv.setFont("UI", 8.5)
    canv.setFillColor(MUTED)
    canv.drawString(20 * mm, 12 * mm, "BitSignal · manual do painel")
    canv.drawRightString(190 * mm, 12 * mm, f"página {doc.page}")
    canv.setStrokeColor(LINE)
    canv.line(20 * mm, 16 * mm, 190 * mm, 16 * mm)
    canv.restoreState()


def cover(canv, doc):
    canv.saveState()
    w, h = A4
    canv.setFillColor(INK)
    canv.rect(0, h - 120 * mm, w, 120 * mm, stroke=0, fill=1)
    canv.setFillColor(ORANGE)
    canv.rect(0, h - 123 * mm, w, 3 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("UI-B", 34)
    canv.drawString(20 * mm, h - 62 * mm, "BitSignal")
    canv.setFont("UI-L", 17)
    canv.drawString(20 * mm, h - 76 * mm, "Manual do painel: como ler e como usar")
    canv.setFont("UI", 11)
    canv.setFillColor(colors.HexColor("#C9D1D9"))
    canv.drawString(20 * mm, h - 90 * mm, "Modelo de ciclo do bitcoin · painel só de leitura · versão de novembro de 2026")
    canv.restoreState()


story = []

# ---------------------------------------------------------------- capa
story.append(Spacer(1, 122 * mm))
story.append(P("<font name='UI-SB' size='13'>Para quem é este manual</font>"))
story.append(P("Para quem quer acompanhar o painel do BitSignal e entender o que cada número quer dizer, "
               "sem precisar saber programar nem conhecer os indicadores por trás dele."))
story.append(Spacer(1, 4))
story.append(P(f"<font name='UI-SB'>Endereço do painel:</font> <link href='{URL}' color='#2B5FA8'>{URL}</link>"))
story.append(Spacer(1, 10))
story.append(box([
    "O BitSignal é um projeto pessoal e <b>experimental</b>. Ele mostra o que um modelo diria para a semana, "
    "não diz o que você deve fazer. <b>Não é recomendação de investimento.</b> Bitcoin é um ativo muito volátil: "
    "você pode perder dinheiro. Cada um decide e responde pelas próprias operações.",
], bg=WARN_BG, border=ORANGE, title="Antes de tudo"))
story.append(Spacer(1, 10))
story.append(P("<font name='UI-SB'>Conteúdo</font>"))
toc = ParagraphStyle("toc", parent=body, spaceAfter=1, leftIndent=4)
for item in ["1. O que é o BitSignal (e o que ele não é)", "2. A ideia em uma página",
             "3. Abrindo o painel e lendo a linha do topo", "4. As três fases e o que fazer em cada uma",
             "5. As abas do painel", "6. A calculadora, passo a passo", "7. Uma rotina semanal simples",
             "8. Limites, riscos e perguntas frequentes", "9. Glossário"]:
    story.append(P(item, toc))
story.append(PageBreak())

# ---------------------------------------------------------------- 1
story.append(P("1. O que é o BitSignal", h1))
story.append(P("O BitSignal é um painel na internet que olha, uma vez por semana, para alguns indicadores "
               "públicos do bitcoin e responde a três perguntas:"))
story += bullets([
    "<b>Em que fase do ciclo estamos?</b> Acumular, manter ou distribuir.",
    "<b>Quanto da posição já deveria ter sido vendido neste ciclo?</b> Um percentual, chamado "
    "<i>venda acumulada-alvo</i>.",
    "<b>Quanto comprar nesta semana?</b> Um percentual da reserva em dinheiro, ou nada.",
])
story.append(P("O que ele <b>não</b> faz:", h2))
story += bullets([
    "Não compra nem vende nada. Não se conecta a corretora nenhuma.",
    "Não manda alertas, e-mails ou mensagens.",
    "Não guarda os seus dados. O que você digita na calculadora some quando fecha a página.",
    "Não conhece as suas operações. Você continua anotando tudo na sua própria planilha.",
    "Não calcula impostos nem custos de corretagem. Todos os valores são brutos.",
])
story.append(P("De onde vêm os dados", h2))
story.append(P("Os indicadores vêm da <b>CoinMetrics</b> (dados públicos e gratuitos, licença de uso não comercial). "
               "O preço “agora”, mostrado só como referência, vem do Yahoo Finance. O modelo só usa "
               "<b>semanas fechadas</b> (de segunda a domingo): o veredito muda no máximo uma vez por semana."))

# ---------------------------------------------------------------- 2
story.append(P("2. A ideia em uma página", h1))
story.append(P("O bitcoin costuma andar em ciclos de alguns anos: sobe muito, cai muito e volta a subir. "
               "O modelo tenta fazer o que quase ninguém consegue fazer no calor do momento:"))
story += bullets([
    "<b>Vender aos poucos</b> quando o preço fica caro, sem tentar acertar o topo exato.",
    "<b>Comprar aos poucos</b> quando o preço fica barato, sem tentar acertar o fundo exato.",
    "<b>Nunca vender mais da metade</b> da posição de um ciclo. A outra metade fica sempre guardada.",
    "<b>Reinvestir o dinheiro das vendas</b> quando um ciclo novo começa.",
])
story.append(Spacer(1, 4))
story.append(cycle_strip())
story.append(Spacer(1, 6))
story.append(P("Para decidir se está caro ou barato, o painel junta seis indicadores conhecidos do mercado num "
               "<b>score de 0 a 100</b>: perto de 0 é barato, perto de 100 é caro. Um segundo mecanismo, o "
               "<b>detector de reversão</b>, observa se o preço começou a cair de verdade depois de um topo; ele "
               "pode mandar vender mesmo quando o score ainda não chegou lá em cima.", body))
story.append(table([
    ["Situação", "O que o modelo faz"],
    ["Score mínimo da semana chega a 85 / 90 / 93", "Venda acumulada-alvo sobe para 5% / 15% / 30%"],
    ["Detector de reversão no nível 1 / 2 / 3", "Venda acumulada-alvo sobe para 10% / 25% / 50%"],
    ["Score máximo de 20 ou menos por 2 semanas", "Arma o recomeço do ciclo: fase ACUMULAR, compras semanais"],
    ["Score máximo ≤ 20 (ou ≤ 10) na fase ACUMULAR", "Compra 2% (ou 4%) da reserva-base na semana"],
    ["Score mínimo volta a 30 ou mais por 2 semanas", "Começa um ciclo novo: compra com todo o caixa e a venda-alvo volta a 0%"],
], [85, 85]))
story.append(Spacer(1, 4))
story.append(P("A venda acumulada-alvo funciona como uma <b>catraca</b>: dentro de um ciclo, ela só sobe. "
               "Se o preço melhorar depois, ela não volta para baixo; só zera quando começa um ciclo novo.", small))

# ---------------------------------------------------------------- 3
story.append(P("3. Abrindo o painel e lendo a linha do topo", h1))
story += steps([
    f"Abra <link href='{URL}' color='#2B5FA8'>o endereço do painel</link> no celular ou no computador.",
    "Espere alguns segundos. Se o painel estava parado, a primeira abertura pode demorar um pouco mais.",
    "Leia a frase logo abaixo do título. Ela resume a semana inteira.",
])
story.append(P("Um exemplo real (semana fechada em 08/11/2026):", h2))
story.append(box([
    "<i>Semana fechada em 08/11/2026 · <b>ACUMULAR</b> · Venda acumulada-alvo no ciclo: <b>25%</b> da posição-base "
    "(ciclo iniciado em 12/11/2023) · Compra programada nesta semana: <b>2%</b> da reserva-base · "
    "Motivo: reinício armado em 2025-12-14; score_max 15.5 → compra 2%</i>",
], bg=SOFT, border=MUTED))
story.append(Spacer(1, 6))
story.append(table([
    ["Trecho", "O que quer dizer"],
    ["Semana fechada em 08/11/2026", "A última semana completa que entrou no cálculo (vai até domingo)."],
    ["ACUMULAR", "A fase atual. Veja a seção 4."],
    ["Venda acumulada-alvo: 25%", "Neste ciclo, o modelo diria que 25% da posição-base já deveria ter sido vendido "
     "(somando todas as vendas do ciclo, não só as desta semana)."],
    ["Ciclo iniciado em 12/11/2023", "Quando começou o ciclo atual. A posição-base é o que você tinha nessa data."],
    ["Compra programada: 2%", "Quanto comprar nesta semana, em % da reserva-base. Um traço (—) significa nenhuma compra."],
    ["Motivo", "O porquê do veredito, em poucas palavras."],
], [55, 115]))
story.append(Spacer(1, 8))
story.append(box([
    "Se aparecer <b>“Dados desatualizados”</b> ou <b>“fonte indisponível”</b>, o painel <b>não mostra veredito</b> "
    "de propósito: ele prefere não dizer nada a dizer algo com dados velhos. Clique em “Tentar de novo” "
    "depois de alguns minutos.",
], title="Quando não aparece veredito"))

# ---------------------------------------------------------------- 4
story.append(P("4. As três fases e o que fazer em cada uma", h1))
story.append(phase_table())
story.append(Spacer(1, 8))
story.append(P("Dois detalhes que costumam confundir", h2))
story += bullets([
    "<b>Na fase ACUMULAR, a venda-alvo continua aparecendo</b> (no exemplo, 25%). Ela é a do ciclo que ainda "
    "não terminou, mostrada só para registro. Nessa fase não há venda nova; o destaque é a compra.",
    "<b>A semana do ciclo novo é especial.</b> Quando o recomeço se confirma, o painel mostra em destaque: "
    "“comprar com <b>todo o caixa disponível</b> (inclui o produto das vendas)”. É assim que o dinheiro "
    "das vendas do ciclo anterior volta para o bitcoin. Essa regra é a novidade do <b>modelo v2</b>, a "
    "versão que o painel usa hoje.",
])
story.append(P("Posição-base e reserva-base", h2))
story += bullets([
    "<b>Posição-base</b> é quanto bitcoin você tinha no início do ciclo. As vendas são calculadas sobre ela, "
    "e as compras feitas durante a fase ACUMULAR não mudam a base do ciclo atual.",
    "<b>Reserva-base</b> é o dinheiro que você separou para comprar bitcoin nos momentos baratos. As compras "
    "semanais são um percentual dela.",
])

# ---------------------------------------------------------------- 5
story.append(P("5. As abas do painel", h1))
story.append(table([
    ["Aba", "O que tem"],
    ["Semana", "O medidor do score (0 a 100), o medidor da venda acumulada-alvo (até 50%), o estado do detector "
     "de reversão e a <b>calculadora</b>."],
    ["Insumos", "Os seis indicadores da semana, cada um com o valor e se estava disponível. Serve para conferir "
     "de onde veio o score."],
    ["Ciclo e eventos", "O gráfico do preço com as fases coloridas e a lista do que aconteceu no ciclo atual "
     "(vendas, recomeço armado etc.)."],
    ["Backtest", "Como o modelo teria se saído no passado, comparado a simplesmente comprar e guardar. Lembre: "
     "passado não garante nada (veja a seção 8)."],
    ["Glossário", "As definições curtas dos termos."],
], [35, 135]))

# ---------------------------------------------------------------- 6
story.append(P("6. A calculadora, passo a passo", h1))
story.append(P("Os percentuais são iguais para todo mundo; as quantidades dependem de quanto cada um tem. "
               "A calculadora faz essa conta. Ela fica na aba <b>Semana</b>, num bloco chamado "
               "“Calculadora: converter os percentuais em valores”."))
story += steps([
    "Clique no título do bloco para abri-lo.",
    "Preencha só o que quiser: <b>BTC no início do ciclo</b>, <b>BTC já vendidos neste ciclo</b>, "
    "<b>reserva-base (USD)</b> e <b>caixa disponível agora (USD)</b>.",
    "Leia o resultado logo abaixo dos campos. Ele se atualiza a cada número digitado.",
])
story.append(P("Exemplo", h2))
story.append(P("Com o veredito da semana de 08/11/2026 (venda-alvo 25%, compra 2%) e o bitcoin a US$ 75.190:"))
story.append(table([
    ["Você digita", "A calculadora mostra"],
    ["BTC no início do ciclo: 1", "Venda acumulada-alvo do ciclo: 0,25 BTC. Falta vender: 0,25 BTC (≈ US$ 18.797)."],
    ["BTC já vendidos: 0,10", "Falta vender passa a ser 0,15 BTC."],
    ["Reserva-base: US$ 1.000", "Compra desta semana: US$ 20,00 ≈ 0,00026599 BTC."],
    ["Caixa disponível: US$ 15", "A compra fica limitada a US$ 15 (o que há em caixa)."],
], [60, 110]))
story.append(Spacer(1, 8))
story.append(box([
    "Os números digitados ficam só na sua sessão do navegador. Nada é gravado, ninguém mais vê e nada vira "
    "registro de operações. Ao fechar a página, eles somem. Os valores são brutos: sem taxas nem impostos.",
], title="Privacidade"))

# ---------------------------------------------------------------- 7
story.append(P("7. Uma rotina semanal simples", h1))
story += steps([
    "<b>Segunda ou terça-feira</b>, abra o painel (os dados de domingo costumam chegar na segunda).",
    "Leia a linha do topo: fase, venda-alvo e compra da semana.",
    "Se quiser quantidades, use a calculadora com os números da sua planilha.",
    "Decida por conta própria se vai seguir ou não. Se fizer alguma operação, anote na sua planilha.",
    "Nas semanas de <b>MANTER</b> (a maioria), não há nada a fazer.",
])
story.append(P("Paciência faz parte: um ciclo do bitcoin leva anos, e o modelo foi feito para mudar de ideia "
               "poucas vezes. Muitas semanas seguidas sem novidade é o comportamento esperado.", small))

# ---------------------------------------------------------------- 8
story.append(P("8. Limites, riscos e perguntas frequentes", h1))
story.append(box([
    "<b>O modelo não foi aprovado no teste histórico.</b> Na avaliação feita sobre 2019–2026, a primeira versão "
    "(v1) protegeu bem nas quedas, mas terminou com cerca de <b>1/3 do patrimônio</b> de quem simplesmente "
    "comprou e guardou, porque o dinheiro das vendas ficava parado. A versão atual (v2) corrige isso "
    "reinvestindo o caixa no ciclo novo, mas essa correção foi escolhida <b>depois</b> de ver o resultado. "
    "Por isso ela só será considerada aprovada com <b>dados futuros</b>: a avaliação vai até o próximo "
    "recomeço de ciclo depois de uma fase de venda, ou até o fim de 2030.",
], bg=WARN_BG, border=ORANGE, title="O ponto mais importante"))
story.append(Spacer(1, 6))
story += bullets([
    "<b>Passado não garante futuro.</b> Os ciclos do bitcoin podem mudar de forma.",
    "<b>Uma fonte só.</b> Se a CoinMetrics mudar ou sair do ar, o painel fica sem veredito até voltar.",
    "<b>Sem custos e sem impostos.</b> Na vida real, os dois reduzem o resultado.",
    "<b>Não é para dinheiro que você vai precisar.</b> Os ciclos podem levar anos para se completar.",
])
story.append(P("Perguntas frequentes", h2))
faq = [
    ("O painel diz 25% de venda-alvo. Tenho que vender 25% hoje?",
     "Não. É o total acumulado do ciclo. Se você já vendeu parte disso antes, falta só a diferença "
     "(a calculadora faz essa conta). E é uma referência do modelo, não uma ordem."),
    ("Por que o veredito não muda todo dia?",
     "Porque o modelo usa só semanas fechadas. O preço do dia aparece como referência, mas não muda o veredito."),
    ("Comecei agora. O que faço com a venda-alvo do ciclo atual?",
     "Para quem entra no meio de um ciclo, a venda-alvo já acumulada não vale retroativamente. Siga apenas o que "
     "mudar daqui para frente, ou espere o próximo ciclo começar."),
    ("O que é o “modelo v1” e o “v2”?",
     "São duas versões. As vendas são idênticas; o v2 só acrescenta a compra com todo o caixa quando começa "
     "um ciclo novo. O painel mostra o v2. O v1 continua registrado para comparação."),
    ("Meus dados ficam salvos em algum lugar?",
     "Não. O painel não tem login e não grava nada do que você digita."),
]
for q, a in faq:
    story.append(KeepTogether([P(f"<font name='UI-SB'>{q}</font>", ParagraphStyle("q", parent=body, spaceAfter=1)),
                               P(a, ParagraphStyle("a", parent=body, leftIndent=10))]))

# ---------------------------------------------------------------- 9
story.append(P("9. Glossário", h1))
story.append(table([
    ["Termo", "Significado"],
    ["Score de valuation", "Nota de 0 (barato) a 100 (caro) feita com seis indicadores do bitcoin."],
    ["Score mínimo / máximo", "Quando falta algum indicador, o score vira uma faixa; o modelo usa o mínimo para "
     "vender e o máximo para comprar, por prudência."],
    ["Posição-base", "Quanto bitcoin você tinha no início do ciclo. Base das vendas."],
    ["Venda acumulada-alvo", "Quanto da posição-base o modelo diria que já foi vendido no ciclo. Só sobe, até 50%."],
    ["Reserva-base", "Dinheiro separado para as compras nos momentos baratos."],
    ["Compra programada", "Percentual da reserva-base a comprar na semana (2% ou 4%)."],
    ["Compra no reinício", "Na semana em que começa um ciclo novo, comprar com todo o caixa disponível (modelo v2)."],
    ["Detector de reversão", "Mecanismo separado do score que percebe quando o preço começou a cair depois de um "
     "topo; tem três níveis (10%, 25%, 50%)."],
    ["Ciclo", "Período entre dois recomeços. Começa depois de uma fase barata (ACUMULAR)."],
    ["Semana fechada", "Semana de segunda a domingo já encerrada; só ela entra no cálculo."],
    ["Experimental", "O modelo ainda não passou na avaliação. Os números são referências, não recomendações."],
], [45, 125]))
story.append(Spacer(1, 10))
story.append(P("Dados: CoinMetrics Community (CC BY-NC 4.0), uso não comercial. Este manual não é recomendação "
               "de investimento.", small))

def keep_headings(flow):
    """Glue each heading to the next flowable so no heading ends a page alone."""
    out, i = [], 0
    while i < len(flow):
        f = flow[i]
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2") and i + 1 < len(flow):
            nxt = flow[i + 1]
            parts = list(nxt._content) if isinstance(nxt, KeepTogether) else [nxt]
            out.append(KeepTogether([f] + parts))
            i += 2
        else:
            out.append(f)
            i += 1
    return out


story = story[:story.index(next(s for s in story if isinstance(s, PageBreak))) + 1] + keep_headings(
    story[story.index(next(s for s in story if isinstance(s, PageBreak))) + 1:])

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                        bottomMargin=22 * mm, title="BitSignal — Manual do painel", author="BitSignal",
                        subject="Como ler e usar o painel do BitSignal")
doc.build(story, onFirstPage=cover, onLaterPages=on_page)
print("ok", OUT)
