import sys
from journalist_crew.manager import JournalistSession
from langdetect import detect

def detect_lang(text):
    try:
        lang_code = detect(text)
        lang_map = {"sq": "Albanian", "mk": "Macedonian", "en": "English"}
        return lang_map.get(lang_code[:2], "English")
    except:
        return "English"

def main():
    session = JournalistSession()
    
    print("\n📰 AI JOURNALIST STUDIO - DATABASE NATIVE")
    print("-----------------------------------------")

    # 1. Topic Selection
    topics = session.db.list_topics()
    if topics:
        print("\n📚 Knowledge Base:")
        for i, t in enumerate(topics):
            print(f"{i+1}. {t}")
        print("Type a number to load history, or a NEW topic name to start fresh.")
    
    user_input = input("\nTopic > ").strip()

    # Load Existing vs Start New
    if user_input.isdigit() and int(user_input) <= len(topics):
        topic_name = topics[int(user_input)-1]
        session.load_topic(topic_name)
    else:
        topic_name = user_input
        if not session.load_topic(topic_name):
            print("\n--- Starting Phase 1: Research (This runs once) ---")
            session.research_phase(topic_name)

    # 2. Editor Loop
    while True:
        print("\n" + "="*50)
        print(f"📂 Active Dossier: {session.current_dossier.topic}")
        print("1. ✍️  Write New Draft (Instant)")
        print("2. 📜 View History")
        print("3. 🔍 Update Research")
        print("4. ❌ Exit")
        
        choice = input("Select: ")

        if choice == '1':
            prompt = input("\nInstructions (e.g., 'Focus on corruption', 'Translate to MK'): ")
            lang = detect_lang(prompt)
            print("Generating...")
            content = session.writing_phase(prompt, lang)
            print("\n" + "-"*30)
            print(content)
            print("-" * 30 + "\n✅ Saved to Database")

        elif choice == '2':
            history = session.db.get_article_history(topic_name)
            if not history:
                print("No articles yet.")
            else:
                for idx, art in enumerate(history):
                    print(f"\n--- Article #{art['id']} [{art['language']}] ---")
                    print(f"Prompt: {art['instructions']}")
                    print(f"Preview: {art['content'][:150]}...\n")
                
                vid = input("View full Article ID # (or Enter to skip): ")
                if vid.isdigit():
                    target = next((x for x in history if str(x['id']) == vid), None)
                    if target: print("\n" + target['content'])

        elif choice == '3':
            prompt = input("\nWhat info is missing? ")
            session.research_phase(topic_name, instructions=f"Update info. Focus on: {prompt}")
            
        elif choice == '4':
            break

if __name__ == "__main__":
    main()