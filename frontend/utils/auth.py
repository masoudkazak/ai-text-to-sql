"""Authentication helpers for Streamlit session."""

from __future__ import annotations

import asyncio

import streamlit as st

from utils.api_client import APIClient


async def login(email: str, password: str) -> tuple[bool, str]:
    client = APIClient()
    response = await client.request("POST", "/api/v1/auth/login", json={"email": email, "password": password})

    if response.status_code != 200:
        return False, response.text

    cookie = response.cookies.get("access_token")
    if cookie:
        st.session_state["cookie"] = {"access_token": cookie}
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


def run(coro):
    return asyncio.run(coro)
