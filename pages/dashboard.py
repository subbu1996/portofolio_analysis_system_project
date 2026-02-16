import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json

# Import utils
from src.utils.mock_data import generate_historical_data
from src.utils.analytics import process_portfolio_data, get_asset_allocation

dash.register_page(__name__, title='Analytics')

# --- INITIAL DATA LOAD ---
# Load static data once
try:
    with open("data/portfolio.json", 'r') as f:
        PORTFOLIO_RAW = json.load(f)
except:
    PORTFOLIO_RAW = {"holdings": [], "transactions": []}

# Generate History
HISTORICAL_DF = generate_historical_data("data/portfolio.json")
ALL_SYMBOLS = list(HISTORICAL_DF.columns.drop("NIFTY_50"))

# --- LAYOUT COMPONENTS ---

def get_kpi_card(title, value, sub_value=None, color="blue", icon="mdi:finance"):
    return dmc.Paper(
        withBorder=True, shadow="sm", p="md", radius="md",
        children=[
            dmc.Group(justify="space-between", children=[
                dmc.Text(title, size="xs", c="dimmed", fw=700, tt="uppercase"),
                DashIconify(icon=icon, width=20, color=dmc.DEFAULT_THEME["colors"][color][6])
            ]),
            dmc.Stack(gap=0, mt="sm", children=[
                dmc.Text(value, size="xl", fw=700),
                dmc.Text(sub_value, size="sm", c=color, fw=500) if sub_value else None
            ])
        ]
    )

layout = dmc.Container(fluid=True, p="lg", children=[
    
    # Header & Filter
    dmc.Grid(align="center", mb="xl", children=[
        dmc.GridCol(span=6, children=[
            dmc.Title("Portfolio Analytics", order=2),
            dmc.Text("Deep dive into your investment performance", c="dimmed", size="sm")
        ]),
        dmc.GridCol(span=6, children=[
            dcc.Dropdown(
                id="holdings-filter",
                options=[{'label': 'All Holdings', 'value': 'ALL'}] + 
                        [{'label': s, 'value': s} for s in ALL_SYMBOLS],
                value=['ALL'], # Default to ALL
                multi=True,
                placeholder="Select Holdings to Analyze",
                style={"width": "100%"}
            )
        ])
    ]),

    # Loading Overlay for the whole dashboard content
    dcc.Loading(overlay_style={"visibility":"visible", "opacity": .5, "backgroundColor": "white"}, children=[
        
        # 1. KPI Row
        dmc.Grid(gutter="md", mb="lg", children=[
            dmc.GridCol(span=3, children=html.Div(id="kpi-net-worth")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-total-profit")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-xirr")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-sharpe")), # Replaced Daily P&L with Sharpe
        ]),

        # 2. Main Performance Charts
        dmc.Grid(gutter="md", mb="lg", children=[
            # Left: Time Series Analysis (Tabs)
            dmc.GridCol(span=8, children=[
                dmc.Paper(withBorder=True, shadow="sm", p="sm", radius="md", children=[
                    dmc.Tabs(value="profit", children=[
                        dmc.TabsList([
                            dmc.TabsTab("Profit % vs Benchmark", value="profit", leftSection=DashIconify(icon="mdi:chart-line")),
                            dmc.TabsTab("Net Worth Growth", value="growth", leftSection=DashIconify(icon="mdi:chart-area")),
                            dmc.TabsTab("Drawdown (Risk)", value="drawdown", leftSection=DashIconify(icon="mdi:arrow-down-bold-circle-outline")),
                        ]),
                        dmc.TabsPanel(dcc.Graph(id="chart-profit-comparison", style={"height": "400px"}), value="profit"),
                        dmc.TabsPanel(dcc.Graph(id="chart-net-worth", style={"height": "400px"}), value="growth"),
                        dmc.TabsPanel(dcc.Graph(id="chart-drawdown", style={"height": "400px"}), value="drawdown"),
                    ])
                ])
            ]),
            
            # Right: Sector & Risk
            dmc.GridCol(span=4, children=[
                dmc.Stack(children=[
                    dmc.Paper(withBorder=True, shadow="sm", p="md", radius="md", children=[
                        dmc.Text("Sector Allocation", fw=600, mb="sm"),
                        dcc.Graph(id="chart-sector", style={"height": "200px"}, config={"displayModeBar": False})
                    ]),
                    dmc.Paper(withBorder=True, shadow="sm", p="md", radius="md", children=[
                        dmc.Text("Risk vs Return Analysis", fw=600, mb="sm"),
                        dcc.Graph(id="chart-risk-return", style={"height": "200px"}, config={"displayModeBar": False})
                    ])
                ])
            ])
        ]),

    ]) # End Loading
])

# --- CALLBACKS ---

@callback(
    [Output("kpi-net-worth", "children"),
     Output("kpi-total-profit", "children"),
     Output("kpi-xirr", "children"),
     Output("kpi-sharpe", "children"),
     Output("chart-profit-comparison", "figure"),
     Output("chart-net-worth", "figure"),
     Output("chart-drawdown", "figure"),
     Output("chart-sector", "figure"),
     Output("chart-risk-return", "figure")],
    [Input("holdings-filter", "value")]
)
def update_dashboard(selected_values):
    # Handle "ALL" selection logic
    if not selected_values or 'ALL' in selected_values:
        selection = 'ALL' # Pass special flag
        display_selection = ALL_SYMBOLS
    else:
        selection = selected_values
        display_selection = selected_values

    # 1. Process Data
    analytics = process_portfolio_data(PORTFOLIO_RAW, HISTORICAL_DF, selection)
    
    if not analytics:
        return [dmc.Alert("No data available for selection", color="red")] * 9

    metrics = analytics['metrics']
    
    # 2. Generate KPIs
    kpi1 = get_kpi_card("Current Value", f"₹{metrics['current_value']:,.0f}", f"Invested: ₹{metrics['total_invested']:,.0f}")
    kpi2 = get_kpi_card("Total Returns", f"₹{metrics['absolute_profit']:,.0f}", f"{metrics['absolute_return_pct']:+.2f}%", color="green" if metrics['absolute_profit'] > 0 else "red")
    kpi3 = get_kpi_card("XIRR", f"{metrics['xirr']*100:.2f}%", "Annualized Return", color="teal")
    kpi4 = get_kpi_card("Risk (Sharpe)", f"{metrics['sharpe']:.2f}", f"Beta: {metrics['beta']:.2f}", color="orange", icon="mdi:shield-alert-outline")

    # 3. Generate Charts
    
    # Chart A: Profit % Comparison
    fig_profit = go.Figure()
    fig_profit.add_trace(go.Scatter(x=analytics['dates'], y=analytics['portfolio_profit_pct'], name="My Portfolio", line=dict(color="#1a73e8", width=2)))
    fig_profit.add_trace(go.Scatter(x=analytics['dates'], y=analytics['benchmark_profit_pct'], name="Nifty 50 Equivalent", line=dict(color="#9aa0a6", dash="dot")))
    fig_profit.update_layout(title="", yaxis_title="Total Profit %", template="plotly_white", hovermode="x unified", margin=dict(t=10, l=10, r=10, b=10))

    # Chart B: Net Worth Area
    fig_growth = go.Figure()
    fig_growth.add_trace(go.Scatter(x=analytics['dates'], y=analytics['portfolio_value'], name="Current Value", fill='tozeroy', line=dict(color="#1a73e8")))
    fig_growth.add_trace(go.Scatter(x=analytics['dates'], y=analytics['invested'], name="Invested Amount", line=dict(color="#e37400", dash="dash")))
    fig_growth.update_layout(yaxis_title="Value (₹)", template="plotly_white", hovermode="x unified", margin=dict(t=10, l=10, r=10, b=10))

    # Chart C: Drawdown
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=analytics['dates'], y=analytics['drawdown'], fill='tozeroy', line=dict(color="#d93025"), name="Drawdown"))
    fig_dd.update_layout(yaxis_title="Drawdown %", template="plotly_white", margin=dict(t=10, l=10, r=10, b=10))

    # Chart D: Sector Allocation
    alloc_df = get_asset_allocation(PORTFOLIO_RAW['holdings'], HISTORICAL_DF.iloc[-1].to_dict(), selection)
    if not alloc_df.empty:
        fig_sector = px.pie(alloc_df, values='value', names='sector', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
        fig_sector.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
        fig_sector.update_traces(textposition='inside', textinfo='label+percent')
        
        # Chart E: Risk vs Return (Scatter)
        # We need mock risk data for individual dots since we calculated portfolio aggregate earlier
        # Using return from alloc_df and randomized beta for visual demo
        fig_risk = px.scatter(alloc_df, x="return", y="value", size="value", color="sector", hover_name="symbol",
                             labels={"return": "Total Return %", "value": "Current Value"})
        fig_risk.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False, xaxis_title="Return %")
    else:
        fig_sector = go.Figure()
        fig_risk = go.Figure()

    return kpi1, kpi2, kpi3, kpi4, fig_profit, fig_growth, fig_dd, fig_sector, fig_risk