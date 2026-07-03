"""UI Streamlit (placeholder del Paso 1).

En pasos siguientes se convierte en el chat conversacional que consume la API.
Por ahora solo verifica conectividad con /health.
"""
import httpx
import streamlit as st

from app.config import get_settings

settings = get_settings()

st.set_page_config(page_title="Asistente RAG", page_icon="banco")
st.title("Asistente RAG (scaffold)")

st.caption("Paso 1: esqueleto. El chat llega en pasos siguientes.")

if st.button("Probar conexion con la API"):
    try:
        resp = httpx.get(f"{settings.api_url}/health", timeout=5)
        st.success("API disponible")
        st.json(resp.json())
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo conectar con la API: {exc}")
