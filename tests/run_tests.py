"""
Script de test batch pour l'assistant Text-to-SQL.

Chaque question de test_questions.json est posee a la VRAIE application Streamlit
(app/chat_app.py), pilotee avec streamlit.testing. On verifie ensuite ce que
l'application a elle-meme enregistre dans historique.json.

Prerequis : n8n, Ollama et MySQL demarres (comme pour utiliser l'application).
Lancement, depuis n'importe quel dossier :
    python tests/run_tests.py
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TESTS_DIR)
APP_PATH = os.path.join(BASE_DIR, "app", "chat_app.py")
TEST_QUESTIONS_FILE = os.path.join(TESTS_DIR, "test_questions.json")
RESULTS_FILE = os.path.join(BASE_DIR, "test_results.json")
TIMEOUT_SECONDS = 150

# Meme fichier que l'application (meme variable d'environnement, meme valeur par defaut)
os.environ.setdefault("HISTORIQUE_FILE", os.path.join(BASE_DIR, "historique.json"))
HISTORIQUE_FILE = os.environ["HISTORIQUE_FILE"]

CATEGORIE_HORS_PERIMETRE = "hors_perimetre"

# Debuts des messages que l'application affiche quand quelque chose a echoue
MESSAGES_ECHEC = (
    "Impossible de contacter l'assistant",
    "Une erreur est survenue",
    "Le serveur met trop de temps",
    "Je n'ai pas compris",
)


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


def poser_question_a_l_app(question):
    """Ouvre l'application, tape la question dans le chat et attend la reponse."""
    from streamlit.testing.v1 import AppTest

    # Avertissement "missing ScriptRunContext" : normal quand Streamlit est pilote par un script
    logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.chat_input[0].set_value(question).run()
    if at.exception:
        return False, str(at.exception[0].message)
    return True, None


def nouvelle_entree(question, nb_avant):
    """Renvoie l'entree ajoutee par l'application pour cette question, ou None."""
    historique = charger_historique(HISTORIQUE_FILE)
    for entree in historique[nb_avant:]:
        if entree.get("user_question") == question:
            return entree
    return None


def evaluer(categorie, entree):
    """Renvoie (succes, raison) a partir de l'entree d'historique."""
    if entree is None:
        return False, "question absente de historique.json"

    champs = {"user_question", "sql_query", "agent_reply", "timestamp", "response_time_ms"}
    manquants = champs - set(entree)
    if manquants:
        return False, f"champs manquants : {sorted(manquants)}"

    sql = (entree.get("sql_query") or "").strip()
    reponse = (entree.get("agent_reply") or "").strip()

    if any(reponse.startswith(m) for m in MESSAGES_ECHEC):
        return False, f"reponse d'echec : {reponse[:80]}"

    if categorie == CATEGORIE_HORS_PERIMETRE:
        if sql == "" or re.search(r"hors\s+p[ée]rim[èe]tre", sql, re.IGNORECASE):
            return True, "refusee comme hors perimetre"
        return False, f"aurait du etre refusee, SQL genere : {sql[:80]}"

    if not re.match(r"(SELECT|WITH)\b", sql, re.IGNORECASE):
        return False, f"pas de requete SELECT : {sql[:80] or '(vide)'}"
    if not reponse:
        return False, "reponse vide"
    return True, "ok"


def main():
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

            nb_avant = len(charger_historique(HISTORIQUE_FILE))
            app_ok, erreur_app = poser_question_a_l_app(question)
            entree = nouvelle_entree(question, nb_avant)

            if app_ok:
                succes, raison = evaluer(categorie, entree)
            else:
                succes, raison = False, f"exception dans l'application : {erreur_app}"

            resultats.append({
                "question": question,
                "categorie": categorie,
                "succes": succes,
                "raison": raison,
                "sql_query": entree.get("sql_query") if entree else None,
                "agent_reply": entree.get("agent_reply") if entree else None,
                "response_time_ms": entree.get("response_time_ms") if entree else None,
                "timestamp_test": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

            duree = f" ({entree['response_time_ms']} ms)" if entree else ""
            print(f"    -> {'OK' if succes else 'ECHEC'}{duree} : {raison}")
        print()

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    for categorie in categories:
        res_cat = [r for r in resultats if r["categorie"] == categorie]
        nb_ok = sum(r["succes"] for r in res_cat)
        print(f"{categorie:<22} {nb_ok}/{len(res_cat)}")
    nb_succes = sum(r["succes"] for r in resultats)
    temps = [r["response_time_ms"] for r in resultats if r["response_time_ms"] is not None]
    if temps:
        print(f"Temps de reponse moyen : {sum(temps) // len(temps)} ms")
    print(f"Total : {nb_succes}/{total} questions reussies.")
    print(f"Resultats detailles ecrits dans {RESULTS_FILE}")
    return 0 if nb_succes == total else 1


if __name__ == "__main__":
    sys.exit(main())
