import gradio as gr
import argparse
import json
import os
import uuid
from datetime import datetime
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# Configure RAGFlow API
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    model = config['model']
    api_key = config['api_key']
    dialogid = config['dialogid']

client = OpenAI(
    api_key=api_key,
    base_url=f"http://10.181.209.154/api/v1/chats_openai/{dialogid}"
)

HISTORY_DIR = "chat_history"

SYSTEM_PROMPT = "You are a helpful assistant. Answer questions in as much detail as possible."

def ask_bot(prompt, history_messages):
    """Handle AI chat request, return full response string"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant"):
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False
        )
        return completion.choices[0].message.content

    except Exception as e:
        return f"API error: {str(e)}"

def save_chat(session_id, messages):
    """Save chat history to file"""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    filepath = os.path.join(HISTORY_DIR, f"{session_id}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "session_id": session_id,
            "messages": messages,
            "created_at": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

def load_chat(session_id):
    """Load chat history"""
    filepath = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get("messages", [])
            # Migrate old tuple-format messages to dict format
            migrated = []
            for msg in messages:
                if isinstance(msg, dict):
                    migrated.append(msg)
                elif isinstance(msg, (list, tuple)) and len(msg) == 2:
                    migrated.append({"role": "user", "content": str(msg[0])})
                    if msg[1]:
                        migrated.append({"role": "assistant", "content": str(msg[1])})
            return migrated
    return []

def get_chat_list():
    """Get all historical chat sessions"""
    if not os.path.exists(HISTORY_DIR):
        return []
    files = []
    for f in os.listdir(HISTORY_DIR):
        if f.endswith('.json'):
            filepath = os.path.join(HISTORY_DIR, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            messages = load_chat(f[:-5])
            preview = messages[0].get("content", "")[:30] + "..." if messages else "Empty chat"
            files.append({
                "name": f"{preview}",
                "date": mtime.strftime("%Y-%m-%d %H:%M"),
                "session_id": f[:-5]
            })
    files.sort(key=lambda x: x["date"], reverse=True)
    return files

def new_chat():
    """Create new chat"""
    return [], str(uuid.uuid4())

def switch_chat(session_id, current_history):
    """Switch to specified history session"""
    if not session_id:
        return [], str(uuid.uuid4())
    messages = load_chat(session_id)
    for msg in messages:
        if msg.get("role") == "user":
            msg["name"] = "User"
        elif msg.get("role") == "assistant":
            msg["name"] = "Chatbot"
    return messages, session_id

def delete_chat(session_id):
    """Delete specified session"""
    filepath = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def clear_all_history():
    """Clear all history"""
    if os.path.exists(HISTORY_DIR):
        for f in os.listdir(HISTORY_DIR):
            if f.endswith('.json'):
                os.remove(os.path.join(HISTORY_DIR, f))
    return [], str(uuid.uuid4())

def select_history_item(session_id):
    """Load session when history item is clicked"""
    if session_id:
        messages = load_chat(session_id)
        for msg in messages:
            if msg.get("role") == "user":
                msg["name"] = "User"
            elif msg.get("role") == "assistant":
                msg["name"] = "Chatbot"
        return messages, session_id
    return [], str(uuid.uuid4())

def load_history():
    """Load chat history list"""
    files = get_chat_list()
    return [[f"{item['name']} ({item['date']})"] for item in files]

def get_model_display_name():
    # Get model display name
    return model

# ======================== Gradio UI ========================
css = """
/* Container */
.gradio-container {
    font-family: 'Segoe UI', -apple-system, sans-serif !important;
}

/* Hide scrollbars globally */
* {
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
}
*::-webkit-scrollbar {
    display: none !important;
}

/* Title area */
.title-header {
    text-align: center;
    padding: 20px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    margin: -20px -20px 20px -20px;
    border-radius: 0 0 20px 20px;
}

.title-header h1 {
    color: white !important;
    font-size: 2em !important;
    font-weight: 600 !important;
    margin: 0 !important;
    letter-spacing: 1px;
}

.title-header p {
    color: rgba(255,255,255,0.9) !important;
    font-size: 0.9em !important;
    margin: 8px 0 0 0 !important;
}

/* Sidebar */
#chatbot {
    height: 450px;
}

.sidebar {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 15px;
    height: 100%;
}

.sidebar-btn {
    width: 100%;
    margin-bottom: 8px;
    border-radius: 8px !important;
    transition: all 0.2s;
}

.sidebar-btn:hover {
    transform: translateX(5px);
}

.new-chat-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    font-weight: 500;
}

.clear-btn {
    background: #ff4757 !important;
    color: white !important;
    border: none !important;
}

.history-item {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 6px;
    cursor: pointer;
    transition: all 0.2s;
}

.history-item:hover {
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.history-item .session-title {
    font-size: 0.85em;
    font-weight: 500;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.history-item .session-date {
    font-size: 0.75em;
    color: #999;
    margin-top: 4px;
}

/* Chat area */
.chat-container {
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    padding: 20px;
    height: 100%;
}

/* Chat messages */
.user-message {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    max-width: 75%;
    margin-left: auto;
    font-size: 0.95em;
    line-height: 1.5;
}

.bot-message {
    background: #f1f3f5;
    color: #333;
    border-radius: 18px 18px 18px 4px;
    padding: 12px 16px;
    max-width: 75%;
    font-size: 0.95em;
    line-height: 1.5;
}

/* Avatar image size override */
#chatbot .avatar-container,
#chatbot picture,
.grado-avatar,
.gradio-container img.avatar,
img.avatar {
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    min-height: 52px !important;
    border-radius: 50% !important;
    overflow: hidden !important;
}

/* Avatar image overrides */
#chatbot .avatar-container img,
#chatbot picture img,
.svelte-vlp1qv img,
.gradio-container img.avatar,
img.avatar {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
    object-position: center !important;
    border-radius: 50% !important;
}
.message.svelte-vlp1qv[data-testid="user"] > .avatar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}
.message.svelte-vlp1qv[data-testid="bot"] > .avatar {
    background: #f1f3f5;
    color: #333;
}

/* Input area */
.input-area {
    margin-top: 20px;
}

.input-row {
    display: flex !important;
    gap: 12px;
    flex-wrap: nowrap !important;
    align-items: center;
    width: 100%;
}

#message {
    flex: 5 !important;
    min-width: 0;
    border-radius: 24px !important;
    border: 2px solid #e0e0e0 !important;
    padding: 14px 20px !important;
    font-size: 1em !important;
    transition: all 0.2s;
}

#submit {
    flex: 0 0 auto !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 12px 28px !important;
    font-weight: 500 !important;
    transition: all 0.2s;
}

#message:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
}

#submit:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

/* Model info */
.model-info {
    text-align: center;
    padding: 12px;
    background: #f8f9fa;
    border-radius: 10px;
    margin-bottom: 15px;
    font-size: 0.85em;
    color: #666;
}

/* Chat history list */
.chat-history-item {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 6px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
}

.chat-history-item:hover {
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.chat-history-item.selected {
    border-color: #667eea;
    background: #f0f1ff;
}

.chat-history-item .session-title {
    font-size: 0.85em;
    font-weight: 500;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 30px;
}

.chat-history-item .session-date {
    font-size: 0.75em;
    color: #999;
    margin-top: 4px;
}

.chat-history-item .delete-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #ff4757;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 0.75em;
    padding: 2px 8px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
}

.chat-history-item:hover .delete-btn {
    opacity: 1;
}

/* Hide default Gradio elements */
footer {
    display: none !important;
}

"""

with gr.Blocks(css=css, theme=gr.themes.Soft()) as demo:
    session_id = gr.State(value=str(uuid.uuid4()))

    with gr.Row():
        with gr.Column(scale=2):
                # Main chat area
                with gr.Column(elem_classes="chat-container"):
                    gr.HTML("""
                    <div class="title-header">
                        <h1>Knowledge Mining</h1>
                        <p>Intelligent Knowledge Mining & Q&A System</p>
                    </div>
                    """)

                    chatbot = gr.Chatbot(
                        type='messages',
                        show_label=False,
                        avatar_images=("user.jpg", "chatbot.gif"),
                        elem_id="chatbot",
                        min_height=600,
                    )

                    with gr.Row(elem_classes="input-row"):
                        message = gr.Textbox(
                            placeholder="Ask a question and start chatting...",
                            scale=5,
                            autofocus=True,
                            lines=1,
                            container=False,
                            elem_id="message",
                        )
                        submit = gr.Button("Send", scale=1, variant="primary", elem_id="submit")

                    model_info = gr.Markdown(f"**Model:** `{model}`", elem_classes="model-info")

        with gr.Column(scale=1, min_width=220):
            # Sidebar
            with gr.Column(elem_classes="sidebar"):
                new_btn = gr.Button("+ New Chat", elem_classes="sidebar-btn new-chat-btn")
                clear_all_btn = gr.Button("Clear All History", elem_classes="sidebar-btn clear-btn")

                gr.HTML("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e0e0e0;'>")
                gr.HTML("<p style='font-size: 0.85em; color: #666; margin-bottom: 10px;'>📁 Chat History</p>")

                # Hidden field to store selected session_id
                selected_session = gr.Number(visible=False, value=None)

                # Chat history list (clickable)
                chat_list = gr.Dataframe(
                    headers=["Session"],
                    datatype=["str"],
                    interactive=False,
                    elem_id="chat-list"
                )

                # Delete selected session button
                delete_btn = gr.Button("Delete Selected", elem_classes="sidebar-btn", variant="stop")

    # ==================== Event Bindings ===================

    # Step 1: Add user message immediately, clear input
    def on_submit(inputs, history, session_id):
        if not inputs or not inputs.strip():
            return history, "", session_id
        history = history or []
        history = history + [{"role": "user", "content": inputs, "name": "User"}]
        return history, "", session_id

    # Step 2: Call API and add bot response (chained after step 1)
    def on_bot_response(history, session_id):
        history = history or []
        user_input = history[-1]["content"] if history and history[-1].get("role") == "user" else ""
        if not user_input:
            return history, session_id
        response = ask_bot(user_input, history[:-1])
        history = history + [{"role": "assistant", "content": response, "name": "Chatbot"}]
        save_chat(session_id, history)
        return history, session_id

    submit.click(
        on_submit, [message, chatbot, session_id], [chatbot, message, session_id]
    ).then(
        on_bot_response, [chatbot, session_id], [chatbot, session_id]
    )
    message.submit(
        on_submit, [message, chatbot, session_id], [chatbot, message, session_id]
    ).then(
        on_bot_response, [chatbot, session_id], [chatbot, session_id]
    )

    # New chat
    new_btn.click(new_chat, outputs=[chatbot, session_id])

    # Clear all history
    clear_all_btn.click(
        clear_all_history,
        outputs=[chatbot, session_id]
    ).then(load_history, outputs=[chat_list])

    # Click history → switch session + update selected_session
    def handle_select(evt: gr.SelectData, current_chat, current_session):
        """Load session for clicked row and record selected ID"""
        files = get_chat_list()
        row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        if row < len(files):
            item = files[row]
            messages = load_chat(item["session_id"])
            for msg in messages:
                if msg.get("role") == "user":
                    msg["name"] = "User"
                elif msg.get("role") == "assistant":
                    msg["name"] = "Chatbot"
            return messages, item["session_id"], item["session_id"]
        return current_chat, current_session, None

    chat_list.select(
        handle_select,
        [chatbot, session_id],
        [chatbot, session_id, selected_session]
    )

    # Delete button → read selected_session, delete file, refresh list
    def do_delete(sid):
        if sid:
            filepath = os.path.join(HISTORY_DIR, f"{sid}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
        return None

    delete_btn.click(
        do_delete,
        [selected_session],
        [selected_session]
    ).then(
        load_history,
        outputs=[chat_list]
    )

    # Load history list on page load
    demo.load(load_history, outputs=[chat_list])

demo.launch(debug=False, show_api=False, server_port=7860)
