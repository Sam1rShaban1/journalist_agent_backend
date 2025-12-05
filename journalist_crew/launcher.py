import os
import subprocess
import sys

def main():
    # 1. Create data directory
    os.makedirs("data", exist_ok=True)

    # 2. Check if Chainlit DB exists
    # if not os.path.exists("data/chainlit.db"):
    print("🚀 First run detected. Initializing Database Schema...")
    try:
        # Run the init script we created earlier
        subprocess.run([sys.executable, "init_chainlit_db_v3.py"], check=True)
        print("✅ Database initialized.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)

    # 3. Start Chainlit
    print("🚀 Starting Journalist Studio...")
    # Equivalent to: chainlit run src/journalist_crew/ui.py --host 0.0.0.0 --port 8000
    cmd = [
        "chainlit", "run", "src/journalist_crew/ui.py",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    
    # Replace current process with Chainlit
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()