"""Approvals page for admin."""

import streamlit as st

from utils.api_client import APIClient
from utils.auth import run

st.title("Approvals")

user = st.session_state.get("user")
if not user:
    st.warning("Please login first")
    st.stop()

if user["role"] != "admin":
    st.error("Only admin can access approvals")
    st.stop()

client = APIClient(st.session_state.get("cookie", {}))
resp = run(client.request("GET", "/api/v1/approvals/pending"))

if resp.status_code != 200:
    st.error(resp.text)
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
            if dec.status_code == 200:
                st.success("Decision saved")
                st.rerun()
            else:
                st.error(dec.text)
