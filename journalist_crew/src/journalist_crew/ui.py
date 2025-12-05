import os
import json
import sqlite3
import datetime
import uuid
import chainlit as cl
from journalist_crew.crew import JournalistCrew
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.input_widget import Select, TextInput

# --- 1. DATA LAYER ---
@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo="sqlite+aiosqlite:///chainlit.db")

# --- 2. LOCALIZATION ---
TRANSLATIONS = {}
LANG_CODES = ["en-US", "sq-AL"]

def load_all_translations():
    base_path = os.path.join(os.getcwd(), ".chainlit", "translations")
    for code in LANG_CODES:
        file_path = os.path.join(base_path, f"{code}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                TRANSLATIONS[code] = data.get("app", {})
        except FileNotFoundError:
            pass
load_all_translations()

def t(key, **kwargs):
    user_langs = cl.user_session.get("languages", "en-US")
    lang = user_langs.split(",")[0] if user_langs else "en-US"
    text = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["en-US"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text

# --- 3. AUTHENTICATION ---
def get_authorized_users():
    raw_users = os.getenv("CHAINLIT_USERS", "{}")
    try:
        return json.loads(raw_users)
    except json.JSONDecodeError:
        return {}

USERS = get_authorized_users()

@cl.password_auth_callback
def auth(username, password):
    if username in USERS and USERS[username] == password:
        return cl.User(identifier=username)
    return None

# --- 4. HELPER: FORMAT DOSSIER ---
def format_dossier_to_markdown(dossier):
    md = f"# Research Dossier: {dossier.topic}\n\n"
    
    md += "### Executive Summary\n"
    for point in dossier.executive_summary:
        md += f"- {point}\n"
    
    md += "\n### Narrative\n"
    md += f"{dossier.comprehensive_narrative}\n"
    
    md += "\n### Timeline\n"
    for event in dossier.timeline:
        md += f"- **{event.year}**: {event.event}\n"

    md += "\n### Key Figures\n"
    md += "| Name | Role | Impact |\n|---|---|---|\n"
    for fig in dossier.key_figures:
        c_name = str(fig.name).replace("|", "-")
        c_role = str(fig.role).replace("|", "-")
        c_impact = str(fig.impact).replace("|", "-")
        md += f"| {c_name} | {c_role} | {c_impact} |\n"
    
    if hasattr(dossier, 'sources') and dossier.sources:
        md += "\n### Sources\n"
        for src in dossier.sources:
            md += f"- [{src.title}]({src.url})\n"

    return md

# --- 5. HELPER: ACTIONS ---
async def send_write_action():
    """Show research-ready text and a clearly visible Write Article action."""

    # 1) Normal message for full-width text
    await cl.Message(
        content="⬇**Research Ready.** Click the button below to Write, or type to research more.",
    ).send()

    # 2) Separate action message so the button always renders and triggers callbacks
    unique_id = f"action-write_{uuid.uuid4().hex[:8]}"

    actions = [
        cl.Action(
            name="write_article",
            value="write",
            label=t("write_btn"),
            payload={},
            id=unique_id,
        )
    ]

    await cl.Message(
        content=" ",  # keep a minimal body so Chainlit renders the action block
        actions=actions,
    ).send()

async def show_dossier_and_actions(dossier):
    formatted_content = format_dossier_to_markdown(dossier)
    await cl.Message(content=formatted_content).send()
    await send_write_action()

# --- 6. DB HELPERS ---
def manual_rename_thread(thread_id, new_name):
    """Safe renaming."""
    try:
        conn = sqlite3.connect("chainlit.db")
        c = conn.cursor()
        c.execute('UPDATE threads SET name = ? WHERE id = ?', (new_name, thread_id))
        conn.commit()
        conn.close()
    except Exception: pass

def manual_update_metadata(thread_id, metadata_dict):
    """Safe metadata update - PREVENTS CRASHES."""
    try:
        conn = sqlite3.connect("chainlit.db")
        c = conn.cursor()
        json_meta = json.dumps(metadata_dict)
        
        # CRITICAL: Only update if row exists. Do not Insert.
        c.execute('UPDATE threads SET metadata = ? WHERE id = ?', (json_meta, thread_id))
        
        if c.rowcount == 0:
            # If thread doesn't exist yet (rare race condition), insert it safely
            c.execute("""
                INSERT INTO threads ("id", "createdAt", "metadata") 
                VALUES (?, ?, ?)
            """, (thread_id, datetime.datetime.now().isoformat(), json_meta))
            
        conn.commit()
        conn.close()
    except Exception as e: 
        print(f"Metadata Error (Ignored): {e}")

def sync_dossiers_to_sidebar(user_identifier):
    try:
        if not os.path.exists("journalist_studio.db"): return

        j_conn = sqlite3.connect("journalist_studio.db")
        j_cursor = j_conn.cursor()
        j_cursor.execute("SELECT id, topic, created_at FROM dossiers")
        dossiers = j_cursor.fetchall()
        j_conn.close()

        c_conn = sqlite3.connect("chainlit.db")
        c_cursor = c_conn.cursor()
        c_cursor.execute('SELECT "id" FROM threads WHERE "userId" = ?', (user_identifier,))
        existing_threads = {row[0] for row in c_cursor.fetchall()}

        count = 0
        for doc_id, topic, created_at in dossiers:
            if doc_id not in existing_threads:
                safe_created_at = created_at if created_at else datetime.datetime.now().isoformat()
                c_cursor.execute("""
                    INSERT INTO threads ("id", "createdAt", "name", "userId", "userIdentifier", "metadata")
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    doc_id, safe_created_at, topic, user_identifier, user_identifier, 
                    json.dumps({"dossier_id": doc_id, "topic_name": topic})
                ))
                count += 1
        if count > 0: c_conn.commit()
        c_conn.close()
    except Exception: pass

# --- 7. EVENT HANDLERS ---
@cl.on_chat_resume
async def on_resume(thread: dict):
    crew = JournalistCrew()
    cl.user_session.set("crew", crew)

    metadata = thread.get("metadata")
    if isinstance(metadata, str):
        try: metadata = json.loads(metadata)
        except: metadata = {}
    if not metadata: metadata = {}
    
    dossier_id = metadata.get("dossier_id") or thread.get("id")

    if dossier_id and crew.load_context(dossier_id):
        await cl.Message(content=t("session_restored")).send()
        await show_dossier_and_actions(crew.current_dossier)
    else:
        await cl.Message(content="Could not load research data.").send()

@cl.on_chat_start
async def start():
    user = cl.user_session.get("user")
    if user: sync_dossiers_to_sidebar(user.identifier)
    crew = JournalistCrew()
    cl.user_session.set("crew", crew)
    
    settings = await cl.ChatSettings([
        Select(id="Language", label="Article Language", values=["Albanian", "English", "Macedonian"], initial_index=0),
        Select(id="Tone", label="Writing Tone", values=["Serious", "Neutral"], initial_index=0),
        TextInput(id="Focus", label="Focus", initial="Corruption")
    ]).send()
    cl.user_session.set("article_settings", settings)
    await cl.Message(content=f"{t('welcome_title')}\n\n{t('welcome_body')}").send()

@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("article_settings", settings)
    await cl.Message(content=f"Settings Updated.").send()

# --- 8. MAIN CHAT LOOP ---
@cl.on_message
async def main(message: cl.Message):
    crew = cl.user_session.get("crew")
    user_input = message.content
    
    loader_msg = cl.Message(content="⏳ **Agents are working...**")
    await loader_msg.send()

    if not crew.current_dossier:
        # NEW RESEARCH
        if cl.context.session.thread_id:
            manual_rename_thread(cl.context.session.thread_id, user_input)

        async with cl.Step(name="Research Agent", type="run") as step:
            step.input = user_input
            if crew.load_context(user_input):
                step.output = "Loaded from Database."
            else:
                await cl.make_async(crew.run_research)(user_input)
                step.output = "Research Completed."
        
        if crew.current_dossier:
            cl.user_session.set("dossier_id", crew.current_dossier.id)
            
            if cl.context.session.thread_id:
                manual_update_metadata(cl.context.session.thread_id, {
                    "dossier_id": crew.current_dossier.id,
                    "topic_name": crew.current_dossier.topic
                })
        
        await loader_msg.remove()
        await show_dossier_and_actions(crew.current_dossier)
        
    else:
        # DIG DEEPER
        topic = crew.current_dossier.topic
        async with cl.Step(name="Research Agent", type="run") as step:
            step.input = f"Digging deeper: {user_input}"
            await cl.make_async(crew.run_research)(topic, instructions=user_input)
            step.output = "Dossier Updated."
        
        await loader_msg.remove()
        await show_dossier_and_actions(crew.current_dossier)

# --- 9. ACTIONS ---

@cl.action_callback("write_article")
async def on_write(action):
    settings = cl.user_session.get("article_settings")
    if not settings: settings = {"Language": "Albanian", "Tone": "Serious"}
    
    lang_pref = settings.get("Language", "Albanian")
    tone_pref = settings.get("Tone", "Serious")

    custom_instructions = ""
    if action.payload:
        custom_instructions = action.payload.get("instructions", "").strip()

    instructions = f"TONE: {tone_pref}. "
    focus_pref = settings.get("Focus")
    if custom_instructions:
        instructions += f"USER INSTRUCTIONS: {custom_instructions}"
    elif focus_pref:
        instructions += f"Focus on {focus_pref}."
    else:
        instructions += "Write a standard investigative article."

    crew = cl.user_session.get("crew")
    target_lang = "Albanian" if "albanian" in lang_pref.lower() else "English"
    if custom_instructions.lower().find("english") != -1:
        target_lang = "English"
    elif custom_instructions.lower().find("albanian") != -1:
        target_lang = "Albanian"

    loader = cl.Message(content="Writing Article...")
    await loader.send()

    async with cl.Step(name="Writer Agent", type="run") as step:
        step.input = instructions
        article = await cl.make_async(crew.run_writer)(instructions, target_lang)
        step.output = "Draft Generated."
    
    await loader.remove()
    await cl.Message(content=article).send()
    
    await send_write_action()