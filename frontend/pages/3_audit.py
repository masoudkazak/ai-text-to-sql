import streamlit as st

from utils.api_client import APIClient
from utils.auth import _load_persisted_access_token, restore_session, run
from utils.ui import handle_api_response, redirect_to_register, render_usage_header

st.title("Audit Logs")

if "user" not in st.session_state:
    token = _load_persisted_access_token()
    if token:
        run(restore_session())

user = st.session_state.get("user")
if not user:
    redirect_to_register()

render_usage_header()

if user["role"] not in {"admin", "developer"}:
    st.error("Only admin or developer can access audit logs")
    st.stop()

client = APIClient(st.session_state.get("cookie", {}))
response = run(client.request("GET", "/api/v1/audit"))
if handle_api_response(response, "Failed to fetch audit logs"):
    st.dataframe(response.json(), use_container_width=True)
