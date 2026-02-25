import streamlit as st

from utils.api_client import APIClient
from utils.auth import _load_persisted_access_token, restore_session, run
from utils.ui import handle_api_response, redirect_to_register, render_usage_header

st.title("Approvals")

if "user" not in st.session_state:
    token = _load_persisted_access_token()
    if token:
        run(restore_session())

user = st.session_state.get("user")
if not user:
    redirect_to_register()

render_usage_header()

if user["role"] != "admin":
    st.error("Only admin can access approvals")
    st.stop()

client = APIClient(st.session_state.get("cookie", {}))
resp = run(client.request("GET", "/api/v1/approvals/pending"))

if not handle_api_response(resp, "Failed to fetch approval requests"):
    st.stop()

pending = resp.json()
if not pending:
    st.info("No pending approvals")
else:
    for row in pending:
        st.write(f"Query Request ID: {row['query_request_id']} | status={row['status']}")
        approve = st.button(f"Approve #{row['query_request_id']}")
        reject = st.button(f"Reject #{row['query_request_id']}")

        if approve or reject:
            dec = run(
                client.request(
                    "POST",
                    "/api/v1/approvals/decision",
                    json={"query_request_id": row["query_request_id"], "approve": bool(approve), "comment": "Reviewed from Streamlit"},
                )
            )
            if handle_api_response(dec, "Failed to save decision"):
                st.success("Decision saved")
                st.rerun()
