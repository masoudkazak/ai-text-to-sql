import streamlit as st

from utils.auth import _load_persisted_access_token, check_token_validity, fetch_usage_summary, restore_session, run


def ensure_authenticated() -> bool:
    if st.session_state.get("user"):
        return True

    token = _load_persisted_access_token()
    if token:
        ok, _ = run(restore_session())
        return ok
    
    return False


def handle_api_response(response, error_message: str = "Request failed") -> bool:
    if 200 <= response.status_code < 300:
        return True
    
    if response.status_code in [401, 403]:
        st.session_state.pop("user", None)
        st.session_state.pop("cookie", None)
        st.error("Your session has expired. Please log in again.")
        st.balloons()
        st.switch_page("pages/0_register.py")
        return False
     
    st.error(f"{error_message}: {response.text}")
    return False


def redirect_to_register() -> None:
    if ensure_authenticated():
        return
    if hasattr(st, "switch_page"):
        st.switch_page("pages/0_register.py")
    st.warning("Please register/login first from Register page")
    st.stop()


def render_usage_header() -> None:
    user = st.session_state.get("user")
    if not user:
        return

    ok, payload = run(fetch_usage_summary())
    if not ok:
        if not ensure_authenticated():
            st.session_state.pop("user", None)
            st.session_state.pop("cookie", None)
            st.rerun()
        return

    c1, c2 = st.columns(2)
    c1.metric(
        "Global Remaining (Start: 50)",
        f"{payload['global_remaining']} / {payload['global_daily_limit']}",
        help=f"Used today: {payload['global_used']}",
    )
    c2.metric(
        "Your Remaining",
        f"{payload['user_remaining']} / {payload['user_daily_limit']}",
        help=f"Used today: {payload['user_used']}",
    )

    tables = payload.get("available_tables", [])
    st.caption("Available tables (excluding blacklisted):")
    st.code(", ".join(tables) if tables else "-", language="text")
