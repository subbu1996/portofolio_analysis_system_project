from dash import callback, Input, Output, State, ALL, ctx, no_update, clientside_callback
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime, timezone, timedelta
from ui_utils.db import (create_session, get_all_sessions, get_messages, 
                      add_message, delete_session, update_session_title)
from ui_utils.llm import (
    start_streaming_response, 
    get_streaming_state, 
    clear_streaming_state,
    stop_streaming
)


# --- Helpers ---

def convert_to_ist(timestamp_str):
    if not timestamp_str: return ""
    try:
        utc_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        utc_time = utc_time.replace(tzinfo=timezone.utc)
        ist_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist_time.strftime("%d %b %Y, %I:%M %p")
    except:
        return timestamp_str

def render_message_bubble(msg, is_loading=False):
    """
    Renders a chat message bubble.
    Args:
        msg: The message dictionary.
        is_loading: Boolean, true if this is the active message currently generating.
    """
    is_user = msg["role"] == "user"
    timestamp_ist = convert_to_ist(msg["timestamp"])
    
    avatar = dmc.Avatar(
        radius="xl", 
        color="blue" if is_user else "grape",
        children="U" if is_user else "AI"
    )

    content_children = [dmc.Text(msg["content"], style={"whiteSpace": "pre-wrap"})]
    
    # Render Thinking Process Accordion if data exists OR if it's currently loading
    # (We want to show the 'Thinking...' header even if the text buffer is briefly empty during start)
    has_thinking = "thinking_process" in msg and msg["thinking_process"]
    
    if not is_user and (has_thinking or is_loading):
        # Determine Header Content based on Loading State
        if is_loading:
            # Active Loading State: Loader + "Thinking..."
            header_content = dmc.Group([
                dmc.Loader(size="xs", type="dots"),
                dmc.Text("Thinking...", size="sm", c="dimmed")
            ], gap="xs")
        else:
            # Static History State: Brain Icon + "Thinking Process"
            header_content = dmc.Group([
                DashIconify(icon="tabler:brain", color="gray"),
                dmc.Text("Thinking Process", size="sm", c="dimmed")
            ], gap="xs")

        thinking_text = msg.get("thinking_process", "Initializing...") if msg.get("thinking_process") else "Initializing..."
        
        # We use the message ID so Dash knows it's the same accordion across updates
        msg_id = msg.get("id", "temp")
        accordion_id = f"thinking-acc-{msg_id}"

        # Insert Accordion at the TOP of the content list
        content_children.insert(0, dmc.Accordion(
            id=accordion_id, 
            children=[
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            header_content,
                            h=40
                        ),
                        dmc.AccordionPanel(
                            dmc.Code(thinking_text, block=True, c="dimmed", style={"fontSize": "0.85em"})
                        )
                    ],
                    value="thinking"
                )
            ],
            variant="separated",
            radius="md",
            mb="xs",
            # This ensures if user closes it, it STAYS closed even if we re-render
            value="thinking" if is_loading else None,
            persistence=True, 
            persistence_type="memory",
            styles={"item": {"border": "1px solid #eee", "backgroundColor": "#fcfcfc"}}
        ))

    content_children.append(
        dmc.Text(timestamp_ist, size="xs", c="dimmed", mt=5, style={"textAlign": "right"})
    )

    return dmc.Group(
        [
            avatar if not is_user else None,
            dmc.Paper(
                children=content_children,
                p="md",
                radius="lg",
                withBorder=True,
                shadow="sm",
                style={
                    "maxWidth": "70%", 
                    "backgroundColor": "#fff" if not is_user else "#e7f5ff",
                    "borderColor": "#dee2e6" if not is_user else "#a5d8ff"
                }
            ),
            avatar if is_user else None,
        ],
        justify="end" if is_user else "start",
        align="start",
        mb="md",
        w="100%"
    )

def render_history_item(session, active_id, collapsed=False):
   
    is_active = str(session["session_id"]) == str(active_id) if active_id else False
    
    # 1. Collapsed View
    if collapsed:
        return dmc.Tooltip(
            label=session["title"],
            position="right",
            children=dmc.ActionIcon(
                DashIconify(icon="bx:message-square-detail"),
                size="lg",
                variant="filled" if is_active else "subtle",
                color="blue" if is_active else "gray",
                mb=10,
                id={"type": "history-item", "index": session["session_id"]},
                n_clicks=0
            )
        )

    # 2. Expanded View
    return dmc.Group([
        dmc.NavLink(
            label=session["title"] or "Untitled Chat",
            description=convert_to_ist(session["timestamp"]),
            leftSection=DashIconify(icon="bx:message-square-detail"),
            active=is_active,
            variant="filled" if is_active else "light",
            color="blue",
            id={"type": "history-item", "index": session["session_id"]},
            n_clicks=0,
            style={"flex": 1, "borderRadius": "8px"}
        ),
        dmc.Menu([
            dmc.MenuTarget(
                dmc.ActionIcon(
                    DashIconify(icon="tabler:dots-vertical"),
                    variant="subtle", color="gray", size="sm"
                )
            ),
            dmc.MenuDropdown([
                dmc.MenuItem(
                    "Rename", 
                    leftSection=DashIconify(icon="tabler:pencil"),
                    id={"type": "rename-init-btn", "index": session["session_id"]},
                    n_clicks=0
                ),
                dmc.MenuItem(
                    "Delete", 
                    leftSection=DashIconify(icon="tabler:trash"),
                    color="red",
                    id={"type": "delete-chat-btn", "index": session["session_id"]},
                    n_clicks=0
                )
            ])
        ])
    ], gap="xs", wrap="nowrap", mb=5)


# --- Callbacks ---

# 1. Sidebar Toggle Logic
@callback(
    [Output("sidebar-panel", "w"),
     Output("sidebar-panel", "align"),
     Output("sidebar-state-store", "data")],
    Input("sidebar-toggle-btn", "n_clicks"),
    State("sidebar-state-store", "data"),
    prevent_initial_call=True
)
def toggle_sidebar(n, is_collapsed):
    new_state = not is_collapsed
    width = 80 if new_state else 300
    align = "center" if new_state else "stretch"
    return width, align, new_state


# 2. Main Logic (Handles Session, New Chat, & Expansion)
@callback(
    [Output("current-session-store", "data"),
     Output("chat-history-list", "children"),
     Output("new-chat-container", "children")],
    [Input({"type": "new-chat-btn", "index": ALL}, "n_clicks"),
     Input({"type": "history-item", "index": ALL}, "n_clicks"),
     Input({"type": "delete-chat-btn", "index": ALL}, "n_clicks"),
     Input("rename-save", "n_clicks"),
     Input("sidebar-state-store", "data")],
    [State("current-session-store", "data")]
)
def manage_session_state(new_chat_clicks, history_clicks, delete_clicks, 
                         rename_save, is_collapsed, current_session_id):
    trigger = ctx.triggered_id
    
    # Handle Deletion
    if isinstance(trigger, dict) and trigger["type"] == "delete-chat-btn":
        sess_to_delete = trigger["index"]
        delete_session(sess_to_delete)
        if str(sess_to_delete) == str(current_session_id):
            current_session_id = None
            
    # Handle Switching
    elif isinstance(trigger, dict) and trigger["type"] == "history-item":
        current_session_id = trigger["index"]

    # Handle New Chat
    elif isinstance(trigger, dict) and trigger["type"] == "new-chat-btn":
        if any(c > 0 for c in new_chat_clicks if c is not None):
            current_session_id = create_session("New Chat")

    # Load Sessions
    sessions = get_all_sessions()
    if not current_session_id:
        if sessions:
            current_session_id = sessions[0]['session_id']
        else:
            current_session_id = create_session("New Chat")
            sessions = get_all_sessions()
    
    # Render New Chat Button
    if is_collapsed:
        new_chat_btn = dmc.Tooltip(
            label="New Chat",
            position="right",
            children=dmc.ActionIcon(
                DashIconify(icon="tabler:plus"), 
                id={"type": "new-chat-btn", "index": "sidebar"}, 
                size="lg", 
                variant="outline",
                color="blue",
                radius="xl"
            )
        )
    else:
        new_chat_btn = dmc.Button(
            "New Chat", 
            id={"type": "new-chat-btn", "index": "main"}, 
            leftSection=DashIconify(icon="tabler:plus"), 
            fullWidth=True, 
            variant="outline", 
            size="md"
        )

    # Render History List
    history_list = [render_history_item(s, current_session_id, is_collapsed) for s in sessions]
    
    return current_session_id, history_list, new_chat_btn


# 3. Rename Logic
@callback(
    [Output("rename-modal", "opened"),
     Output("rename-target-id", "data"),
     Output("rename-input", "value")],
    [Input({"type": "rename-init-btn", "index": ALL}, "n_clicks"),
     Input("rename-cancel", "n_clicks"),
     Input("rename-save", "n_clicks")],
    [State("rename-input", "value"),
     State("rename-target-id", "data")],
    prevent_initial_call=True
)
def handle_rename_modal(init_clicks, cancel, save, new_title, target_id):
    trigger = ctx.triggered_id
    
    if isinstance(trigger, dict) and trigger["type"] == "rename-init-btn":
        if not any(init_clicks): return no_update, no_update, no_update
        return True, trigger["index"], "" 
    
    if trigger == "rename-save":
        if target_id and new_title:
            update_session_title(target_id, new_title)
        return False, None, ""
        
    if trigger == "rename-cancel":
        return False, None, ""

    return no_update, no_update, no_update


# 4. Message Sending
@callback(
    [Output("user-input", "value"),
     Output("message-trigger", "data")],
    Input("send-btn", "n_clicks"),
    [State("user-input", "value"),
     State("current-session-store", "data")],
    prevent_initial_call=True
)
def handle_message_submission(n_clicks, text, session_id):
    if not session_id:
        return no_update, no_update
    
    session_id = str(session_id)
    
    # Check if currently streaming
    streaming_state = get_streaming_state(session_id)
    
    if streaming_state and streaming_state.status == "processing":
        # Stop button was clicked
        stop_streaming(session_id)
        return no_update, {"action": "stopped", "timestamp": datetime.now().isoformat()}
    
    # Send button was clicked
    if not text or not text.strip():
        return no_update, no_update
    
    add_message(session_id, "user", text.strip())
    start_streaming_response(text.strip(), session_id)
    
    # Clear input and trigger chat display update
    return "", {"action": "sent", "timestamp": datetime.now().isoformat()}


@callback(
    [Output("chat-window", "children"),
     Output("update-interval", "disabled"),
     Output("send-btn", "children"),
     Output("send-btn", "color"),
     Output("send-btn", "id")],
    [Input("current-session-store", "data"),
     Input("message-trigger", "data"),  
     Input("update-interval", "n_intervals")],
    prevent_initial_call=False
)
def update_chat_display(session_id, message_trigger, n_intervals):
    if not session_id:
        return [], True, DashIconify(icon="tabler:send", width=20), "blue", "send-btn"
    
    session_id = str(session_id)
    
    # Check streaming state
    streaming_state = get_streaming_state(session_id)
    is_streaming = streaming_state and streaming_state.status == "processing"
    
    # Load ALL messages
    messages = get_messages(session_id)
    
    chat_content = []
    for i, m in enumerate(messages):
        # Determine if this message is the one currently streaming
        # It must be the last message AND we must be in streaming state AND it must be an AI message
        is_generating = is_streaming and (i == len(messages) - 1) and (m["role"] == "assistant")
        chat_content.append(render_message_bubble(m, is_loading=is_generating))
    
    if is_streaming:
        interval_disabled = False  # Keep polling
        
        # STOP Button Configuration
        btn_icon = DashIconify(icon="tabler:player-stop-filled", width=20)
        btn_color = "red"
    else:
        interval_disabled = True   # Stop polling
        
        # SEND Button Configuration
        btn_icon = DashIconify(icon="tabler:send", width=20)
        btn_color = "blue"

    # Clean up completed streams
    if streaming_state and streaming_state.status in ["complete", "error", "stopped"]:
        clear_streaming_state(session_id)
    
    return chat_content, interval_disabled, btn_icon, btn_color, "send-btn"


# Auto-Scroll & Enter Key
clientside_callback(
    """
    function(children) {
        var viewport = document.querySelector(".chat-viewport");
        if (viewport) {
            // Calculate distance from bottom
            // scrollHeight (total content) - scrollTop (current position) - clientHeight (visible area)
            var distanceToBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
            
            // Only auto-scroll if the user is already near the bottom (within 150px)
            // This prevents "fighting" the user if they scroll up to read history
            if (distanceToBottom < 150) {
                setTimeout(function() {
                    viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
                }, 100);
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("chat-window", "style"),
    Input("chat-window", "children")
)

clientside_callback(
    """
    function(value, n_intervals) {
        const textarea = document.getElementById('user-input');
        if (!textarea) return window.dash_clientside.no_update;
        
        if (!textarea.hasAttribute('data-listener-added')) {
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    const sendBtn = document.getElementById('send-btn');
                    if (sendBtn) sendBtn.click();
                }
            });
            textarea.setAttribute('data-listener-added', 'true');
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("user-input", "style"),
    Input("user-input", "value"),
    Input("update-interval", "n_intervals")
)