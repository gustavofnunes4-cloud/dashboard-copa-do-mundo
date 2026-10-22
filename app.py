"""Dashboard de público e finanças dos ciclos da Copa do Mundo (2010–2022)."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PASTA = Path(__file__).resolve().parent
ANOS = [2010, 2014, 2018, 2022]
SEDES = {2010: "África do Sul", 2014: "Brasil", 2018: "Rússia", 2022: "Catar"}
AZUL = "#1C64F2"

st.set_page_config(page_title="Copas do Mundo | Dados e economia", page_icon="⚽", layout="wide")

st.markdown(
    """<style>
    .block-container {padding-top: 2.1rem; max-width: 1250px;}
    div[data-testid="stMetric"] {background: #F1F6FF; border: 1px solid #DCE8FC;
      border-radius: 13px; padding: 18px 20px;}
    div[data-testid="stMetricLabel"] {color: #25456B;}
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_data
def carregar_publico(caminho: str) -> pd.DataFrame:
    tabela = pd.read_csv(caminho, dtype={"score": "string"}, encoding="utf-8-sig")
    colunas = {"year", "attendance", "city", "stadium", "team1", "team2", "score"}
    faltantes = colunas - set(tabela.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV de público: {', '.join(sorted(faltantes))}")
    tabela["year"] = pd.to_numeric(tabela["year"], errors="coerce")
    tabela["attendance"] = pd.to_numeric(tabela["attendance"], errors="coerce")
    return tabela.loc[tabela["year"].isin(ANOS)].copy()


@st.cache_data
def carregar_financas(caminho: str) -> pd.DataFrame:
    tabela = pd.read_csv(caminho, encoding="utf-8-sig")
    colunas = {"year", "pais", "receita_fifa_milhoes", "resultado_liquido_milhoes"}
    faltantes = colunas - set(tabela.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV financeiro: {', '.join(sorted(faltantes))}")
    for coluna in ("year", "receita_fifa_milhoes", "resultado_liquido_milhoes"):
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    return tabela.loc[tabela["year"].isin(ANOS)].copy().sort_values("year")


def formatar_numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def mostrar_grafico(figura, chave: str) -> None:
    figura.update_layout(
        template="plotly_white",
        font=dict(family="Arial", size=13),
        margin=dict(l=16, r=16, t=52, b=24),
        hoverlabel=dict(bgcolor="white"),
    )
    st.plotly_chart(figura, use_container_width=True, key=chave)


st.title("⚽ Copas do Mundo: público e economia")
st.caption("Comparação das edições de 2010, 2014, 2018 e 2022 • Dados históricos e relatórios financeiros")

try:
    publico = carregar_publico(str(PASTA / "attendance.csv"))
    financas = carregar_financas(str(PASTA / "economia_copas.csv"))
except (FileNotFoundError, ValueError, pd.errors.ParserError) as erro:
    st.error(f"Não foi possível carregar os arquivos: {erro}")
    st.info("Mantenha app.py, attendance.csv e economia_copas.csv na mesma pasta.")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    ano = st.selectbox(
        "Edição da Copa",
        ANOS,
        index=1,
        format_func=lambda valor: f"{valor} — {SEDES[valor]}",
    )
    st.caption("O filtro altera os indicadores, os jogos e as cidades. Os gráficos comparativos mostram todas as edições.")
    st.divider()
    st.subheader("Sobre os dados")
    st.write("**Público:** registros de espectadores por partida.")
    st.write("**Economia:** receitas e resultados líquidos da FIFA em ciclos de quatro anos.")

jogos = publico.loc[publico["year"] == ano].copy()
publicos_validos = jogos["attendance"].dropna()
if jogos.empty or publicos_validos.empty:
    st.warning("Não há registros de público válidos para esta edição.")
    st.stop()

st.subheader(f"Visão geral • {ano} — {SEDES[ano]}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Público acumulado", formatar_numero(publicos_validos.sum()))
c2.metric("Média por partida", formatar_numero(publicos_validos.mean()))
c3.metric("Partidas registradas", formatar_numero(len(jogos)))
c4.metric("Cidades-sede", formatar_numero(jogos["city"].nunique()))

aba_publico, aba_cidades, aba_economia, aba_dados = st.tabs(
    ["📊 Público por Copa", "🏟️ Cidades-sede", "💰 Economia da FIFA", "📋 Dados e fontes"]
)

with aba_publico:
    st.markdown("### Como o público mudou entre as Copas?")
    resumo = (
        publico.groupby("year", as_index=False)
        .agg(publico_total=("attendance", "sum"), media=("attendance", "mean"), jogos=("attendance", "size"))
        .sort_values("year")
    )
    metrica = st.radio("Comparar", ["Média por jogo", "Público acumulado"], horizontal=True)
    coluna = "media" if metrica == "Média por jogo" else "publico_total"
    fig = px.bar(
        resumo, x="year", y=coluna, color="year",
        color_discrete_sequence=[AZUL, "#22A6A1", "#F2A541", "#7246BF"],
        text_auto=",.0f",
        labels={"year": "Copa", coluna: "Espectadores"},
        title=f"{metrica} (2010–2022)",
    )
    fig.update_xaxes(type="category")
    fig.update_layout(showlegend=False)
    mostrar_grafico(fig, "grafico_publico")
    maior_media = resumo.loc[resumo["media"].idxmax()]
    st.info(
        f"A maior média por partida nesta base foi em **{int(maior_media['year'])}**, "
        f"com **{formatar_numero(maior_media['media'])}** espectadores por jogo. "
        "Compare também a quantidade de partidas antes de interpretar totais."
    )

with aba_cidades:
    st.markdown(f"### Onde houve mais público em {ano}?")
    cidades = (
        jogos.groupby("city", as_index=False)
        .agg(publico_total=("attendance", "sum"), partidas=("attendance", "size"))
        .sort_values("publico_total", ascending=False)
        .head(10)
    )
    fig = px.bar(
        cidades.sort_values("publico_total"), x="publico_total", y="city",
        orientation="h", text_auto=",.0f", color_discrete_sequence=[AZUL],
        title=f"10 cidades-sede com maior público acumulado — {ano}",
        labels={"publico_total": "Espectadores acumulados", "city": "Cidade"},
        hover_data={"partidas": True},
    )
    mostrar_grafico(fig, "grafico_cidades")
    lider = cidades.iloc[0]
    st.success(
        f"**{lider['city']}** recebeu o maior público acumulado: "
        f"**{formatar_numero(lider['publico_total'])}** espectadores "
        f"em **{int(lider['partidas'])}** partidas."
    )
    st.caption("Público de estádio não equivale a turistas únicos nem a receita de turismo. Uma pessoa pode assistir a vários jogos.")

with aba_economia:
    st.markdown("### Quanto a FIFA arrecadou e qual foi seu resultado líquido?")
    st.warning(
        "Estes valores pertencem à **FIFA, em ciclos de quatro anos**. "
        "Não representam os gastos públicos, as receitas turísticas ou o lucro/prejuízo dos países-sede."
    )
    fig = px.bar(
        financas, x="year", y="receita_fifa_milhoes", text_auto=",.0f",
        color_discrete_sequence=[AZUL],
        labels={"year": "Copa", "receita_fifa_milhoes": "US$ milhões"},
        title="Receitas da FIFA por ciclo (US$ milhões)",
    )
    fig.update_xaxes(type="category")
    mostrar_grafico(fig, "grafico_receitas")

    fig_resultado = px.bar(
        financas, x="year", y="resultado_liquido_milhoes", text_auto=",.0f",
        color_discrete_sequence=["#159B89"],
        labels={"year": "Copa", "resultado_liquido_milhoes": "US$ milhões"},
        title="Resultado líquido da FIFA por ciclo (US$ milhões)",
    )
    fig_resultado.update_xaxes(type="category")
    mostrar_grafico(fig_resultado, "grafico_resultados")

    maior = financas.loc[financas["resultado_liquido_milhoes"].idxmax()]
    menor = financas.loc[financas["resultado_liquido_milhoes"].idxmin()]
    c1, c2 = st.columns(2)
    c1.metric("Maior resultado líquido", f"{int(maior['year'])} · US$ {formatar_numero(maior['resultado_liquido_milhoes'])} mi")
    c2.metric("Menor resultado líquido", f"{int(menor['year'])} · US$ {formatar_numero(menor['resultado_liquido_milhoes'])} mi")
    st.caption(
        "Valores nominais, sem correção pela inflação. Resultado líquido é uma medida contábil "
        "do ciclo completo e não deve ser calculado subtraindo investimentos da receita. "
        "A FIFA adotou mudanças contábeis entre os períodos, o que limita comparações estritas."
    )
    st.dataframe(
        financas.rename(columns={
            "year": "Copa", "pais": "País-sede",
            "receita_fifa_milhoes": "Receita (US$ milhões)",
            "resultado_liquido_milhoes": "Resultado líquido (US$ milhões)",
        }),
        hide_index=True, use_container_width=True,
    )

with aba_dados:
    st.markdown("### Conferência da base de jogos")
    st.dataframe(
        jogos[["date", "team1", "team2", "score", "attendance", "stadium", "city", "stage", "phase"]]
        .rename(columns={"date": "Data", "team1": "Seleção 1", "team2": "Seleção 2",
                         "score": "Placar", "attendance": "Público", "stadium": "Estádio",
                         "city": "Cidade", "stage": "Etapa original", "phase": "Fase geral"}),
        use_container_width=True, hide_index=True,
    )
    st.caption(f"Registros nesta edição: {len(jogos)} • Público ausente: {jogos['attendance'].isna().sum()}")
    st.info(
        "Qualidade dos dados: em algumas edições, a coluna original 'stage' repete "
        "'phase' no mata-mata. Essa diferença foi mantida e não interfere nos "
        "gráficos de público por ano ou cidade."
    )
    st.markdown("### Fontes e metodologia")
    st.markdown(
        """
        - **Público:** arquivo `attendance.csv` fornecido no projeto, com registros de partidas e referências no campo `source`.
        - **2010:** [Relatório Financeiro FIFA 2010](https://static.poder360.com.br/2022/11/relatorio-anual-fifa-2010.pdf).
        - **2014:** [Relatório Financeiro FIFA 2014](https://img.fifa.com/image/upload/e4e5lkxrbqvgscxgjnhx.pdf).
        - **2018:** [Relatório Financeiro FIFA 2018](https://static.poder360.com.br/2022/11/relatorio-anual-fifa-2018.pdf).
        - **2022:** [Relatório Anual FIFA 2022](https://publications.fifa.com/en/annual-report-2022/finances/2019-2022-cycle-in-review/2022-financial-highlights/).

        **Método:** somar o público das partidas de cada cidade ou ano e calcular a média por jogo.
        Os dados econômicos são valores publicados pela FIFA referentes a períodos de quatro anos:
        2007–2010, 2011–2014, 2015–2018 e 2019–2022.
        """
    )

st.divider()
st.caption("Dashboard educacional • Copa do Mundo 2010–2022 • Público e finanças são medidas distintas")
