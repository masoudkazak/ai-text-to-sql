import streamlit as st

from utils.api_client import APIClient
from utils.auth import _load_persisted_access_token, restore_session, run
from utils.ui import handle_api_response, redirect_to_register, render_usage_header

st.title("Query")

if "user" not in st.session_state:
    token = _load_persisted_access_token()
    if token:
        run(restore_session())

user = st.session_state.get("user")
if not user:
    redirect_to_register()

render_usage_header()

text = st.text_area("Natural language request", height=180)

if st.button("Submit Query") and text.strip():
    client = APIClient(st.session_state.get("cookie", {}))
    response = run(client.request("POST", "/api/v1/query", json={"text": text}))

    if handle_api_response(response, "Failed to submit request"):
        data = response.json()
        st.code(data["generated_sql"], language="sql")

        decision = data["governance"]["decision"]
        if decision == "APPROVED":
            st.success(f"Decision: {decision}")
        elif decision == "REQUIRES_APPROVAL":
            st.warning("Decision: REQUIRES_APPROVAL (pending approval)")
        else:
            st.error("Decision: DENIED")

        if data.get("result"):
            st.dataframe(data["result"], use_container_width=True)

st.divider()
st.subheader("Check Existing Request")
request_id = st.number_input("Query Request ID", min_value=1, step=1)
if st.button("Check Status / Fetch Result"):
    client = APIClient(st.session_state.get("cookie", {}))
    response = run(client.request("GET", f"/api/v1/query/{int(request_id)}"))
    if handle_api_response(response, "Failed to fetch request"):
        data = response.json()
        st.write(f"Status: {data['status']}")
        st.code(data["generated_sql"], language="sql")
        if data.get("result") is not None:
            st.dataframe(data["result"], use_container_width=True)
