from langdetect import detect

from journalist_crew.crew import JournalistCrew


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
    print("AI JOURNALIST STUDIO - SESSION MANAGEMENT")
    print("=================================================")

    # 1. List Sessions from the internal DB
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
        topic_name = user_input
        crew_instance.run_research(topic_name)

    while True:
        if not crew_instance.current_dossier:
            print("Error: No Context Loaded.")
            break

        print("\n" + "="*60)
        print(f"📂 Session: {crew_instance.current_dossier.topic}")
        print(f"🆔 ID: {crew_instance.current_dossier.id}")
        print("1. ✍️  Write Draft")
        print("2. 📜 History")
        print("3. 🕵️  Dig Deeper (Update Info)")
        print("4. ❌ Exit")
        
        choice = input("Option: ")

        if choice == '1':
            prompt = input("\nInstructions: ")
            lang = detect_lang(prompt)
            # Calls the method in crew.py that uses the Smart LLM
            content = crew_instance.run_writer(prompt, lang)
            print("\n" + "-"*30)
            print(content)
            print("-" * 30 + "\n✅ Saved to DB")

        elif choice == '2':
            # Retrieve history using UUID
            history = crew_instance.db.get_article_history(crew_instance.current_dossier.id)
            if not history:
                print("No drafts yet.")
            else:
                for idx, art in enumerate(history):
                    print(f"\n--- {idx+1}. {art['created_at']} [{art['language']}] ---")
                    print(f"Prompt: {art['instructions']}")
                    print(f"Preview: {art['content'][:100]}...")

        elif choice == '3':
            focus = input("\nWhat should we focus on? ")
            print("\n🚀 Updating Research Dossier...")
            crew_instance.run_research(crew_instance.current_dossier.topic, instructions=focus)
            print("✅ Dossier Updated.")

        elif choice == '4':
            break

if __name__ == "__main__":
    main()