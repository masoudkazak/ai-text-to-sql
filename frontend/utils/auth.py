"""Authentication helpers for Streamlit session."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import extra_streamlit_components as stx
import streamlit as st

from utils.api_client import APIClient

# Global cookie manager instance
_cookie_manager_instance = None


def _get_cookie_manager() -> stx.CookieManager:
    global _cookie_manager_instance
    if _cookie_manager_instance is None:
        _cookie_manager_instance = stx.CookieManager()
    return _cookie_manager_instance


def _persist_access_token(token: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    _get_cookie_manager().set("nldb_access_token", token, expires_at=expires_at)


def _load_persisted_access_token() -> str | None:
    token = _get_cookie_manager().get("nldb_access_token")
    return token


def _clear_persisted_access_token() -> None:
    _get_cookie_manager().delete("nldb_access_token")


async def login(email: str, password: str) -> tuple[bool, str]:
    client = APIClient()
    response = await client.request("POST", "/api/v1/auth/login", json={"email": email, "password": password})

    if response.status_code != 200:
        return False, response.text

    cookie = response.cookies.get("access_token")
    if cookie:
        st.session_state["cookie"] = {"access_token": cookie}
        _persist_access_token(cookie)
        st.session_state["user"] = response.json()
        return True, "ok"
    return False, "No cookie returned"


async def register(name: str, email: str, password: str) -> tuple[bool, str]:
    client = APIClient()
    response = await client.request("POST", "/api/v1/auth/register", json={"name": name, "email": email, "password": password})

    if response.status_code != 201:
        return False, response.text

    cookie = response.cookies.get("access_token")
    if cookie:
        st.session_state["cookie"] = {"access_token": cookie}
        _persist_access_token(cookie)
        st.session_state["user"] = response.json()
        return True, "ok"
    return False, "No cookie returned"


async def fetch_me() -> tuple[bool, dict]:
    cookies = st.session_state.get("cookie", {})
    response = await APIClient(cookies).request("GET", "/api/v1/auth/me")
    if response.status_code == 200:
        user = response.json()
        st.session_state["user"] = user
        return True, user
    return False, {}


async def logout() -> None:
    cookies = st.session_state.get("cookie", {})
    await APIClient(cookies).request("POST", "/api/v1/auth/logout")
    st.session_state.pop("cookie", None)
    st.session_state.pop("user", None)
    _clear_persisted_access_token()


async def fetch_usage_summary() -> tuple[bool, dict]:
    cookies = st.session_state.get("cookie", {})
    response = await APIClient(cookies).request("GET", "/api/v1/auth/usage-summary")
    if response.status_code == 200:
        return True, response.json()
    return False, {}


async def restore_session() -> tuple[bool, dict]:
    """Restore session from persisted token."""
    token = _load_persisted_access_token()
    if not token:
        st.session_state.pop("cookie", None)
        st.session_state.pop("user", None)
        return False, {}

    # Set cookie in session state for API calls
    st.session_state["cookie"] = {"access_token": token}
    
    try:
        response = await APIClient(st.session_state["cookie"]).request("GET", "/api/v1/auth/me")
        if response.status_code == 200:
            user = response.json()
            st.session_state["user"] = user
            return True, user
    except Exception:
        pass
    
    # Token is invalid, clear everything
    st.session_state.pop("cookie", None)
    st.session_state.pop("user", None)
    _clear_persisted_access_token()
    return False, {}


def init_auth_session() -> None:
    """Initialize authentication session on app load - restore from persistent cookies."""
    if "user" not in st.session_state:
        token = _load_persisted_access_token()
        if token:
            st.session_state["cookie"] = {"access_token": token}
            # Try to restore user immediately
            import asyncio
            try:
                success, user = asyncio.run(restore_session())
            except:
                pass


def run(coro):
    return asyncio.run(coro)


def check_token_validity() -> bool:
    """Check if token is still valid with backend."""
    token = _load_persisted_access_token()
    if not token:
        return False
    
    try:
        response = asyncio.run(
            APIClient({"access_token": token}).request("GET", "/api/v1/auth/me")
        )
        return response.status_code == 200
    except:
        return False
