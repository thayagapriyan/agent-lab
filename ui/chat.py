"""Streamlit chat GUI for Agent Memory Lab — the easy way to *see* memory working.

Why this exists: the CLI (`agent.serve`) builds a fresh agent per prompt, so it can't
show a conversation. This UI keeps ONE Agent alive across many turns (in
st.session_state), which is what makes both memory layers visible:

* short-term — recall within this conversation (works even with memory OFF), and
* long-term  — recall across sessions/restarts for the same actor (needs memory ON).

Identity-first UX: you're asked for an **actor id** before chatting, because that's
*who* the memories belong to (namespace `semantic/{actorId}`). A real app would pass
the logged-in user's id here; if you don't have one, the UI offers a generated id so
you can still try it. Reusing the same actor id later recalls what was stored before.

Run:  streamlit run ui/chat.py
"""

from __future__ import annotations

import os
import uuid

import streamlit as st

from agent.config import load_config, MemoryConfig
from agent.core import build_agent
from memory.factory import close_session_manager

st.set_page_config(page_title="Agent Memory Lab — Chat", page_icon="🧠")


def _suggested_actor_id() -> str:
    return f"actor-{uuid.uuid4().hex[:8]}"


def _reset_chat() -> None:
    """Tear down the current agent (flushing memory) and clear the conversation."""
    agent = st.session_state.get("agent")
    if agent is not None:
        close_session_manager(getattr(agent, "memory_session_manager", None))
    for key in ("agent", "messages", "actor_id", "session_id", "memory_enabled"):
        st.session_state.pop(key, None)


# ── Gate screen: identify the actor before chatting ───────────────────────────
if "agent" not in st.session_state:
    st.title("🧠 Agent Memory Lab")
    st.caption(
        "Chat with a Strands agent backed by AgentCore Memory. First, tell me **who "
        "you are** — memories are stored per *actor* (user), so the agent can recall "
        "your facts in a later conversation."
    )

    with st.form("identify"):
        actor_id = st.text_input(
            "Actor id (who are you?)",
            value=_suggested_actor_id(),
            help="A stable id for the user — e.g. an email, a username, or a customer id. "
            "Reuse the SAME id across visits to recall earlier facts. The pre-filled "
            "value is a throwaway id for quick testing.",
        )
        memory_enabled = st.toggle(
            "Memory ON",
            value=True,
            help="OFF runs the no-memory baseline (the control): only short-term, "
            "in-conversation recall — nothing persists across sessions.",
        )
        start = st.form_submit_button("Start chatting", type="primary")

    if start:
        if not actor_id.strip():
            st.error("Please enter an actor id (or keep the generated one).")
            st.stop()

        cfg = load_config()
        mem_cfg = MemoryConfig(
            memory_id=os.getenv("MEMORY_ID", ""),
            namespace=os.getenv("MEMORY_NAMESPACE", "semantic/{actorId}"),
            actor_id=actor_id.strip(),
            session_id=f"session-{uuid.uuid4().hex[:8]}",
            enabled=memory_enabled,
        )
        try:
            agent = build_agent(config=cfg, memory_config=mem_cfg)
        except Exception as exc:  # surface creds/MEMORY_ID problems clearly
            st.error(f"Could not start the agent: {exc}")
            st.stop()

        st.session_state.agent = agent
        st.session_state.messages = []
        st.session_state.actor_id = mem_cfg.actor_id
        st.session_state.session_id = mem_cfg.session_id
        st.session_state.memory_enabled = memory_enabled
        st.rerun()

    st.stop()


# ── Chat screen ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Session")
    st.write(f"**Actor:** `{st.session_state.actor_id}`")
    st.write(f"**Session:** `{st.session_state.session_id}`")
    st.write("**Memory:** " + ("🟢 ON (long-term)" if st.session_state.memory_enabled else "⚪ OFF (baseline)"))
    st.caption(
        "Reuse the same **actor** id in a new session to test long-term recall across "
        "conversations. Click below to start over as a different actor."
    )
    if st.button("New actor / reset"):
        _reset_chat()
        st.rerun()

st.title("🧠 Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Say something — try teaching a fact, then ask about it later"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                # Same Agent instance across turns → short-term memory; plus long-term
                # if memory is ON. This is the whole reason the GUI beats the CLI.
                reply = str(st.session_state.agent(prompt))
            except Exception as exc:
                reply = f"⚠️ error: {exc}"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
