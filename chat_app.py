import streamlit as st
import requests
import pandas as pd
import uuid
import logging
import traceback

logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Assistant Base de Donnees", page_icon="chat", layout="wide")

WEBHOOK_URL = "http://localhost:5678/webhook/sql-assistant-v2"
MAX_DISPLAY_ROWS = 10

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
            st.dataframe(df_full.head(MAX_DISPLAY_ROWS).drop_duplicates().reset_index(drop=True), use_container_width=True)
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
            try:
                response = requests.post(WEBHOOK_URL, json={"question": question}, timeout=120)
                if response.status_code == 200:
                    data = response.json()

                    if isinstance(data, list) and len(data) > 0:
                        df = pd.DataFrame(data).drop_duplicates().reset_index(drop=True)
                        total = len(df)
                        msg_idx = len(current["messages"])
                        current["full_results"][msg_idx] = df

                        if total > MAX_DISPLAY_ROWS:
                            answer = f"{total} resultats trouves (apercu des {MAX_DISPLAY_ROWS} premiers ci-dessous)."
                            st.markdown(answer)
                            st.dataframe(df.head(MAX_DISPLAY_ROWS), use_container_width=True)
                            csv = df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label=f"Telecharger les {total} resultats (CSV)",
                                data=csv,
                                file_name=f"resultats_{msg_idx}.csv",
                                mime="text/csv",
                                key=f"download_new_{st.session_state.current_conv}_{msg_idx}"
                            )
                        else:
                            answer = f"{total} resultat(s) trouve(s) (affiches ci-dessous)."
                            st.markdown(answer)
                            st.dataframe(df, use_container_width=True)
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
            except requests.exceptions.Timeout:
                answer = "Le serveur met trop de temps a repondre. Reessaie."
                logger.error(f"Timeout sur la question: '{question}'")
                st.markdown(answer)
            except Exception as e:
                answer = f"Impossible de contacter l'assistant : {e}"
                logger.error(f"Erreur sur la question '{question}': {e}\n{traceback.format_exc()}")
                st.markdown(answer)

        current["messages"].append({"role": "assistant", "content": answer})
    st.rerun()
