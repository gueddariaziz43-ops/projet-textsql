import streamlit as st
import requests
import pandas as pd
import uuid
import logging
import traceback
import json
import os
from datetime import datetime, timezone

logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def dedup_safe(df):
    try:
        return df.drop_duplicates().reset_index(drop=True)
    except TypeError:
        return df.reset_index(drop=True)

st.set_page_config(page_title="Assistant Base de Donnees", page_icon="chat", layout="wide")

WEBHOOK_URL = "http://localhost:5678/webhook/sql-assistant-v2"
MAX_DISPLAY_ROWS = 10
HISTORIQUE_FILE = "historique.json"


def enregistrer_historique(user_question, sql_query, agent_reply, response_time_ms):
    entree = {
        "user_question": user_question,
        "sql_query": sql_query,
        "agent_reply": agent_reply,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "response_time_ms": response_time_ms
    }
    try:
        if os.path.exists(HISTORIQUE_FILE):
            with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                historique = json.load(f)
        else:
            historique = []
        historique.append(entree)
        with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Impossible d'ecrire dans {HISTORIQUE_FILE}: {e}\n{traceback.format_exc()}")


if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_conv" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = {"title": "Nouvelle conversation", "messages": [], "full_results": {}}
    st.session_state.current_conv = new_id

with st.sidebar:
    st.header("Conversations")

    if st.button("Nouvelle conversation", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {"title": "Nouvelle conversation", "messages": [], "full_results": {}}
        st.session_state.current_conv = new_id
        st.rerun()

    st.divider()

    for conv_id in reversed(list(st.session_state.conversations.keys())):
        conv = st.session_state.conversations[conv_id]
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(conv["title"], key=f"select_{conv_id}", use_container_width=True):
                st.session_state.current_conv = conv_id
                st.rerun()
        with col2:
            if st.button("X", key=f"delete_{conv_id}"):
                del st.session_state.conversations[conv_id]
                if st.session_state.current_conv == conv_id:
                    if st.session_state.conversations:
                        st.session_state.current_conv = list(st.session_state.conversations.keys())[0]
                    else:
                        new_id = str(uuid.uuid4())
                        st.session_state.conversations[new_id] = {"title": "Nouvelle conversation", "messages": [], "full_results": {}}
                        st.session_state.current_conv = new_id
                st.rerun()

current = st.session_state.conversations[st.session_state.current_conv]
st.title(f"Assistant Text-to-SQL - {current['title']}")

for idx, msg in enumerate(current["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if idx in current["full_results"]:
            df_full = current["full_results"][idx]
            st.dataframe(dedup_safe(df_full.head(MAX_DISPLAY_ROWS)), use_container_width=True)
            if len(df_full) > MAX_DISPLAY_ROWS:
                csv = df_full.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"Telecharger les {len(df_full)} resultats (CSV)",
                    data=csv,
                    file_name=f"resultats_{idx}.csv",
                    mime="text/csv",
                    key=f"download_{st.session_state.current_conv}_{idx}"
                )

question = st.chat_input("Pose ta question...")

if question:
    current["messages"].append({"role": "user", "content": question})

    if current["title"] == "Nouvelle conversation":
        current["title"] = question[:40] + ("..." if len(question) > 40 else "")

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Reflexion en cours..."):
            start_time = datetime.now(timezone.utc)
            sql_query = ""
            answer = ""
            try:
                response = requests.post(WEBHOOK_URL, json={"question": question}, timeout=120)
                elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

                if response.status_code == 200:
                    data = response.json()

                    if isinstance(data, dict) and "agent_reply" in data:
                        sql_query = data.get("sql_query", "")
                        answer = data.get("agent_reply", "")
                        rows = data.get("data", [])

                        st.markdown(answer)

                        if isinstance(rows, list) and len(rows) > 0:
                            df = dedup_safe(pd.DataFrame(rows))
                            total = len(df)
                            msg_idx = len(current["messages"])
                            current["full_results"][msg_idx] = df
                            st.dataframe(df.head(MAX_DISPLAY_ROWS), use_container_width=True)
                            if total > MAX_DISPLAY_ROWS:
                                csv = df.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    label=f"Telecharger les {total} resultats (CSV)",
                                    data=csv,
                                    file_name=f"resultats_{msg_idx}.csv",
                                    mime="text/csv",
                                    key=f"download_new_{st.session_state.current_conv}_{msg_idx}"
                                )

                    elif isinstance(data, list) and len(data) > 0:
                        df = dedup_safe(pd.DataFrame(data))
                        total = len(df)
                        msg_idx = len(current["messages"])
                        current["full_results"][msg_idx] = df
                        answer = f"{total} resultat(s) trouve(s) (affiches ci-dessous)."
                        st.markdown(answer)
                        st.dataframe(df.head(MAX_DISPLAY_ROWS), use_container_width=True)
                    elif isinstance(data, list) and len(data) == 0:
                        answer = "Aucun resultat trouve pour cette question."
                        st.markdown(answer)
                    else:
                        answer = str(data)
                        st.markdown(answer)
                else:
                    answer = "Une erreur est survenue cote serveur."
                    logger.error(f"Erreur serveur (status {response.status_code}) pour la question: '{question}'")
                    st.markdown(answer)

                enregistrer_historique(question, sql_query, answer, elapsed_ms)

            except requests.exceptions.Timeout:
                elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                answer = "Le serveur met trop de temps a repondre. Reessaie."
                logger.error(f"Timeout sur la question: '{question}'")
                st.markdown(answer)
                enregistrer_historique(question, sql_query, answer, elapsed_ms)
            except Exception as e:
                elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                answer = f"Impossible de contacter l'assistant : {e}"
                logger.error(f"Erreur sur la question '{question}': {e}\n{traceback.format_exc()}")
                st.markdown(answer)
                enregistrer_historique(question, sql_query, answer, elapsed_ms)

        current["messages"].append({"role": "assistant", "content": answer})
    st.rerun()
