import dash
from dash import html, dcc, callback, Input, Output, dash_table
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json

# Import utils
from src.utils.mock_data import generate_historical_data
from src.utils.analytics import process_portfolio_data

dash.register_page(__name__, title='Analytics')

# --- INITIAL DATA LOAD ---
try:
    with open("data/portfolio.json", 'r') as f:
        PORTFOLIO_RAW = json.load(f)
except Exception as e:
    print(f"Error loading portfolio: {e}")
    PORTFOLIO_RAW = {"holdings": [], "transactions": []}

# Generate History
# HISTORICAL_DF = generate_historical_data("data/portfolio.json")
HISTORICAL_DF = pd.read_parquet("data/historical_data.parquet")
# Ensure we have a list of symbols
ALL_SYMBOLS = list(HISTORICAL_DF.columns.drop("NIFTY_50", errors='ignore'))

# --- HELPER FUNCTIONS ---

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

def prepare_holdings_data(portfolio, historical_df, selected_symbols):
    """
    Prepare detailed row-level data for the table and advanced charts.
    """
    if historical_df.empty:
        return pd.DataFrame()

    current_prices = historical_df.iloc[-1].to_dict()
    data = []
    
    for h in portfolio.get('holdings', []):
        symbol = h['symbol']
        
        # Filter logic
        if selected_symbols != 'ALL' and symbol not in selected_symbols:
            continue
            
        # Safe price retrieval
        current_price = current_prices.get(symbol, h.get('avg_price', 0))
        quantity = h.get('quantity', 0)
        
        invested = quantity * h.get('avg_price', 0)
        current_val = quantity * current_price
        
        pnl = current_val - invested
        # Avoid division by zero
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0
        
        data.append({
            "Symbol": symbol,
            "Asset Type": h.get('asset_type', 'Unknown').replace('_', ' ').title(),
            "Sector": h.get('sector', 'Other'),
            "Quantity": quantity,
            "Avg Price": round(h.get('avg_price', 0), 2),
            "Current Price": round(current_price, 2),
            "Invested Amount": round(invested, 2),
            "Current Value": round(current_val, 2),
            "P&L": round(pnl, 2),
            "Net Change %": round(pnl_pct, 2)
        })
    
    return pd.DataFrame(data)

# --- LAYOUT COMPONENTS ---

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

    # Loading Overlay
    dcc.Loading(overlay_style={"visibility":"visible", "opacity": .5, "backgroundColor": "white"}, children=[
        
        # 1. KPI Row
        dmc.Grid(gutter="md", mb="lg", children=[
            dmc.GridCol(span=3, children=html.Div(id="kpi-net-worth")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-total-profit")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-xirr")),
            dmc.GridCol(span=3, children=html.Div(id="kpi-sharpe")),
        ]),

        # 2. Main Analytics Section
        dmc.Grid(gutter="md", mb="lg", children=[
            # Left: Time Series Analysis (Tabs)
            dmc.GridCol(span=8, children=[
                dmc.Paper(withBorder=True, shadow="sm", p="sm", radius="md", style={"height": "100%"}, children=[
                    dmc.Tabs(value="profit", children=[
                        dmc.TabsList([
                            dmc.TabsTab("Profit % vs Benchmark", value="profit", leftSection=DashIconify(icon="mdi:chart-line")),
                            dmc.TabsTab("Net Worth Growth", value="growth", leftSection=DashIconify(icon="mdi:chart-area")),
                            dmc.TabsTab("Drawdown (Risk)", value="drawdown", leftSection=DashIconify(icon="mdi:arrow-down-bold-circle-outline")),
                        ]),
                        dmc.TabsPanel(dcc.Graph(id="chart-profit-comparison", style={"height": "450px"}), value="profit"),
                        dmc.TabsPanel(dcc.Graph(id="chart-net-worth", style={"height": "450px"}), value="growth"),
                        dmc.TabsPanel(dcc.Graph(id="chart-drawdown", style={"height": "450px"}), value="drawdown"),
                    ])
                ])
            ]),
            
            # Right: Advanced Composition & Movers
            dmc.GridCol(span=4, children=[
                dmc.Stack(children=[
                    # Allocation Sunburst
                    dmc.Paper(withBorder=True, shadow="sm", p="md", radius="md", children=[
                        dmc.Text("Portfolio Composition", fw=600, mb="xs"),
                        dcc.Graph(id="chart-sunburst", style={"height": "250px"}, config={"displayModeBar": False})
                    ]),
                    # Top Movers Bar Chart
                    dmc.Paper(withBorder=True, shadow="sm", p="md", radius="md", children=[
                        dmc.Text("Top Movers (Net Change %)", fw=600, mb="xs"),
                        dcc.Graph(id="chart-movers", style={"height": "200px"}, config={"displayModeBar": False})
                    ])
                ])
            ])
        ]),

        # 3. Detailed Holdings Table
        dmc.Paper(withBorder=True, shadow="sm", p="md", radius="md", mb="xl", children=[
            dmc.Group(justify="space-between", mb="md", children=[
                dmc.Text("Holdings Breakdown", fw=600, size="lg"),
                dmc.Badge("Interactive Table", color="blue", variant="light")
            ]),
            html.Div(id="holdings-table-container")
        ])

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
     Output("chart-sunburst", "figure"),
     Output("chart-movers", "figure"),
     Output("holdings-table-container", "children")],
    [Input("holdings-filter", "value")]
)
def update_dashboard(selected_values):
    # Handle "ALL" selection logic
    if not selected_values or 'ALL' in selected_values:
        selection_flag = 'ALL'
    else:
        selection_flag = selected_values

    # 1. Process Time-Series Data (Existing Logic)
    analytics = process_portfolio_data(PORTFOLIO_RAW, HISTORICAL_DF, selection_flag)
    
    # 2. Process Holdings Data (New Logic for Table/Charts)
    holdings_df = prepare_holdings_data(PORTFOLIO_RAW, HISTORICAL_DF, selection_flag)

    if not analytics or holdings_df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False}, annotations=[
            {"text": "No Data Available", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 20}}
        ])
        return [dmc.Alert("No data available for selection", color="red")] * 4 + [empty_fig] * 5 + [html.Div("No Data")]

    metrics = analytics['metrics']
    
    # --- GENERATE KPIs ---
    kpi1 = get_kpi_card("Current Value", f"₹{metrics['current_value']:,.0f}", f"Invested: ₹{metrics['total_invested']:,.0f}")
    kpi2 = get_kpi_card("Total Returns", f"₹{metrics['absolute_profit']:,.0f}", f"{metrics['absolute_return_pct']:+.2f}%", color="green" if metrics['absolute_profit'] > 0 else "red")
    kpi3 = get_kpi_card("XIRR", f"{metrics['xirr']*100:.2f}%", "Annualized Return", color="teal")
    kpi4 = get_kpi_card("Risk (Sharpe)", f"{metrics['sharpe']:.2f}", f"Beta: {metrics['beta']:.2f}", color="orange", icon="mdi:shield-alert-outline")

    # --- GENERATE CHARTS ---
    
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

    # Chart D: Sunburst (Asset Allocation)
    # WARNING FIX: Filter out assets with <= 0 value to prevent Plotly errors
    sunburst_df = holdings_df[holdings_df['Current Value'] > 0].copy()
    
    if not sunburst_df.empty:
        fig_sunburst = px.sunburst(
            sunburst_df, 
            path=['Asset Type', 'Sector', 'Symbol'], 
            values='Current Value',
            color='Net Change %',
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0
        )
        fig_sunburst.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        fig_sunburst.update_traces(textinfo="label+percent entry")
    else:
        fig_sunburst = go.Figure()
        fig_sunburst.update_layout(annotations=[{"text": "No Positive Assets", "showarrow": False, "xref": "paper", "yref": "paper"}])

    # Chart E: Top/Bottom Movers
    sorted_df = holdings_df.sort_values(by="Net Change %", ascending=True)
    if len(sorted_df) > 10:
        movers_df = pd.concat([sorted_df.head(3), sorted_df.tail(3)])
    else:
        movers_df = sorted_df
    
    if not movers_df.empty:
        fig_movers = px.bar(
            movers_df, 
            x="Net Change %", 
            y="Symbol", 
            orientation='h',
            color="Net Change %",
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0,
            text="Net Change %"
        )
        fig_movers.update_layout(
            margin=dict(t=0, b=0, l=0, r=0), 
            xaxis_title=None, 
            yaxis_title=None,
            showlegend=False,
            coloraxis_showscale=False
        )
        fig_movers.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    else:
        fig_movers = go.Figure()

    # --- GENERATE TABLE ---
    # Safe Conditional Formatting Syntax for Dash Table
    style_data_conditional = [
        {
            'if': {'filter_query': '{Net Change %} > 0', 'column_id': 'Net Change %'},
            'color': 'green', 'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{Net Change %} < 0', 'column_id': 'Net Change %'},
            'color': 'red', 'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{P&L} > 0', 'column_id': 'P&L'},
            'color': 'green'
        },
        {
            'if': {'filter_query': '{P&L} < 0', 'column_id': 'P&L'},
            'color': 'red'
        }
    ]

    table = dash_table.DataTable(
        data=holdings_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in holdings_df.columns],
        sort_action="native",
        filter_action="native",
        style_as_list_view=True,
        style_cell={'padding': '10px', 'textAlign': 'left', 'fontFamily': 'sans-serif'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        style_data_conditional=style_data_conditional,
        page_size=10
    )

    return kpi1, kpi2, kpi3, kpi4, fig_profit, fig_growth, fig_dd, fig_sunburst, fig_movers, table