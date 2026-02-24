import streamlit as st

from utils.auth import _load_persisted_access_token, check_token_validity, fetch_usage_summary, restore_session, run


def ensure_authenticated() -> bool:
    """Check if user is authenticated, restore from cookies if needed."""
    # First check if user is in session state
    if st.session_state.get("user"):
        return True
    
    # If not, try to restore from persisted token
    token = _load_persisted_access_token()
    if token:
        ok, _ = run(restore_session())
        return ok
    
    return False


def handle_api_response(response, error_message: str = "درخواست ناموفق") -> bool:
    """Handle API response and redirect to login if token is expired."""
    if response.status_code == 200:
        return True
    
    # Check if it's an authentication error
    if response.status_code in [401, 403]:
        st.session_state.pop("user", None)
        st.session_state.pop("cookie", None)
        st.error("نشست شما منقضی شده است. لطفا دوباره وارد شوید.")
        st.balloons()
        st.switch_page("pages/0_register.py")
        return False
    
    # Other errors
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
        # Token might be expired, try to restore
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
