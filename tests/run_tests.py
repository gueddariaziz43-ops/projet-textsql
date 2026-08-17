"""
Script de test batch pour l'assistant Text-to-SQL.
"""

import json
import time
import requests
from datetime import datetime, timezone

WEBHOOK_URL = "http://localhost:5678/webhook/sql-assistant-v2"
TEST_QUESTIONS_FILE = "test_questions.json"
HISTORIQUE_FILE = "historique.json"
RESULTS_FILE = "test_results.json"
TIMEOUT_SECONDS = 120


def charger_questions(chemin):
    with open(chemin, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


def charger_historique(chemin):
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def enregistrer_historique(user_question, sql_query, agent_reply, response_time_ms):
    entree = {
        "user_question": user_question,
        "sql_query": sql_query,
        "agent_reply": agent_reply,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "response_time_ms": response_time_ms
    }
    historique = charger_historique(HISTORIQUE_FILE)
    historique.append(entree)
    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


def poser_question(question):
    start = time.time()
    try:
        resp = requests.post(WEBHOOK_URL, json={"question": question}, timeout=TIMEOUT_SECONDS)
        duree_ms = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            return True, resp.json(), duree_ms
        else:
            return False, f"Status HTTP {resp.status_code}", duree_ms
    except requests.exceptions.Timeout:
        duree_ms = int((time.time() - start) * 1000)
        return False, "Timeout", duree_ms
    except Exception as e:
        duree_ms = int((time.time() - start) * 1000)
        return False, str(e), duree_ms


def verifier_historique_contient(question, historique_avant):
    historique_apres = charger_historique(HISTORIQUE_FILE)
    if len(historique_apres) <= len(historique_avant):
        return False, None
    nouvelle_entree = historique_apres[-1]
    if nouvelle_entree.get("user_question") == question:
        return True, nouvelle_entree
    anciennes_questions = {e.get("user_question") for e in historique_avant}
    for entree in reversed(historique_apres):
        if entree.get("user_question") == question and entree.get("user_question") not in anciennes_questions:
            return True, entree
    return False, None


def main():
    print(f"Chargement de {TEST_QUESTIONS_FILE}...")
    categories = charger_questions(TEST_QUESTIONS_FILE)

    total = sum(len(qs) for qs in categories.values())
    print(f"{total} questions a tester, reparties en {len(categories)} categories.\n")

    resultats = []
    compteur = 0

    for categorie, questions in categories.items():
        print(f"--- Categorie : {categorie} ---")
        for question in questions:
            compteur += 1
            print(f"[{compteur}/{total}] {question}")

            historique_avant = charger_historique(HISTORIQUE_FILE)

            succes_http, reponse, duree_ms = poser_question(question)

            sql_query = ""
            agent_reply = ""
            if succes_http and isinstance(reponse, dict):
                sql_query = reponse.get("sql_query", "")
                agent_reply = reponse.get("agent_reply", "")
            elif not succes_http:
                agent_reply = f"ERREUR: {reponse}"

            enregistrer_historique(question, sql_query, agent_reply, duree_ms)
            historique_ok, entree_historique = verifier_historique_contient(question, historique_avant)

            resultat = {
                "question": question,
                "categorie": categorie,
                "succes_http": succes_http,
                "duree_ms": duree_ms,
                "reponse_brute": reponse if succes_http else None,
                "erreur": reponse if not succes_http else None,
                "trouve_dans_historique": historique_ok,
                "timestamp_test": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            resultats.append(resultat)

            statut = "OK" if succes_http else "ECHEC"
            print(f"    -> {statut} ({duree_ms} ms)")

        print()

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    nb_succes = sum(1 for r in resultats if r["succes_http"])
    print("=" * 50)
    print(f"Termine : {nb_succes}/{total} reponses HTTP reussies.")
    print(f"Resultats detailles ecrits dans {RESULTS_FILE}")


if __name__ == "__main__":
    main()
