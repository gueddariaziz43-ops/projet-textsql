# Dossier PFA - Assistant Text-to-SQL : modifications et pistes d'amelioration

## 1. Modifications realisees

| Domaine | Avant | Apres |
|---|---|---|
| Agent 2 | Un seul appel au LLM, reponse = phrase fixe | Agent 2 (Mistral) reformule les resultats en francais |
| Compteur de resultats | Affichait « undefined resultat(s) » | Compte correct, avec message de secours si Ollama est indisponible |
| Securite SQL | Seul le prompt empechait un DELETE / DROP | Verification : une seule requete, SELECT uniquement, sinon refus |
| Hors perimetre | Requete executee quand meme | Aucune requete executee, message explicatif |
| Droits MySQL | Utilisateur avec tous les droits | `sql/utilisateur_lecture_seule.sql` : SELECT sur 5 vues uniquement |
| Question avec guillemets | Cassait le JSON envoye a Ollama | Question echappee |
| Tests | Le script ecrivait lui-meme l'historique puis le verifiait (toujours OK) | Le script pilote la vraie application et verifie ce qu'elle ecrit |
| Organisation | `chat_app.py` en double, README obsolete | Un seul `app/chat_app.py`, README a jour |

## 2. Architecture

Utilisateur -> Streamlit -> Webhook n8n -> Agent 1 (SQL) -> Verification -> MySQL -> Agent 2 (reformulation) -> Streamlit

## 3. Idees d'amelioration (par priorite pour un PFA)

### Evaluation (le plus valorise dans un rapport)
1. **Mesurer la precision** : ajouter dans `tests/test_questions.json` le SQL ou le resultat attendu pour chaque question, et calculer un taux de reussite par categorie.
2. **Comparer plusieurs modeles** (mistral, llama3, qwen2.5-coder, sqlcoder) sur les memes 24 questions : tableau precision / temps de reponse.
3. **Agrandir le jeu de test** (50+ questions, cas ambigus, fautes d'orthographe, questions en arabe).

### Qualite des reponses
4. **Auto-correction** : si MySQL renvoie une erreur, renvoyer la requete et l'erreur a l'Agent 1 pour une deuxieme tentative.
5. **Memoire de conversation** : comprendre « et pour les clients actifs ? » en s'appuyant sur la question precedente.
6. **Schema dynamique** : lire les colonnes des vues depuis MySQL (`INFORMATION_SCHEMA`) au lieu de les ecrire a la main dans le prompt.
7. **Limites automatiques** : ajouter `LIMIT` et un timeout aux requetes pour eviter les resultats enormes.

### Interface
8. **Afficher la requete SQL** generee dans un bloc depliable (transparence, utile pour la soutenance).
9. **Graphiques automatiques** (barres, courbes) avec `st.bar_chart` pour les resultats numeriques.
10. **Boutons utile / pas utile** : stocker le retour utilisateur dans `historique.json`.
11. **Questions en arabe / dialecte tunisien**.

### Exploitation
12. **Tableau de bord de l'historique** : nombre de questions, temps moyen, taux d'erreur, questions les plus frequentes.
13. **Docker Compose** : MySQL + n8n + Ollama + Streamlit lances avec une seule commande.
14. **Authentification** et roles (qui a le droit de voir quelles vues).

## 4. Plan conseille pour le rapport
1. Contexte et problematique
2. Architecture (schema ci-dessus)
3. Choix techniques (Streamlit, n8n, Ollama/Mistral, MySQL)
4. Securite (verification SQL, utilisateur lecture seule)
5. Resultats : tableau de precision et temps de reponse par categorie
6. Limites et perspectives (section 3)
