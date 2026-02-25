import streamlit as st

from utils.api_client import APIClient
from utils.auth import _load_persisted_access_token, restore_session, run
from utils.ui import handle_api_response, redirect_to_register, render_usage_header

st.title("Users (Admin)")

if "user" not in st.session_state:
    token = _load_persisted_access_token()
    if token:
        run(restore_session())

user = st.session_state.get("user")
if not user:
    redirect_to_register()

render_usage_header()

if user["role"] != "admin":
    st.error("Only admin can access users management")
    st.stop()

client = APIClient(st.session_state.get("cookie", {}))

st.subheader("Create User")
with st.form("create_user_form", clear_on_submit=True):
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    role = st.selectbox(
        "Role",
        options=["viewer", "analyst", "developer", "restricted", "admin"],
        index=0,
    )
    daily_query_limit = st.number_input("Daily Query Limit", min_value=0, value=100, step=1)
    allowed_tables_raw = st.text_input("Allowed Tables (comma separated)")

    submit = st.form_submit_button("Create User")
    if submit:
        payload = {
            "name": name.strip(),
            "email": email.strip(),
            "password": password,
            "role": role,
            "daily_query_limit": int(daily_query_limit),
            "allowed_tables": [t.strip() for t in allowed_tables_raw.split(",") if t.strip()],
        }
        create_resp = run(client.request("POST", "/api/v1/users", json=payload))
        if handle_api_response(create_resp, "Failed to create user"):
            st.success("User created successfully")

st.divider()
st.subheader("Users List")
users_resp = run(client.request("GET", "/api/v1/users"))
if handle_api_response(users_resp, "Failed to fetch users list"):
    users = users_resp.json()
    if users:
        st.dataframe(users, use_container_width=True)
    else:
        st.info("No users found")
