"""Streamlit app entrypoint."""

import streamlit as st

from utils.auth import login, run

st.set_page_config(page_title="NLDB Gateway", layout="wide")

st.title("Natural Language Database Gateway")

if "user" not in st.session_state:
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, msg = run(login(email, password))
        if ok:
            st.success("Logged in")
            st.rerun()
        else:
            st.error(msg)
else:
    user = st.session_state["user"]
    st.success(f"Logged in as {user['email']} ({user['role']})")
    st.info("Use left sidebar pages: Query / Approvals / Audit")
