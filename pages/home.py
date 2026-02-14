import dash
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update, clientside_callback
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime, timezone, timedelta
from ui_utils.db import (create_session, get_all_sessions, get_messages, 
                      add_message, delete_session, update_session_title)
from ui_utils.llm import generate_response

dash.register_page(__name__, path='/', title='Chat')

from pages.home_callbacks import *

# --- Layout ---

layout = dmc.Group([
    dcc.Store(id="current-session-store", storage_type="session"),
    dcc.Store(id="sidebar-state-store", data=False),
    
    # Rename Modal
    dmc.Modal(
        title="Rename Chat",
        id="rename-modal",
        zIndex=2000,
        opened=False,
        children=[
            dmc.TextInput(id="rename-input", placeholder="Enter new title", mb="md"),
            dmc.Group([
                dmc.Button("Cancel", id="rename-cancel", variant="outline", color="gray"),
                dmc.Button("Save", id="rename-save", color="blue"),
            ], justify="end"),
            dcc.Store(id="rename-target-id") 
        ]
    ),
    
    # Sidebar
    dmc.Stack(
        id="sidebar-panel",
        className="sidebar-transition",
        w=300, 
        h="100%",
        p="md",
        style={"borderRight": "1px solid #e9ecef", "backgroundColor": "#fff"},
        children=[
            # Header (History Text Removed)
            dmc.Group(
                justify="end", # Align burger to the right
                mb="md",
                children=[
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:menu-2"), 
                        id="sidebar-toggle-btn", 
                        variant="subtle", 
                        color="gray",
                        size="lg"
                    )
                ]
            ),
            
            # New Chat Button Container
            # Initial State: Full Button using Pattern ID 'main'
            html.Div(
                id="new-chat-container", 
                style={"marginBottom": "10px"},
                children=[
                    dmc.Button(
                        "New Chat", 
                        id={"type": "new-chat-btn", "index": "main"}, 
                        leftSection=DashIconify(icon="tabler:plus"), 
                        fullWidth=True, 
                        variant="outline", 
                        size="md"
                    )
                ]
            ),
            
            # History List
            dmc.ScrollArea(
                id="chat-history-list",
                flex=1,
                type="hover",
                offsetScrollbars=True,
                style={"overflowX": "hidden"}
            )
        ]
    ),

    # Main Chat Area
    dmc.Stack([
        dmc.ScrollArea(
            id="chat-window",
            flex=1,
            p="xl",
            children=[],
            type="auto",
            classNames={"viewport": "chat-viewport"},
        ),
        
        dmc.Container(
            fluid=True,
            p="md",
            children=[
                dmc.Group([
                    dmc.Textarea(
                        id="user-input",
                        placeholder="Type a message...",
                        autosize=True,
                        minRows=1,
                        maxRows=4,
                        w=600,
                        style={"flex": 1},
                    ),
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:send", width=20),
                        id="send-btn",
                        variant="filled",
                        color="blue",
                        size="lg",
                        radius="xl",
                        n_clicks=0
                    )
                ], align="end")
            ],
            style={"borderTop": "1px solid #e9ecef", "backgroundColor": "#fff"}
        )
    ], h="100%", style={"flex": 1}, gap=0)
    
], h="calc(100vh - 60px)", gap=0, align="stretch", style={"overflow": "hidden"})

