import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("==================================================")
    print("       VELTRIX PEOPLEOPS ASSISTANT CHATBOT        ")
    print("==================================================")
    print("Connected to live server at http://127.0.0.1:8000\n")
    
    emp_id = input("Enter your Employee ID (e.g., E2004 for Employee, E2002 for Manager, E1001 for HR) [default: E2004]: ").strip()
    if not emp_id:
        emp_id = "E2004"
        
    session_id = "interactive_test_session"
    print(f"\nLogged in as {emp_id}! Type your questions below.")
    print("Type 'exit' or 'quit' to stop.\n" + "-"*50)
    
    while True:
        try:
            msg = input(f"\nYou ({emp_id}): ").strip()
            if not msg:
                continue
            if msg.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
                
            headers = {
                "X-Employee-Id": emp_id,
                "Content-Type": "application/json"
            }
            payload = {
                "session_id": session_id,
                "message": msg
            }
            
            resp = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                print(f"\nBot (Route: {data['route']}):")
                print(data['answer'])
                if data.get('citations'):
                    print("\n[Citations]:")
                    for c in data['citations']:
                        print(f"  - {c['doc_id']} ({c['locator']})")
                if data.get('tool_calls'):
                    print("\n[Tool Calls]:")
                    for t in data['tool_calls']:
                        print(f"  - {t['name']}({t['args']}) -> Status: {t['status']}")
                if data.get('pending_confirmation'):
                    print("\n⚠️ [Action Pending Confirmation: Reply 'yes' or 'confirm' to proceed]")
            else:
                print(f"\n[Error {resp.status_code}]: {resp.text}")
        except Exception as e:
            print(f"\nConnection error: {e}")
            print("Make sure your server is running (`docker compose up` or `uvicorn src.main:app`)!")
            break

if __name__ == "__main__":
    main()
