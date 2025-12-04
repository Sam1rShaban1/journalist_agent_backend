import os
import chainlit as cl
from journalist_crew.crew import JournalistCrew

# --- 1. AUTHENTICATION (Required for Sidebar) ---
@cl.password_auth_callback
def auth(username, password):
    # Check against values in .env
    env_user = os.getenv("APP_USER")
    env_pass = os.getenv("APP_PASSWORD")
    
    if username == env_user and password == env_pass:
        return cl.User(identifier=username)
    return None

# --- 2. CHAT RESUME (Fixes KeyError) ---
@cl.on_chat_resume
async def on_resume(thread: dict): # <--- Fixed type hint here
    # When a user clicks a past chat in the sidebar, this runs.
    # We just need to re-initialize the crew context.
    crew = JournalistCrew()
    cl.user_session.set("crew", crew)
    
    await cl.Message(content="👋 Mirësevini përsëri! Seanca u rikthye.").send()
    await show_main_menu()

# --- 3. SESSION START ---
@cl.on_chat_start
async def start():
    # Initialize the Crew logic
    crew = JournalistCrew()
    cl.user_session.set("crew", crew)

    # Show existing history from DB
    sessions = crew.db.list_dossiers()
    welcome_msg = "## 📰 Mirësevini në Studion e Gazetarisë AI\n\n"
    
    if sessions:
        welcome_msg += "**Temat e mëparshme:**\n"
        for s in sessions[:5]: 
            welcome_msg += f"* {s['topic']} (Përditësuar: {s['modified_at']})\n"
    else:
        welcome_msg += "Nuk u gjetën kërkime të mëparshme."

    await cl.Message(content=welcome_msg).send()

    # Ask for Topic
    res = await cl.AskUserMessage(content="Ju lutem shkruani **Emrin e Temës** për të ngarkuar ose filluar kërkimin.", timeout=600).send()
    if res:
        topic = res["output"]
        # Save topic to metadata for the sidebar title
        cl.user_session.set("chat_settings", {"topic": topic})
        await process_topic_selection(topic)

async def process_topic_selection(topic):
    crew = cl.user_session.get("crew")
    
    # Update Chat Title in Sidebar
    await cl.header_header(element=topic) # Sets the chat title
    
    msg = cl.Message(content=f"🔎 Duke kontrolluar bazën e të dhënave për **{topic}**...")
    await msg.send()
    
    if crew.load_context(topic):
        msg.content = f"✅ U ngarkua dosja ekzistuese për **{topic}**."
        await msg.update()
        await show_main_menu()
    else:
        msg.content = f"🚀 Duke filluar kërkim të ri për **{topic}**... (Kjo kërkon disa minuta)"
        await msg.update()
        
        # Run Research (Async wrapper)
        dossier = await cl.make_async(crew.run_research)(topic)
        
        await cl.Message(content=f"✅ Kërkimi Përfundoi!\n\n**Përmbledhje:**\n{dossier.executive_summary[0]}...").send()
        await show_main_menu()

# --- 4. THE MENU (BUTTONS) ---
async def show_main_menu():
    actions = [
        cl.Action(name="write_draft", value="write", label="✍️ Shkruaj Artikull"),
        cl.Action(name="view_history", value="history", label="📜 Shiko Historikun"),
        cl.Action(name="dig_deeper", value="dig", label="🕵️ Kërko më Thellë"),
    ]
    await cl.Message(content="**Çfarë dëshironi të bëni më pas?**", actions=actions).send()

# --- 5. ACTION HANDLERS ---
@cl.action_callback("write_draft")
async def on_write(action):
    res = await cl.AskUserMessage(content="📝 Shkruani udhëzimet (p.sh., 'Shkruaj në Shqip', 'Fokuso tek korrupsioni'):", timeout=600).send()
    if res:
        instructions = res["output"]
        crew = cl.user_session.get("crew")
        
        msg = cl.Message(content="✍️ Duke shkruar artikullin...")
        await msg.send()
        
        article = await cl.make_async(crew.run_writer)(instructions, "Albanian") 
        
        msg.content = article
        await msg.update()
        await show_main_menu()

@cl.action_callback("view_history")
async def on_history(action):
    crew = cl.user_session.get("crew")
    if not crew.current_dossier:
        await cl.Message(content="Asnjë dosje nuk është ngarkuar.").send()
        return

    history = crew.db.get_article_history(crew.current_dossier.id)
    if not history:
        await cl.Message(content="Ende nuk është shkruar asnjë draft.").send()
    else:
        content = "## 📜 Historiku i Drafteve\n"
        for art in history:
            content += f"**{art['created_at']}** ({art['language']})\n> {art['instructions']}\n\n---\n"
        await cl.Message(content=content).send()
    
    await show_main_menu()

@cl.action_callback("dig_deeper")
async def on_dig(action):
    res = await cl.AskUserMessage(content="🕵️ Cili informacion specifik mungon? (p.sh., 'Gjej buxhetin e 2023'):", timeout=600).send()
    if res:
        focus = res["output"]
        crew = cl.user_session.get("crew")
        topic = crew.current_dossier.topic
        
        msg = cl.Message(content=f"🚀 Duke përditësuar kërkimin për **{topic}** me fokus: *{focus}*...")
        await msg.send()
        
        await cl.make_async(crew.run_research)(topic, instructions=focus)
        
        msg.content = "✅ Kërkimi u përditësua."
        await msg.update()
        await show_main_menu()