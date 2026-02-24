"""Streamlit app entrypoint."""

import streamlit as st

from utils.auth import _load_persisted_access_token, login, register, restore_session, run
from utils.ui import render_usage_header

st.set_page_config(page_title="NLDB Gateway", layout="wide")

st.title("Natural Language Database Gateway")

# Check if user is authenticated
if "user" not in st.session_state:
    # Try to restore from persisted token
    token = _load_persisted_access_token()
    if token:
        ok, _ = run(restore_session())
        if ok:
            st.rerun()

if "user" not in st.session_state:
    login_tab, register_tab = st.tabs(["Login", "Register (Viewer only)"])

    with login_tab:
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

    with register_tab:
        st.subheader("Register")
        name = st.text_input("Name")
        reg_email = st.text_input("Register Email")
        reg_password = st.text_input("Register Password", type="password")

        if st.button("Create Viewer Account"):
            ok, msg = run(register(name, reg_email, reg_password))
            if ok:
                st.success("Account created and logged in")
                st.rerun()
            else:
                st.error(msg)
else:
    user = st.session_state["user"]
    st.success(f"Logged in as {user['email']} ({user['role']})")
    render_usage_header()
    st.info("Use left sidebar pages: Query / Approvals / Audit")
