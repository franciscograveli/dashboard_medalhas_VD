"""Dashboard Quadro de Medalhas Olímpicas (1992-2020) - Dash + Plotly Express."""
import math
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, Input, Output, State, dcc, html
from plotly.subplots import make_subplots

# ----------------------------------------------------------------- dados ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE_DIR, "Country_Medals.csv"))
# Padroniza nomes: um mesmo país com grafias diferentes entre edições e/ou nome
# que o mapa do Plotly reconhece.
NAME_FIXES = {
    "United States": "United States of America",
    "Macedonia": "North Macedonia",
}
df["Country_Name"] = df["Country_Name"].replace(NAME_FIXES)
df = df[df["Year"] >= 1992].copy()

# Entidades históricas que o mapa do Plotly não reconhece
NOT_ON_MAP = {
    "Czechoslovakia", "Yugoslavia", "Unified Team", "ROC",
    "Independent Olympic Athletes", "Independent Olympic Participants",
    "Serbia and Montenegro", "Kosovo",
}
missing_on_map = sorted(NOT_ON_MAP & set(df["Country_Name"]))

# ------------------------------------------------------------- constantes ---
MEDAL_COLS = ["Gold", "Silver", "Bronze"]
PT = {"Gold": "Ouro", "Silver": "Prata", "Bronze": "Bronze"}
MEDAL_COLOR = {"Gold": "#D4AF37", "Silver": "#A8A9AD", "Bronze": "#CD7F32"}
MEDAL_SCALE = {
    "Gold": [[0, "#FFF8DC"], [1, "#B8860B"]],
    "Silver": [[0, "#F2F2F2"], [1, "#5F6368"]],
    "Bronze": [[0, "#FBE9DA"], [1, "#8B4513"]],
}
BLUE = "#118DFF"
PALETTE = ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7",
           "#744EC2", "#197278", "#D64550", "#1AAB40", "#5F6B7A"]
INK, MUTED, GRID = "#252423", "#605E5C", "#EDEBE9"
OVERALL_RANK = (df[MEDAL_COLS].sum(axis=1).groupby(df["Country_Name"]).sum()
                .sort_values(ascending=False).index.tolist())
MAX_PIES = 4

HOSTS = df.groupby("Year")[["Host_city", "Host_country"]].first().reset_index()
year_options = [
    {"label": f"{r.Year} – {r.Host_city} ({r.Host_country})", "value": int(r.Year)}
    for r in HOSTS.itertuples()
]
country_options = [{"label": c, "value": c} for c in sorted(df["Country_Name"].unique())]
medal_options = [{"label": PT[c], "value": c} for c in MEDAL_COLS]

pio.templates.default = "plotly_white"
MAP_CONFIG = {"scrollZoom": False, "displayModeBar": False}
FIG_CONFIG = {"displayModeBar": False}


# --------------------------------------------------------------- helpers ---
def sel_cols(medals):
    """Medalhas escolhidas, na ordem Ouro/Prata/Bronze (vazio = todas)."""
    cols = [c for c in MEDAL_COLS if c in (medals or [])]
    return cols or list(MEDAL_COLS)


def metric(frame, cols):
    return frame[cols].sum(axis=1)


def medal_phrase(cols):
    if len(cols) == 3:
        return "medalhas"
    return "medalhas de " + " + ".join(PT[c].lower() for c in cols)


def fmt(n):
    return f"{int(n):,}".replace(",", ".")


def country_colors(countries):
    """Cor fixa por país (segue a entidade, não a posição no ranking atual)."""
    cmap, free = {}, list(PALETTE)
    for c in countries:
        if c in OVERALL_RANK[:10]:
            cmap[c] = PALETTE[OVERALL_RANK.index(c)]
            free.remove(cmap[c])
    for c in countries:
        cmap.setdefault(c, free.pop(0) if free else "#A19F9D")
    return cmap


def style(fig, title, h):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", x=0.01, xanchor="left", font=dict(size=15, color=INK)),
        height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Inter, Arial", size=12, color=MUTED),
        margin=dict(l=10, r=10, t=48, b=10),
        hoverlabel=dict(bgcolor="white", font_size=13, bordercolor=GRID),
    )
    return fig


# ------------------------------------------------------------------- app ---
app = Dash(__name__)
server = app.server  # usado pelo gunicorn no Render
app.title = "Quadro de Medalhas Olímpicas"


def card(*children, className="", **kw):
    kids = list(kw.pop("children", None) or children)
    return html.Div(kids, className=f"card {className}".strip(), **kw)


app.layout = html.Div([
    html.Div(className="app-header", children=[
        html.Div([
            html.H1("Quadro de Medalhas Olímpicas"),
            html.Div("Jogos de Verão · 1992–2020 · 8 edições · 136 países", className="sub"),
        ]),
        html.Div(className="rings", children=[
            html.Span(style={"borderColor": c}) for c in
            ["#0085C7", "#F4C300", "#FFFFFF", "#009F3D", "#DF0024"]
        ]),
    ]),
    html.Div(className="page", children=[
        card(className="filters", children=[
            html.Div([
                html.Div("Tipo de medalha · todos os gráficos", className="filter-label"),
                dcc.Checklist(id="medal-filter", options=medal_options, value=list(MEDAL_COLS),
                              className="pills"),
            ]),
            html.Div([
                html.Div("Países · compare vários (ou clique no mapa)", className="filter-label"),
                dcc.Dropdown(id="country-filter", options=country_options, value=[], multi=True,
                             placeholder="Todos os países", style={"width": "400px"}),
            ]),
            html.Div([
                html.Div("Edições · gráfico de barras", className="filter-label"),
                dcc.Dropdown(id="year-filter", options=year_options, value=[], multi=True,
                             placeholder="Todas as edições", style={"width": "400px"}),
            ]),
        ]),
        html.Div(id="kpis", className="kpis"),
        html.Div(className="row top", children=[
            card(dcc.Graph(id="map", config=MAP_CONFIG), html.Div(
                "Não exibidos no mapa (sem correspondência geográfica atual): "
                + ", ".join(missing_on_map) + ".", className="foot")),
            card(dcc.Graph(id="pie-chart", config=FIG_CONFIG)),
        ]),
        html.Div(className="row bottom", children=[
            card(dcc.Graph(id="area-chart", config=FIG_CONFIG)),
            card(dcc.Graph(id="bar-chart", config=FIG_CONFIG)),
        ]),
        html.Div("Fonte: Olympic Medals by Country (Kaggle) · Dash + Plotly Express", className="foot"),
    ]),
])


# ------------------------------------------------------------- callbacks ---
@app.callback(Output("country-filter", "value"), Input("map", "clickData"),
              State("country-filter", "value"), prevent_initial_call=True)
def toggle_country_from_map(click, current):
    """Clicar em um país do mapa o adiciona (ou remove) da seleção."""
    current = list(current or [])
    if click and click.get("points"):
        c = click["points"][0]["location"]
        current.remove(c) if c in current else current.append(c)
    return current


@app.callback(Output("kpis", "children"), Input("medal-filter", "value"),
              Input("country-filter", "value"))
def update_kpis(medals, countries):
    cols = sel_cols(medals)
    data = df[df["Country_Name"].isin(countries)] if countries else df
    scope = ", ".join(countries) if countries and len(countries) <= 2 else (
        f"{len(countries)} países" if countries else "Mundo")

    def kpi(label, value, color, active, note):
        return html.Div(className="kpi active" if active else "kpi", style={"--c": color}, children=[
            html.Div(label, className="k-label"),
            html.Div(fmt(value), className="k-value"),
            html.Div(note, className="k-note"),
        ])

    ranking = metric(df, cols).groupby(df["Country_Name"]).sum().sort_values(ascending=False)
    if not countries:
        lead = ("País líder", ranking.index[0], f"{fmt(ranking.iloc[0])} medalhas")
    elif len(countries) == 1:
        lead = ("Posição no ranking", f"{ranking.index.get_loc(countries[0]) + 1}º",
                f"de {len(ranking)} países")
    else:
        sub = ranking[ranking.index.isin(countries)]
        lead = ("Líder da seleção", sub.index[0], f"{fmt(sub.iloc[0])} medalhas")
    lead_el = html.Div(className="kpi", style={"--c": BLUE}, children=[
        html.Div(lead[0], className="k-label"),
        html.Div(lead[1], className="k-value",
                 style={"fontSize": "24px", "paddingTop": "6px"} if len(str(lead[1])) > 4 else {}),
        html.Div(lead[2], className="k-note")])
    return [
        kpi("Total · seleção", metric(data, cols).sum(), BLUE, True, scope),
        *[kpi(PT[c], data[c].sum(), MEDAL_COLOR[c], c in cols, scope) for c in MEDAL_COLS],
        lead_el,
    ]


@app.callback(Output("map", "figure"), Input("medal-filter", "value"),
              Input("country-filter", "value"))
def update_map(medals, countries):
    cols = sel_cols(medals)
    data = metric(df, cols).groupby(df["Country_Name"]).sum().rename("Medalhas").reset_index()
    data = data[~data["Country_Name"].isin(NOT_ON_MAP)].reset_index(drop=True)
    scale = MEDAL_SCALE[cols[0]] if len(cols) == 1 else "YlOrRd"
    fig = px.choropleth(data, locations="Country_Name", locationmode="country names",
                        color="Medalhas", color_continuous_scale=scale)
    fig.update_geos(
        projection_type="natural earth", showframe=False, showcoastlines=False,
        showcountries=True, countrycolor="white", showland=True, landcolor="#EDEBE9",
        showocean=False, bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 85],
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color="white",
                      hovertemplate="<b>%{location}</b><br>Medalhas: %{z}<extra></extra>")
    if countries:  # contorno azul nos países selecionados
        sel = [c for c in countries if c not in NOT_ON_MAP]
        fig.add_trace(go.Choropleth(
            locations=sel, locationmode="country names", z=[1] * len(sel), showscale=False,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker=dict(line=dict(color=INK, width=2.5)),
            hovertemplate="<b>%{location}</b><extra></extra>"))
    style(fig, f"Total de {medal_phrase(cols)} por país · clique para comparar", 440)
    fig.update_layout(
        margin=dict(l=0, r=0, t=48, b=0), dragmode=False, clickmode="event+select",
        coloraxis_colorbar=dict(thickness=10, len=0.6, title="", outlinewidth=0, x=0.99),
    )
    return fig


@app.callback(Output("area-chart", "figure"), Input("medal-filter", "value"),
              Input("country-filter", "value"))
def update_area(medals, countries):
    cols = sel_cols(medals)
    d = df.assign(_m=metric(df, cols))
    labels = {"_m": "Medalhas", "Year": "Ano", "Country_Name": "País"}
    if countries:  # comparação: linhas por país
        data = (d[d["Country_Name"].isin(countries)]
                .groupby(["Year", "Country_Name"])["_m"].sum().reset_index())
        fig = px.line(data, x="Year", y="_m", color="Country_Name", markers=True,
                      color_discrete_map=country_colors(countries), labels=labels)
        fig.update_traces(line_width=3, marker_size=8)
        title = f"Comparação ao longo das edições · {medal_phrase(cols)}"
    else:  # visão geral: top 10 empilhado
        top = d.groupby("Country_Name")["_m"].sum().nlargest(10).index
        data = (d[d["Country_Name"].isin(top)]
                .groupby(["Year", "Country_Name"])["_m"].sum().reset_index())
        fig = px.area(data, x="Year", y="_m", color="Country_Name",
                      category_orders={"Country_Name": list(top)},
                      color_discrete_map=country_colors(list(top)), labels=labels)
        fig.for_each_trace(lambda t: t.update(fillcolor=t.line.color,
                                              line=dict(color="white", width=1)))
        title = f"Evolução do Top 10 em {medal_phrase(cols)}"
    style(fig, title, 400)
    fig.update_xaxes(tickvals=sorted(df["Year"].unique()), showgrid=False, title=None)
    fig.update_yaxes(gridcolor=GRID, title=None)
    fig.update_layout(margin=dict(l=10, r=34, t=48, b=10),  # folga p/ o rótulo "2020"
                      legend=dict(orientation="h", y=-0.12, title=None, font_size=11))
    return fig


@app.callback(
    Output("bar-chart", "figure"),
    Input("medal-filter", "value"), Input("year-filter", "value"),
    Input("country-filter", "value"),
)
def update_bar(medals, years, countries):
    cols = sel_cols(medals)
    data = df[df["Year"].isin(years)] if years else df
    if countries:
        data = data[data["Country_Name"].isin(countries)]
    g = data.groupby("Country_Name")[cols].sum()
    g["Total"] = g[cols].sum(axis=1)
    g = g.reset_index().sort_values(["Total", "Country_Name"], ascending=[False, True]).head(10)
    g = g.iloc[::-1]
    long = g.melt(id_vars=["Country_Name", "Total"], value_vars=cols,
                  var_name="Tipo", value_name="Medalhas")
    long["Tipo"] = long["Tipo"].map(PT)
    fig = px.bar(long, x="Medalhas", y="Country_Name", color="Tipo", orientation="h",
                 color_discrete_map={PT[c]: MEDAL_COLOR[c] for c in MEDAL_COLS},
                 category_orders={"Tipo": [PT[c] for c in cols]},
                 labels={"Country_Name": "País"})
    fig.update_traces(marker_line=dict(color="white", width=1))
    fig.add_trace(go.Scatter(x=g["Total"], y=g["Country_Name"], mode="text",
                             text=g["Total"].astype(int), textposition="middle right",
                             textfont=dict(color=INK, size=12), showlegend=False,
                             hoverinfo="skip", cliponaxis=False))
    if not years:
        when = "1992–2020"
    elif len(years) <= 3:
        when = " · ".join(str(y) for y in sorted(years))
    else:
        when = f"{len(years)} edições"
    style(fig, f"{'Seleção' if countries else 'Top 10'} em {medal_phrase(cols)} · {when}", 400)
    n, m = len(g), max(len(g), 4)  # reserva espaço para poucas barras não ficarem gigantes
    fig.update_xaxes(visible=False)
    fig.update_yaxes(title=None, range=[n - m - 0.5, n - 0.5])
    fig.update_layout(bargap=0.35, margin=dict(l=10, r=40, t=48, b=10),
                      barmode="stack", showlegend=len(cols) > 1,
                      legend=dict(orientation="h", y=-0.05, title=None,
                                itemclick=False, itemdoubleclick=False))
    return fig


@app.callback(Output("pie-chart", "figure"), Input("medal-filter", "value"),
              Input("country-filter", "value"), Input("year-filter", "value"))
def update_pie(medals, countries, years=None):
    cols = sel_cols(medals)
    countries = countries or []
    base = df[df["Year"].isin(years)] if years else df
    scopes = countries if 2 <= len(countries) <= MAX_PIES else [None]
    n = len(scopes)
    ncols = 1 if n == 1 else 2
    nrows = math.ceil(n / ncols)
    fig = make_subplots(
        rows=nrows, cols=ncols, specs=[[{"type": "domain"}] * ncols] * nrows,
        subplot_titles=[f"<b>{c}</b>" for c in scopes] if n > 1 else None,
        vertical_spacing=0.14,
    )
    for a in fig.layout.annotations:  # títulos dos países, acima de cada rosca
        a.update(font=dict(size=13, color=INK))
    for i, c in enumerate(scopes):
        if c is None:
            data = base[base["Country_Name"].isin(countries)] if countries else base
        else:
            data = base[base["Country_Name"] == c]
        vals = data[MEDAL_COLS].sum()
        tot = vals.sum()
        fig.add_trace(go.Pie(
            labels=[PT[m] for m in MEDAL_COLS], values=vals.values,
            hole=0.58 if n == 1 else 0.5, sort=False,
            marker=dict(colors=[MEDAL_COLOR[m] for m in MEDAL_COLS], line=dict(color="white", width=2)),
            pull=[0.08 if m in cols and len(cols) < 3 else 0 for m in MEDAL_COLS],
            text=["" if v == 0 else f"{v / tot:.0%}" for v in vals.values], textinfo="text",
            textfont_size=12 if n == 1 else 11, showlegend=(i == 0),
            title=dict(
                text=(f"<b style='font-size:26px;color:{INK}'>{fmt(tot)}</b><br>medalhas" if n == 1
                      else f"<b style='font-size:17px;color:{INK}'>{fmt(tot)}</b>"),
                position="middle center", font=dict(size=11, color=MUTED)),
            hovertemplate="%{label}: %{value} medalhas (%{percent})<extra></extra>",
        ), row=i // ncols + 1, col=i % ncols + 1)
    if n == 1:
        scope = ", ".join(countries) if countries else "Mundo"
        if len(countries) > MAX_PIES:
            scope = f"{len(countries)} países somados"
        title = f"Composição das medalhas · {scope}"
    else:
        title = "Composição das medalhas · comparação"
    if years:
        title += " · " + (" · ".join(str(y) for y in sorted(years)) if len(years) <= 3
                          else f"{len(years)} edições")
    style(fig, title, 440)
    fig.update_layout(
                      margin=dict(l=10, r=10, t=48 if n == 1 else 76, b=10),
                      legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center", font_size=13,
                                itemclick=False, itemdoubleclick=False))
    return fig


if __name__ == "__main__":
    app.run(debug=True)
