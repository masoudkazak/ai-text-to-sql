import streamlit as st

from utils.auth import _load_persisted_access_token, demo_login, login, logout, register, restore_session, run
from utils.ui import render_usage_header

st.set_page_config(page_title="NLDB Gateway", layout="wide")

st.title("Natural Language Database Gateway")

if "user" not in st.session_state:
    token = _load_persisted_access_token()
    if token:
        ok, _ = run(restore_session())
        if ok:
            st.rerun()

if "user" not in st.session_state:
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 Try Demo", key="demo_button", use_container_width=True):
            ok, msg = run(demo_login())
            if ok:
                st.success("Demo account created and logged in!")
                st.rerun()
            else:
                st.error(f"Demo login failed: {msg}")
    
    st.divider()

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
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🚪 Logout", key="logout_button", use_container_width=True):
            run(logout())
            st.success("Logged out!")
            st.rerun()
    
    st.success(f"Logged in as {user['email']} ({user['role']})")
    render_usage_header()
    st.info("Use left sidebar pages: Query / Approvals / Audit")
