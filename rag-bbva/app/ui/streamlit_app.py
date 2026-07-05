"""Interfaz conversacional (Streamlit).

Chat minimalista y funcional que consume la API /chat. Maneja el session_id por
navegador, muestra el historial y las fuentes citadas. La memoria real la lleva
el backend (SQLite); aqui solo se refleja para la vista.
"""
from __future__ import annotations

import uuid

import httpx

import streamlit as st

from app.config import get_settings

settings = get_settings()
API_URL = settings.api_url

st.set_page_config(page_title="Asistente RAG", layout="centered")
st.title("Asistente RAG del banco")
st.caption("Pregunta sobre la informacion publicada en el sitio.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []


def _render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander("Fuentes"):
        for s in sources:
            label = s.get("title") or s.get("url", "")
            st.markdown(f"- [{label}]({s.get('url', '')})")


with st.sidebar:
    st.subheader("Sesion")
    st.code(st.session_state.session_id, language=None)
    st.caption(f"Contexto: ultimos {settings.conversation_window} mensajes")
    if st.button("Nueva conversacion"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Historial ya mostrado
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        _render_sources(message.get("sources", []))

# Entrada del usuario
prompt = st.chat_input("Escribe tu pregunta...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando..."):
            try:
                resp = httpx.post(
                    f"{API_URL}/chat",
                    json={
                        "session_id": st.session_state.session_id,
                        "message": prompt,
                    },
                    timeout=180,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                st.markdown(answer)
                _render_sources(sources)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )
            except httpx.HTTPStatusError as exc:
                detail = ""
                try:
                    detail = exc.response.json().get("detail", "")
                except Exception:  # noqa: BLE001
                    detail = exc.response.text
                st.error(f"La API respondio {exc.response.status_code}: {detail}")
            except httpx.RequestError as exc:
                st.error(f"No se pudo conectar con la API ({API_URL}): {exc}")
