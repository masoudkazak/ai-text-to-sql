"""Public register page."""

import streamlit as st

from utils.auth import _load_persisted_access_token, register, restore_session, run

st.title("Register (Viewer)")

# Check if user is authenticated
if "user" not in st.session_state:
    # Try to restore from persisted token
    token = _load_persisted_access_token()
    if token:
        ok, _ = run(restore_session())
        if ok:
            st.rerun()

if st.session_state.get("user"):
    st.success("You are already logged in.")
    st.stop()

name = st.text_input("Name")
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Create Account"):
    ok, msg = run(register(name, email, password))
    if ok:
        st.success("Account created and logged in")
        if hasattr(st, "switch_page"):
            st.switch_page("app.py")
        st.rerun()
    else:
        st.error(msg)
