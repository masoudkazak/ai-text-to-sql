"""Audit page for admin/developer."""

import streamlit as st

from utils.api_client import APIClient
from utils.auth import run

st.title("Audit Logs")

user = st.session_state.get("user")
if not user:
    st.warning("Please login first")
    st.stop()

if user["role"] not in {"admin", "developer"}:
    st.error("Only admin or developer can access audit logs")
    st.stop()

client = APIClient(st.session_state.get("cookie", {}))
response = run(client.request("GET", "/api/v1/audit"))
if response.status_code == 200:
    st.dataframe(response.json(), use_container_width=True)
else:
    st.error(response.text)
