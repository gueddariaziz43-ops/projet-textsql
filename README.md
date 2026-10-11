# Assistant Text-to-SQL

Application permettant de poser des questions en langage naturel sur une base
de donnees MySQL (produits, fournisseurs, achats, clients, factures) et d'obtenir
une reponse generee automatiquement par un modele LLM local (Ollama / Mistral),
en passant par un workflow n8n qui genere, verifie et execute le SQL correspondant.

## Architecture

```
Utilisateur --> Streamlit (app/chat_app.py) --> Webhook n8n
    --> Agent 1 (Ollama) : genere la requete SQL
    --> Verification : une seule requete, SELECT uniquement, sinon refus
    --> MySQL : execute la requete (utilisateur en lecture seule)
    --> Agent 2 (Ollama) : reformule les resultats en une phrase claire
    --> Streamlit : affiche la reponse + le tableau des resultats
```

Le workflow n8n repond toujours au format :

```json
{ "sql_query": "SELECT ...", "agent_reply": "Il y a 12 produits actifs.", "data": [ { ... } ] }
```

Cas particuliers geres par le workflow :
- **Question hors perimetre** (salutation, meteo, poeme...) : l'Agent 1 renvoie
  `SELECT 'Question hors périmètre'`, aucune requete n'est executee et
  l'assistant explique ce qu'il sait faire.
- **Requete dangereuse** (`DELETE`, `DROP`, `UPDATE`...) : refusee avant d'arriver a MySQL.
- **Erreur SQL** : l'assistant demande de reformuler la question.
- **Agent 2 indisponible** : la reponse retombe sur « N resultat(s) trouve(s) ».

## Structure du projet

```
projet-textsql/
├── app/
│   └── chat_app.py                 Application Streamlit (interface de chat)
├── n8n/
│   └── My workflow 8.json          Workflow n8n a importer
├── sql/
│   └── utilisateur_lecture_seule.sql  Cree l'utilisateur MySQL en lecture seule
├── tests/
│   ├── run_tests.py                Tests automatises (pilote la vraie application)
│   └── test_questions.json         24 questions de test, en 4 categories
├── requirements.txt                Dependances Python
├── .gitignore
└── README.md
```

Fichiers generes a la racine (non suivis par Git) :
- `historique.json` : historique des questions/reponses
- `app.log` : logs des erreurs
- `test_results.json` : rapport des tests

## Installation

```powershell
pip install -r requirements.txt
```

Prerequis externes (non inclus dans ce depot) :
- MySQL / XAMPP demarre, avec la base `cms` importee
- Ollama demarre avec le modele `mistral` (`ollama serve`, puis `ollama pull mistral`)
- n8n demarre (`n8n start`) avec le workflow `n8n/My workflow 8.json` importe et **active**

### Securite : utilisateur MySQL en lecture seule (recommande)

Le SQL est genere par un LLM : il ne faut pas lui donner le droit de modifier la base.

1. Ouvrir `sql/utilisateur_lecture_seule.sql`, remplacer le mot de passe.
2. L'executer dans phpMyAdmin (onglet SQL).
3. Dans n8n, mettre ce nouvel utilisateur dans le credential « MySQL account ».

## Lancer l'application

Depuis la racine du projet :

```powershell
python -m streamlit run app/chat_app.py
```

Variables d'environnement optionnelles :
- `WEBHOOK_URL` : adresse du webhook n8n
  (par defaut `http://localhost:5678/webhook/sql-assistant-v2`)
- `HISTORIQUE_FILE` : chemin du fichier d'historique (par defaut `historique.json` a la racine)

## Lancer les tests automatises

Avec n8n, Ollama et MySQL demarres :

```powershell
python tests/run_tests.py
```

Pour chaque question de `test_questions.json`, le script ouvre la vraie
application Streamlit, tape la question dans le chat et attend la reponse.
Il verifie ensuite l'entree que l'application a ecrite dans `historique.json` :
- les 5 champs sont presents ;
- pour les questions sur les donnees : une requete `SELECT` a ete generee
  et la reponse n'est pas un message d'erreur ;
- pour les questions hors perimetre : aucune requete n'a ete executee.

Le rapport (reussite par categorie, temps moyen, detail de chaque question)
est ecrit dans `test_results.json`. Le script se termine avec le code 1 si au
moins une question echoue.

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
