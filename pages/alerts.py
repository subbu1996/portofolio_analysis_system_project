import dash
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify

dash.register_page(__name__, title='Alerts')

layout = dmc.Center(
    style={"height": "100%"},
    children=[
        dmc.Stack(
            align="center",
            children=[
                DashIconify(icon="mingcute:alert-line", width=80, color="#adb5bd"),
                dmc.Text("System Alerts", size="xl", fw=500),
                dmc.Badge("Feature Coming Soon", color="red", variant="light", size="lg")
            ]
        )
    ]
)