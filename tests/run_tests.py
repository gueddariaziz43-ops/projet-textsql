import json
import requests
import time
from datetime import datetime, timezone

WEBHOOK_URL = "http://localhost:5678/webhook/sql-assistant-v2"
TEST_FILE = "test_questions.json"
HISTORY_FILE = "historique.json"
RESULTS_FILE = "test_results.json"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_history_count():
    try:
        history = load_json(HISTORY_FILE)
        return len(history)
    except FileNotFoundError:
        return 0

def run_test(category, question):
    print(f"[{category}] Test : {question}")
    history_before = get_history_count()
    start = time.time()

    try:
        response = requests.post(WEBHOOK_URL, json={"question": question}, timeout=120)
        elapsed_ms = round((time.time() - start) * 1000)
        status = "OK" if response.status_code == 200 else f"HTTP_ERROR_{response.status_code}"
        data = response.json() if response.status_code == 200 else None
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.time() - start) * 1000)
        status = "TIMEOUT"
        data = None
    except Exception as e:
        elapsed_ms = round((time.time() - start) * 1000)
        status = f"EXCEPTION: {e}"
        data = None

    time.sleep(1)
    history_after = get_history_count()
    logged = history_after > history_before

    return {
        "category": category,
        "question": question,
        "status": status,
        "response_time_ms": elapsed_ms,
        "logged_in_history": logged,
        "raw_response": data,
        "tested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def main():
    test_data = load_json(TEST_FILE)
    results = []

    for category, questions in test_data["categories"].items():
        for question in questions:
            result = run_test(category, question)
            results.append(result)

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = len(results)
    success = sum(1 for r in results if r["status"] == "OK")
    print(f"\n--- Résumé ---\n{success}/{total} tests réussis (statut OK)")
    print(f"Résultats détaillés sauvegardés dans {RESULTS_FILE}")

if __name__ == "__main__":
    main()