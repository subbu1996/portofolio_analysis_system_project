import dash
from dash import Dash, html, dcc, _dash_renderer, Input, Output, clientside_callback
import dash_mantine_components as dmc
from dash_iconify import DashIconify

_dash_renderer._set_react_version("18.2.0")

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
server = app.server

def get_header_content():
    return dmc.Group(
        justify="flex-start",
        h="100%",
        px="md",
        gap="xl",
        children=[
            dmc.Group([
                DashIconify(icon="lucide:network", width=30, color="#1a73e8"),
                dmc.Text("Portofolio Analysis: Multi-Agentic System", size="xl", fw=700, c="#1a73e8")
            ]),
            
            dmc.Group([
                dmc.Anchor("Chat", href="/", id="nav-chat", underline=False, fw=500),
                dmc.Anchor("Dashboard", href="/dashboard", id="nav-dashboard", underline=False, fw=500),
                dmc.Anchor("Alerts", href="/alerts", id="nav-alerts", underline=False, fw=500),
            ], gap="lg")
        ]
    )

app.layout = dmc.MantineProvider(
    children=[
        dcc.Store(id="global-store", storage_type="session"),
        dcc.Location(id="url", refresh=False),
        
        dmc.AppShell(
            header={"height": 60},
            padding=0,
            children=[
                dmc.AppShellHeader(children=get_header_content(), zIndex=101),
                dmc.AppShellMain(
                    children=dash.page_container,
                    style={"height": "100vh", "backgroundColor": "#fff", "display": "flex", "flexDirection": "column"}
                )
            ]
        )
    ]
)

# --- Client-Side Callback for Navbar Highlighting ---
clientside_callback(
    """
    function(pathname) {
        // Defines the order of links matching the Output list below
        const targetPaths = ["/", "/dashboard", "/alerts"];
        
        // Styles
        const inactiveStyle = { 
            color: "#5f6368", 
            fontWeight: "500", 
            borderBottom: "3px solid transparent", 
            paddingBottom: "2px",
            transition: "color 0.2s"
        };
        const activeStyle = { 
            color: "#1a73e8", 
            fontWeight: "700", 
            borderBottom: "3px solid #1a73e8", 
            paddingBottom: "2px",
            transition: "color 0.2s"
        };
        
        
        let cleanPath = pathname;
        if (cleanPath && cleanPath.length > 1 && cleanPath.endsWith('/')) {
            cleanPath = cleanPath.slice(0, -1);
        }
      
        return targetPaths.map(target => {
            return (cleanPath === target) ? activeStyle : inactiveStyle;
        });
    }
    """,
    [Output("nav-chat", "style"), 
     Output("nav-dashboard", "style"), 
     Output("nav-alerts", "style")],
    Input("url", "pathname")
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)