import sys
from journalist_crew.crew import JournalistCrew
from langdetect import detect

def detect_lang(text):
    try:
        lang_code = detect(text)
        lang_map = {"sq": "Albanian", "mk": "Macedonian", "en": "English"}
        return lang_map.get(lang_code[:2], "English")
    except:
        return "English"

def main():
    crew_instance = JournalistCrew()
    
    print("=================================================")
    print("🗞️  AI JOURNALIST STUDIO - SESSION MANAGEMENT")
    print("=================================================")

    # 1. List Sessions
    sessions = crew_instance.db.list_dossiers()
    
    if sessions:
        print("\n📚 Previous Sessions:")
        for i, s in enumerate(sessions):
            print(f"{i+1}. {s['topic']} (Created: {s['created_at']})")
        print("\nType number to load, or type NEW topic name.")
    else:
        print("\nNo history found.")

    user_input = input("\nSelection > ").strip()

    if user_input.isdigit() and int(user_input) <= len(sessions):
        # Load Existing by UUID
        selected = sessions[int(user_input)-1]
        crew_instance.load_context(selected['id'])
    else:
        # Start New
        topic_name = user_input
        print(f"\n--- Creating New Session for '{topic_name}' ---")
        crew_instance.run_research(topic_name)

    # 2. Main Loop
    while True:
        print("\n" + "="*60)
        print(f"📂 Session: {crew_instance.current_dossier.topic}")
        print(f"🆔 ID: {crew_instance.current_dossier.id}")
        print("1. ✍️  Write Draft")
        print("2. 📜 History")
        print("3. ❌ Exit")
        
        choice = input("Option: ")

        if choice == '1':
            prompt = input("\nInstructions: ")
            lang = detect_lang(prompt)
            content = crew_instance.run_writer(prompt, lang)
            print("\n" + "-"*30)
            print(content)
            print("-" * 30 + "\n✅ Saved to DB")

        elif choice == '2':
            history = crew_instance.db.get_article_history(crew_instance.current_dossier.id)
            if not history:
                print("No drafts yet.")
            else:
                for idx, art in enumerate(history):
                    print(f"\n--- {idx+1}. {art['created_at']} [{art['language']}] ---")
                    print(f"Prompt: {art['instructions']}")
                    print(f"Preview: {art['content'][:100]}...")

        elif choice == '3':
            break

if __name__ == "__main__":
    main()