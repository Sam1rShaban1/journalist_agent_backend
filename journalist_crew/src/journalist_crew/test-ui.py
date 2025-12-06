import os
import json
import uuid
import sqlite3
import datetime
from typing import Any, Dict, Optional

import chainlit as cl
from chainlit.input_widget import Select, TextInput
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from journalist_crew.crew import JournalistCrew


# -----------------------------------------------------------------------------
# 1. DATA LAYER
# -----------------------------------------------------------------------------
@cl.data_layer
def get_data_layer():
    # Default Chainlit DB lives next to the entry file
    return SQLAlchemyDataLayer(conninfo="sqlite+aiosqlite:///chainlit.db")


# -----------------------------------------------------------------------------
# 2. LOCALIZATION HELPERS
# -----------------------------------------------------------------------------
TRANSLATIONS: Dict[str, Dict[str, str]] = {}
LANG_CODES = ["en-US", "sq-AL"]


def _load_translations():
    base = os.path.join(os.getcwd(), ".chainlit", "translations")
    for code in LANG_CODES:
        path = os.path.join(base, f"{code}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                TRANSLATIONS[code] = data.get("app", {})
        except FileNotFoundError:
            TRANSLATIONS[code] = {}


_load_translations()


def t(key: str, **kwargs):
    user_langs = cl.user_session.get("languages", "en-US")
    lang = user_langs.split(",")[0] if user_langs else "en-US"
    text = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS.get("en-US", {}).get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


# -----------------------------------------------------------------------------
# 3. AUTH (optional password gate)
# -----------------------------------------------------------------------------
def get_authorized_users() -> Dict[str, str]:
    raw = os.getenv("CHAINLIT_USERS", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


USERS = get_authorized_users()


@cl.password_auth_callback
def auth(username: str, password: str):
    if username in USERS and USERS[username] == password:
        return cl.User(identifier=username)
    return None


# -----------------------------------------------------------------------------
# 4. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def format_dossier_to_markdown(dossier) -> str:
    md = [f"# Research Dossier: {dossier.topic}", ""]

    if dossier.executive_summary:
        md.append("### Executive Summary")
        md.extend([f"- {point}" for point in dossier.executive_summary])
        md.append("")

    if dossier.comprehensive_narrative:
        md.append("### Narrative")
        md.append(dossier.comprehensive_narrative)
        md.append("")

    if dossier.timeline:
        md.append("### Timeline")
        for event in dossier.timeline:
            md.append(f"- **{event.year}** – {event.event}")
        md.append("")

    if dossier.key_figures:
        md.append("### Key Figures")
        md.append("| Name | Role | Impact |")
        md.append("|---|---|---|")
        for fig in dossier.key_figures:
            c_name = str(fig.name).replace("|", "/")
            c_role = str(fig.role).replace("|", "/")
            c_impact = str(fig.impact).replace("|", "/")
            md.append(f"| {c_name} | {c_role} | {c_impact} |")
        md.append("")

    if getattr(dossier, "sources", None):
        md.append("### Sources")
        for src in dossier.sources:
            md.append(f"- [{src.title}]({src.url})")
        md.append("")

    return "\n".join(md)


async def send_write_action():
    """Always render the write action in its own message so Chainlit shows it after resume."""
    label = t("write_btn")
    if not label or label == "write_btn":
        label = "✍️ Write article"

    # First send the status text so the button can remain in a dedicated action block
    await cl.Message(
        content="⬇ **Research ready.** Click below to draft an article or ask follow-up questions.",
    ).send()

    unique_id = f"write-{uuid.uuid4().hex[:8]}"
    actions = [
        cl.Action(
            name="write_article",
            value="write",
            label=label,
            id=unique_id,
            payload={},
        )
    ]

    # Chainlit renders actions more reliably when the message body is minimal (especially on resume)
    await cl.Message(content=" ", actions=actions).send()


async def show_dossier(dossier):
    await cl.Message(content=format_dossier_to_markdown(dossier)).send()
    await send_write_action()


def safe_parse_metadata(metadata: Any) -> Dict[str, Any]:
    if not metadata:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except json.JSONDecodeError:
            return {}
    return {}


def manual_rename_thread(thread_id: str, new_name: str):
    try:
        conn = sqlite3.connect("chainlit.db")
        cur = conn.cursor()
        cur.execute('UPDATE threads SET name = ? WHERE id = ?', (new_name, thread_id))
        conn.commit()
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[manual_rename_thread] ignored error: {exc}")
    finally:
        conn.close()


def manual_update_metadata(thread_id: str, metadata: Dict[str, Any]):
    """Ensure metadata + createdAt always satisfy NOT NULL constraints."""
    try:
        conn = sqlite3.connect("chainlit.db")
        cur = conn.cursor()
        payload = json.dumps(metadata)

        now = datetime.datetime.utcnow().isoformat()
        cur.execute(
            '''
            INSERT INTO threads ("id", "createdAt")
            VALUES (?, ?)
            ON CONFLICT("id") DO NOTHING
            ''',
            (thread_id, now),
        )
        cur.execute('UPDATE threads SET metadata = ? WHERE id = ?', (payload, thread_id))
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[manual_update_metadata] ignored error: {exc}")
    finally:
        conn.close()


def ensure_crew() -> JournalistCrew:
    crew: Optional[JournalistCrew] = cl.user_session.get("crew")
    if not crew:
        crew = JournalistCrew()
        cl.user_session.set("crew", crew)
    return crew


def sync_dossiers_to_sidebar(user_identifier: str):
    """Populate Chainlit sidebar with any dossiers stored in journalist_studio.db."""
    try:
        if not os.path.exists("journalist_studio.db"):
            return

        j_conn = sqlite3.connect("journalist_studio.db")
        j_cur = j_conn.cursor()
        j_cur.execute("SELECT id, topic, created_at FROM dossiers")
        dossiers = j_cur.fetchall()
        j_conn.close()

        c_conn = sqlite3.connect("chainlit.db")
        c_cur = c_conn.cursor()
        c_cur.execute('SELECT "id" FROM threads WHERE "userId" = ?', (user_identifier,))
        existing = {row[0] for row in c_cur.fetchall()}

        inserted = False
        for doc_id, topic, created_at in dossiers:
            if doc_id in existing:
                continue
            created = created_at or datetime.datetime.utcnow().isoformat()
            c_cur.execute(
                '''
                INSERT INTO threads ("id", "createdAt", "name", "userId", "userIdentifier", "metadata")
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    doc_id,
                    created,
                    topic,
                    user_identifier,
                    user_identifier,
                    json.dumps({"dossier_id": doc_id, "topic_name": topic}),
                ),
            )
            inserted = True
        if inserted:
            c_conn.commit()
        c_conn.close()
    except Exception as exc:  # pragma: no cover
        print(f"[sync_dossiers_to_sidebar] ignored error: {exc}")


# -----------------------------------------------------------------------------
# 5. EVENT HANDLERS
# -----------------------------------------------------------------------------
@cl.on_chat_start
async def on_start():
    user = cl.user_session.get("user")
    if user:
        sync_dossiers_to_sidebar(user.identifier)

    crew = ensure_crew()

    settings = await cl.ChatSettings(
        [
            Select(
                id="Language",
                label="Article Language",
                values=["Albanian", "English", "Macedonian"],
                initial_index=0,
            ),
            Select(id="Tone", label="Writing Tone", values=["Serious", "Neutral"], initial_index=0),
            TextInput(id="Focus", label="Focus", initial="Corruption"),
        ]
    ).send()
    cl.user_session.set("article_settings", settings)

    await cl.Message(
        content="👋 **Welcome to Journalist Crew.**\nDescribe a topic to start or pick an existing dossier.",
    ).send()
    crew.current_dossier = None


@cl.on_chat_resume
async def on_resume(thread: Dict[str, Any]):
    # Always create a fresh crew for this session
    crew = JournalistCrew()
    cl.user_session.set("crew", crew)
    
    metadata = safe_parse_metadata(thread.get("metadata"))
    dossier_id = metadata.get("dossier_id") or thread.get("id")
    
    print(f"[on_resume] Attempting to load dossier_id: {dossier_id}")
    
    if dossier_id and crew.load_context(dossier_id):
        await cl.Message(content="✅ Session restored from previous research.").send()
        # Ensure dossier is loaded before showing
        if crew.current_dossier:
            await show_dossier(crew.current_dossier)
        else:
            await cl.Message(content="❗Dossier loaded but content missing. Start fresh.").send()
    else:
        await cl.Message(content="❗Unable to restore this session. Start fresh with a new prompt.").send()


@cl.on_settings_update
async def on_settings_update(settings):
    cl.user_session.set("article_settings", settings)
    await cl.Message(content="⚙️ Settings updated.").send()


@cl.on_message
async def on_message(message: cl.Message):
    crew = ensure_crew()
    user_input = message.content.strip()

    loader = cl.Message(content="⏳ Agents are working...")
    await loader.send()

    if not crew.current_dossier:
        # Treat the first user message as topic / dossier identifier
        topic_or_id = user_input

        # Rename thread for readability
        if cl.context.session.thread_id:
            manual_rename_thread(cl.context.session.thread_id, topic_or_id)

        # Attempt to load existing dossier first
        if crew.load_context(topic_or_id):
            step_output = "Loaded dossier from archive."
        else:
            await cl.make_async(crew.run_research)(topic_or_id)
            step_output = "Fresh research completed."

        if crew.current_dossier and cl.context.session.thread_id:
            manual_update_metadata(
                cl.context.session.thread_id,
                {"dossier_id": crew.current_dossier.id, "topic_name": crew.current_dossier.topic},
            )

        await loader.remove()
        await cl.Step(name="Research Agent", type="run").send_token(step_output)
        await show_dossier(crew.current_dossier)
        return

    # We already have a dossier loaded -> treat as follow-up instructions
    topic = crew.current_dossier.topic
    await cl.Step(
        name="Research Agent",
        type="run",
        input=f"Dig deeper on '{topic}' with user instruction: {user_input}",
    ).__aenter__()
    await cl.make_async(crew.run_research)(topic, instructions=user_input)
    await loader.remove()
    await show_dossier(crew.current_dossier)


# -----------------------------------------------------------------------------
# 6. ACTIONS
# -----------------------------------------------------------------------------
@cl.action_callback("write_article")
async def on_write(action: cl.Action):
    crew = ensure_crew()
    if not crew.current_dossier:
        await cl.Message(content="⚠️ Research dossier missing. Ask a topic first.").send()
        return

    settings = cl.user_session.get("article_settings") or {
        "Language": "Albanian",
        "Tone": "Serious",
    }

    res = await cl.AskUserMessage(
        content=f"{t('instruction_prompt')} (Language: {settings.get('Language', 'Albanian')})",
        timeout=600,
    ).send()

    custom = res["output"].strip() if res and res.get("output") else ""
    tone = settings.get("Tone", "Serious")
    focus = settings.get("Focus")

    instructions = f"TONE: {tone}. "
    if custom:
        instructions += f"USER INSTRUCTIONS: {custom}"
    elif focus:
        instructions += f"Focus on {focus}."
    else:
        instructions += "Write a standard investigative article."

    lang_pref = settings.get("Language", "Albanian").lower()
    target_lang = "Albanian" if "albanian" in lang_pref else "English"
    if "english" in custom.lower():
        target_lang = "English"
    elif "albanian" in custom.lower():
        target_lang = "Albanian"

    loader = cl.Message(content="✍️ Drafting article...")
    await loader.send()

    async with cl.Step(name="Writer Agent", type="run") as step:
        step.input = instructions
        article = await cl.make_async(crew.run_writer)(instructions, target_lang)
        step.output = "Draft generated."

    await loader.remove()
    await cl.Message(content=article).send()
    await send_write_action()