# Assistant Text-to-SQL

Application permettant de poser des questions en langage naturel sur une base
de donnees MySQL (produits, fournisseurs, achats, clients) et d'obtenir une
reponse generee automatiquement via un modele LLM local (Ollama / Mistral),
en passant par un workflow n8n qui genere et execute le SQL correspondant.

## Architecture

```
Utilisateur --> Streamlit (chat_app.py) --> Webhook n8n --> Ollama (genere le SQL)
                                                          --> MySQL (execute le SQL)
                                                          --> Reponse reformulee --> Streamlit
```

## Structure du projet

```
projet-textsql/
├── chat_app.py          Application Streamlit (interface de chat)
├── run_tests.py          Script de test batch (lit test_questions.json)
├── test_questions.json   20-30 questions de test, reparties en 4 categories
├── test_results.json     Resultats generes apres l'execution de run_tests.py
├── historique.json       Historique des questions/reponses (genere a l'usage)
├── app.log                Fichier de logs des erreurs (genere a l'usage)
├── requirements.txt       Dependances Python
├── .gitignore
└── README.md
```

## Installation

```powershell
pip install -r requirements.txt
```

Prerequis externes (non inclus dans ce depot) :
- MySQL / XAMPP demarre, avec la base `cms` importee
- Ollama demarre avec le modele `mistral` (`ollama serve`)
- n8n demarre avec le workflow importe (`n8n start`)

## Lancer l'application

```powershell
python -m streamlit run chat_app.py
```

## Lancer les tests automatises

```powershell
python run_tests.py
```

Le script lit `test_questions.json`, envoie chaque question a l'application,
et verifie que `historique.json` a bien ete complete. Un rapport est ecrit
dans `test_results.json`.

## Historique des echanges

Chaque question posee est enregistree dans `historique.json` avec 5 champs :
- `user_question` : la question posee
- `sql_query` : la requete SQL generee par l'Agent 1
- `agent_reply` : la reponse finale de l'Agent 2
- `timestamp` : date/heure ISO 8601
- `response_time_ms` : temps de traitement total en millisecondes

## Logs

Toutes les erreurs (SQL, timeout, exceptions) sont enregistrees dans
`app.log` avec niveau ERROR, timestamp et stack trace complete.
