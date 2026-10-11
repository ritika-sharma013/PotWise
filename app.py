"""PotWise Streamlit application entry point."""

from __future__ import annotations

import hashlib
import base64
import sqlite3
from contextlib import nullcontext
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from core.identify import (
    IdentificationError,
    OllamaModelError,
    OllamaUnavailableError,
)
from core.ai_provider import GeminiProviderError, chat_with_provider, identify_plant_with_provider
from core.plant_data import get_plant_by_id, get_supported_plants
from core.assistant import AssistantResponseError
from core.problem_data import ProblemDataError, get_problems_for_plant, load_problem_data
from core.soil import calculate_soil_mix
from core.voice import get_last_voice_error, speech_to_text, text_to_speech
from core.mic_recorder import record_microphone
from core.chat_history import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversation_messages,
    list_recent_conversations,
    rename_conversation,
    save_message,
    update_conversation,
)
from core.pots import (
    delete_pot,
    list_saved_pots,
    save_pot,
)


def main() -> None:
    st.set_page_config(page_title="PotWise", page_icon="🌿", layout="centered")
    st.session_state.setdefault("anonymous_session_id", uuid4().hex)
    _session_database_path()
    st.markdown(
        """
        <style>
        :root {
            --pw-background: #F3EBDD;
            --pw-sidebar: #EAE0CC;
            --pw-surface: #DCE5D5;
            --pw-card: #FFFDF7;
            --pw-border: #D6CCB8;
            --pw-primary: #123F2A;
            --pw-green: #0B5A3C;
            --pw-green-hover: #2F7654;
            --pw-sage: #A8B89A;
            --pw-beige: #E6D8BE;
            --pw-cream: #FFFDF7;
            --pw-text: #2F4A3A;
            --pw-muted: #5F6B61;
        }

        /* =====================================================
           POTWISE UI / UX THEME
           ===================================================== */

        .stApp,
        [data-testid="stAppViewContainer"] {
            background: var(--pw-background);
            color: var(--pw-text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.5;
        }

        html,
        body {
            background: var(--pw-background);
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 760px;
            padding-top: 2.25rem;
            padding-bottom: 3.25rem;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: var(--pw-sidebar);
            border-right: 1px solid var(--pw-border);
        }

        [data-testid="stSidebarContent"] {
            padding: 1.65rem 1.1rem;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--pw-primary);
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button {
            background: transparent;
            color: var(--pw-primary);
            border-color: transparent;
            text-align: left;
            min-height: 2.3rem;
            padding: 0.45rem 0.6rem;
            font-size: 0.92rem;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] {
            margin-bottom: 0.2rem;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
            background: var(--pw-sage);
            color: var(--pw-primary);
            border-color: var(--pw-sage);
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
            background: var(--pw-green);
            color: var(--pw-cream);
            border-color: var(--pw-green);
            text-align: center;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"]:hover {
            background: var(--pw-green-hover);
            color: var(--pw-cream);
            border-color: var(--pw-green-hover);
        }

        h1, h2, h3, h4, h5, h6,
        [data-testid="stMarkdownContainer"] p,
        label {
            color: var(--pw-primary);
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        [data-testid="stMarkdownContainer"] p {
            color: var(--pw-text);
        }

        [data-testid="stAppViewContainer"] h2 {
            margin-top: 2rem;
            margin-bottom: 0.75rem;
            font-weight: 700;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--pw-muted);
        }

        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: var(--pw-primary);
        }

        .pw-hero {
            margin-bottom: 1.9rem;
            padding-top: 0.15rem;
        }

        .pw-hero-title {
            margin: 0;
            color: var(--pw-primary);
            font-size: 2.25rem;
            font-weight: 700;
            letter-spacing: -0.04em;
            line-height: 1.05;
        }

        .pw-hero-subtitle {
            margin: 0.6rem 0 0;
            color: var(--pw-primary);
            font-size: 0.98rem;
            font-weight: 500;
            letter-spacing: 0.01em;
        }

        a {
            color: var(--pw-green);
        }

        [data-testid="stButton"] > button,
        [data-testid="stFormSubmitButton"] > button {
            background: var(--pw-green);
            color: var(--pw-cream) !important;
            border: 1px solid var(--pw-green);
            border-radius: 0.45rem;
            box-shadow: none;
        }

        [data-testid="stButton"] > button p,
        [data-testid="stButton"] > button span,
        [data-testid="stFormSubmitButton"] > button p,
        [data-testid="stFormSubmitButton"] > button span {
            color: var(--pw-cream) !important;
            font-weight: 600;
        }

        [data-testid="stButton"] > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: var(--pw-green);
            color: var(--pw-cream);
            border: 1px solid var(--pw-green);
        }

        [data-testid="stButton"] > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            background: var(--pw-green-hover);
            border-color: var(--pw-green-hover);
            color: var(--pw-cream);
        }

        [data-testid="stButton"] > button:focus-visible,
        [data-testid="stFormSubmitButton"] > button:focus-visible {
            outline: 2px solid var(--pw-sage);
            outline-offset: 2px;
            box-shadow: none;
        }

        [data-testid="stButton"] > button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: var(--pw-green-hover);
            border-color: var(--pw-green-hover);
            color: var(--pw-cream);
        }

        [data-testid="stFileUploader"] {
            background: var(--pw-cream);
            border: 1px solid var(--pw-border);
            border-radius: 0.65rem;
            padding: 0.7rem;
            margin-bottom: 1rem;
        }

        [data-testid="stFileUploader"] > section {
            background: transparent;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: transparent;
            border: 0;
            color: var(--pw-primary);
        }

        [data-testid="stFileUploaderDropzone"] button {
            background: var(--pw-green);
            border-color: var(--pw-green);
            color: var(--pw-cream) !important;
            font-weight: 600;
        }

        [data-testid="stFileUploaderDropzone"] button * {
            color: var(--pw-cream) !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-baseweb="select"] > div {
            background: var(--pw-cream);
            color: var(--pw-text);
            border-color: var(--pw-border);
            border-radius: 0.45rem;
            font-size: 0.95rem;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stNumberInput"] input:focus {
            border-color: var(--pw-green);
            box-shadow: 0 0 0 1px var(--pw-green);
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stNumberInput"] input::placeholder {
            color: var(--pw-muted);
            opacity: 1;
        }

        [data-testid="stAlert"] {
            background: #DCE5D5;
            border: 1px solid var(--pw-sage);
            border-radius: 0.55rem;
            color: var(--pw-text);
        }

        [data-testid="stAlert"] p,
        [data-testid="stAlert"] svg {
            color: var(--pw-primary);
            fill: var(--pw-primary);
        }

        [data-testid="stAlert"] p {
            font-weight: 500;
        }

        [data-testid="stExpander"] {
            background: var(--pw-card);
            border: 1px solid var(--pw-border);
            border-radius: 0.55rem;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p {
            color: var(--pw-primary);
        }

        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"],
        [role="option"] {
            background: var(--pw-cream);
            color: var(--pw-primary);
        }

        [role="option"]:hover,
        [role="option"][aria-selected="true"] {
            background: var(--pw-sage);
            color: var(--pw-primary);
        }

        [data-testid="stSpinner"] {
            color: var(--pw-green);
        }

        [data-testid="stChatMessage"] p {
            color: var(--pw-text);
        }

        /* Streamlit renders assistant Markdown headings/lists as separate elements. */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {
            color: var(--pw-text) !important;
            opacity: 1 !important;
        }

        [data-testid="stSpinner"] p {
            color: var(--pw-primary);
            font-weight: 600;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button:not([kind="primary"]) {
            background: transparent !important;
            color: var(--pw-primary) !important;
            border-color: transparent !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button:not([kind="primary"]) p,
        [data-testid="stSidebar"] [data-testid="stButton"] > button:not([kind="primary"]) span {
            color: var(--pw-primary) !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"],
        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] p,
        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] span {
            background: var(--pw-green) !important;
            color: var(--pw-cream) !important;
            border-color: var(--pw-green) !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button:not([kind="primary"]):hover {
            background: var(--pw-sage) !important;
            color: var(--pw-primary) !important;
            border-color: var(--pw-sage) !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"]:hover {
            background: var(--pw-green-hover) !important;
            color: var(--pw-cream) !important;
            border-color: var(--pw-green-hover) !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] > button[aria-pressed="true"] {
            background: var(--pw-sage) !important;
            color: var(--pw-primary) !important;
            border: 1px solid var(--pw-green) !important;
        }

        [data-testid="stSidebar"] [class*="st-key-plantwise-chat-"] {
            border: 1px solid var(--pw-green);
            border-radius: 0.5rem;
            padding: 0.15rem 0.25rem;
        }

        /* Keep Streamlit's collapse-button hover styling intact. */
        [data-testid="stSidebarCollapseButton"]:not(:hover),
        [data-testid="stSidebarCollapseButton"] button:not(:hover),
        button[data-testid="stSidebarCollapseButton"]:not(:hover),
        button[aria-label="Close sidebar"]:not(:hover),
        button[aria-label="Open sidebar"]:not(:hover) {
            background: var(--pw-green) !important;
            color: var(--pw-cream) !important;
            border: 1px solid var(--pw-green) !important;
            border-radius: 0.45rem;
        }

        [data-testid="stSidebarCollapseButton"]:not(:hover) svg,
        [data-testid="stSidebarCollapseButton"] button:not(:hover) svg,
        button[data-testid="stSidebarCollapseButton"]:not(:hover) svg,
        button[aria-label="Close sidebar"]:not(:hover) svg,
        button[aria-label="Open sidebar"]:not(:hover) svg {
            color: var(--pw-cream) !important;
            fill: var(--pw-cream) !important;
            stroke: var(--pw-cream) !important;
        }

        [data-testid="stChatMessage"] {
            background: var(--pw-card);
            border: 1px solid var(--pw-border);
            border-radius: 0.55rem;
            padding: 0.9rem 1rem;
            margin-bottom: 0.55rem;
        }

        [data-testid="stChatMessage"][data-message-author-role="user"] {
            background: var(--pw-green);
            border-color: var(--pw-green);
        }

        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] h4,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stChatMessage"][data-message-author-role="user"] [data-testid="stMarkdownContainer"] strong {
            color: var(--pw-cream) !important;
            opacity: 1 !important;
        }

        [data-testid="stChatMessage"][data-message-author-role="assistant"] {
            border-left: 3px solid var(--pw-green);
        }

        [data-testid="stTextArea"] textarea {
            line-height: 1.5;
        }

        [data-testid="stRadio"] label,
        [data-testid="stToggle"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stSelectbox"] label {
            color: var(--pw-primary);
            font-weight: 600;
        }

        [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
            background: var(--pw-green);
            border-color: var(--pw-green);
        }

        [data-testid="stToggle"] [data-checked="true"] {
            background: var(--pw-green);
        }

        [data-testid="stFileUploader"],
        [data-testid="stAlert"],
        [data-testid="stExpander"],
        [data-testid="stChatMessage"] {
            border-color: rgba(11, 90, 60, 0.28);
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-"] {
            margin: 0.35rem 0;
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-"] [data-testid="stCaptionContainer"] {
            color: var(--pw-muted);
            font-size: 0.78rem;
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"],
        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"] > button {
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
            height: 36px !important;
            min-height: 36px !important;
            max-height: 36px !important;
            flex: 0 0 36px !important;
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"] > button {
            padding: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"] > button:not(:hover) {
            background: var(--pw-green) !important;
            color: var(--pw-cream) !important;
            border-color: var(--pw-green) !important;
        }

        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"] > button:not(:hover) p,
        [data-testid="stSidebar"] [class*="st-key-my-pot-delete-"] [data-testid="stButton"] > button:not(:hover) span {
            color: var(--pw-cream) !important;
            margin: 0;
            font-size: 1.05rem !important;
            line-height: 1;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="pw-hero">
            <div class="pw-hero-title">🌿&nbsp; PotWise</div>
            <div class="pw-hero-subtitle">Not sure what your plant needs? Just ask PotWise.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_recent_chats()
    st.header("Identify a plant")
    upload_widget_key = st.session_state.setdefault(
        "plant_upload_widget_key",
        "plant_upload_initial",
    )
    uploaded_image = st.file_uploader(
        "Upload a plant photo",
        type=["jpg", "jpeg", "png", "webp"],
        help="The image is sent only to your local Ollama instance.",
        key=upload_widget_key,
    )
    if uploaded_image is None:
        if st.session_state.get("open_history_conversation"):
            _render_open_conversation()
            return
        st.info("Upload a photo to begin.")
        return

    image_bytes = uploaded_image.getvalue()
    st.image(image_bytes, caption=uploaded_image.name, use_container_width=True)
    image_signature = hashlib.sha256(image_bytes).hexdigest()
    if st.session_state.get("identification_image_signature") != image_signature:
        current_id = st.session_state.get("current_conversation_id")
        current_conversation = None
        if (
            isinstance(current_id, str)
            and st.session_state.get("identification_image_signature") is None
        ):
            try:
                current_conversation = get_conversation(
                    current_id,
                    database_path=_session_database_path(),
                )
            except sqlite3.Error:
                st.error("Could not load the current chat right now.")
                return

        is_blank_current_conversation = bool(
            isinstance(current_conversation, dict)
            and not current_conversation.get("plant_id")
            and not current_conversation.get("plant_name")
        )
        if not is_blank_current_conversation:
            try:
                st.session_state.current_conversation_id = create_conversation(
                    database_path=_session_database_path()
                )
            except sqlite3.Error:
                st.error("Could not create a new chat right now.")
                return
        st.session_state.open_history_conversation = False
        st.session_state.identification_image_signature = image_signature
        st.session_state.pop("identification", None)
        st.session_state.pop("manual_selection_requested", None)
        st.session_state.pop("confirmed_plant_id", None)
        st.session_state.pop("confirmed_plant_name", None)
        st.session_state.pop("confirmed_plant", None)
        st.session_state.pop("plant_confirmed", None)
        st.session_state.pop("assistant_messages", None)
        st.session_state.pop("assistant_plant_id", None)
        st.session_state.pop("assistant_conversation_id", None)
        st.session_state.pop("assistant_mic_signature", None)
        st.session_state.pop("assistant_mic_recording_bytes", None)
        st.session_state.pop("assistant_mic_transcription_attempted", None)
        st.session_state.pop("assistant_mic_transcript", None)
        st.session_state.pop("assistant_mic_submitted_signature", None)

    if st.session_state.get("open_history_conversation"):
        _render_open_conversation()
        return

    if st.button("Identify with local Gemma", type="primary"):
        st.session_state.pop("confirmed_plant_id", None)
        st.session_state.pop("confirmed_plant_name", None)
        st.session_state.pop("confirmed_plant", None)
        st.session_state.pop("plant_confirmed", None)
        st.session_state.pop("assistant_messages", None)
        st.session_state.pop("assistant_plant_id", None)
        st.session_state.pop("assistant_conversation_id", None)
        st.session_state.pop("assistant_mic_signature", None)
        st.session_state.pop("assistant_mic_recording_bytes", None)
        st.session_state.pop("assistant_mic_transcription_attempted", None)
        st.session_state.pop("assistant_mic_transcript", None)
        st.session_state.pop("assistant_mic_submitted_signature", None)
        with st.spinner("Checking the image with local Ollama…"):
            try:
                st.session_state.identification = identify_plant_with_provider(image_bytes)
            except GeminiProviderError as exc:
                st.error(str(exc))
            except OllamaUnavailableError as exc:
                st.error(str(exc))
            except OllamaModelError as exc:
                st.error(str(exc))
            except IdentificationError as exc:
                st.error(str(exc))

    result = st.session_state.get("identification")
    if result is None:
        return

    st.subheader("Identification result")
    if result.status == "not_plant":
        st.warning("This doesn't appear to be a plant. Please upload a clear plant image.")
        return
    if result.status == "uncertain":
        st.warning("I couldn't confidently identify this plant. Try a clearer image.")
        _render_manual_selection()
        return

    st.success(f"Likely plant: {result.common_name}")
    if result.scientific_name:
        st.caption(f"Scientific name: {result.scientific_name}")
    if result.confidence is not None:
        st.caption(f"Confidence: {result.confidence:.0%}")
    if not result.plant_id:
        st.info("Care information is unavailable until you select a supported plant.")

    plant_confirmed = bool(
        st.session_state.get("plant_confirmed")
        or st.session_state.get("confirmed_plant_id")
    )
    if plant_confirmed:
        st.session_state.plant_confirmed = True
    if not plant_confirmed and not st.session_state.get("manual_selection_requested"):
        confirm_col, manual_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, this is my plant", key="confirm_identification"):
                st.session_state.confirmed_plant_id = result.plant_id
                st.session_state.confirmed_plant_name = result.common_name
                st.session_state.plant_confirmed = True
                st.rerun()
        with manual_col:
            if st.button("No, choose manually", key="choose_manual_plant"):
                st.session_state.manual_selection_requested = True
    if st.session_state.get("manual_selection_requested"):
        _render_manual_selection()
    else:
        _render_confirmed_profile()


def _session_database_path() -> Path:
    """Return the SQLite file isolated to this Streamlit browser session."""

    session_id = st.session_state.setdefault("anonymous_session_id", uuid4().hex)
    sessions_directory = Path(__file__).resolve().parent / "database" / "sessions"
    sessions_directory.mkdir(parents=True, exist_ok=True)
    return sessions_directory / f"potwise_{session_id}.sqlite3"


def _reset_assistant_view() -> None:
    for key in (
        "assistant_messages",
        "assistant_plant_id",
        "assistant_conversation_id",
        "assistant_audio_cache",
        "assistant_voice_targets",
        "assistant_voice_attempted",
        "assistant_voice_autoplayed",
        "assistant_mic_signature",
        "assistant_mic_recording_bytes",
        "assistant_mic_transcription_attempted",
        "assistant_mic_transcript",
        "assistant_mic_submitted_signature",
    ):
        st.session_state.pop(key, None)


def _reset_current_plant_state(previous_plant_id: str | None = None) -> None:
    """Clear the active plant/UI state without touching persistent history."""

    for key in (
        "identification",
        "identification_image_signature",
        "manual_selection_requested",
        "manual_plant_selection",
        "confirmed_plant_id",
        "confirmed_plant_name",
        "confirmed_plant",
        "plant_confirmed",
        "open_history_conversation",
    ):
        st.session_state.pop(key, None)

    if isinstance(previous_plant_id, str) and previous_plant_id:
        for prefix in ("soil_volume_", "assistant_mode_", "hands_free_"):
            st.session_state.pop(f"{prefix}{previous_plant_id}", None)
    _reset_assistant_view()


def _render_recent_chats() -> None:
    try:
        conversations = list_recent_conversations(
            database_path=_session_database_path()
        )
    except sqlite3.Error:
        conversations = []

    with st.sidebar:
        st.subheader("Recent Chats")
        if st.button(
            "+ New Chat",
            key="new_chat_button",
            use_container_width=True,
            type="primary",
        ):
            previous_plant_id = st.session_state.get("confirmed_plant_id")
            try:
                new_conversation_id = create_conversation(
                    None,
                    None,
                    database_path=_session_database_path(),
                )
            except sqlite3.Error:
                st.error("Could not create a new chat right now.")
            else:
                st.session_state.current_conversation_id = new_conversation_id
                previous_upload_key = st.session_state.get("plant_upload_widget_key")
                if isinstance(previous_upload_key, str):
                    st.session_state.pop(previous_upload_key, None)
                st.session_state.plant_upload_widget_key = (
                    f"plant_upload_{new_conversation_id}"
                )
                _reset_current_plant_state(
                    previous_plant_id
                    if isinstance(previous_plant_id, str)
                    else None
                )
                st.session_state.open_history_conversation = False
                st.rerun()

        if not conversations:
            st.caption("No recent chats yet.")
            _render_my_pots()
            return
        for conversation in conversations[:20]:
            conversation_id = str(conversation["id"])
            plant_name = conversation.get("plant_name") or "PlantWise Chat"
            title = conversation.get("title") or f"🌱 {plant_name}"
            row_context = (
                st.container(key=f"plantwise-chat-{conversation_id}")
                if plant_name == "PlantWise Chat" and not conversation.get("plant_id")
                else nullcontext()
            )
            with row_context:
                chat_col, delete_col = st.columns([0.78, 0.22], gap="small")
                with chat_col:
                    if st.button(
                        f"🌱 {plant_name}",
                        key=f"recent_chat_{conversation_id}",
                        use_container_width=True,
                    ):
                        st.session_state.current_conversation_id = conversation_id
                        st.session_state.open_history_conversation = True
                        if conversation.get("plant_id"):
                            st.session_state.confirmed_plant_id = conversation["plant_id"]
                            st.session_state.confirmed_plant_name = plant_name
                            st.session_state.plant_confirmed = True
                        _reset_assistant_view()
                        st.rerun()
                with delete_col:
                    if st.button(
                        "🗑️",
                        key=f"delete_recent_chat_{conversation_id}",
                        help="Delete this chat",
                        use_container_width=True,
                    ):
                        try:
                            delete_conversation(
                                conversation_id,
                                database_path=_session_database_path(),
                            )
                        except sqlite3.Error:
                            st.error("Could not delete this chat right now.")
                        else:
                            if st.session_state.get("current_conversation_id") == conversation_id:
                                st.session_state.pop("current_conversation_id", None)
                                st.session_state.open_history_conversation = False
                                st.session_state.pop("identification", None)
                                st.session_state.pop("identification_image_signature", None)
                                st.session_state.pop("manual_selection_requested", None)
                                st.session_state.pop("confirmed_plant_id", None)
                                st.session_state.pop("confirmed_plant_name", None)
                                st.session_state.pop("confirmed_plant", None)
                                st.session_state.pop("plant_confirmed", None)
                                _reset_assistant_view()
                            st.rerun()

        _render_my_pots()


def _render_open_conversation() -> None:
    conversation_id = st.session_state.get("current_conversation_id")
    if not isinstance(conversation_id, str):
        st.info("Choose a recent chat or upload a plant image to begin.")
        return
    try:
        conversation = get_conversation(
            conversation_id,
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.error("Chat history is unavailable right now.")
        return
    if not conversation or not conversation.get("plant_id"):
        st.info("This chat will be ready after a plant is confirmed.")
        return
    plant_id = str(conversation["plant_id"])
    plant = get_plant_by_id(plant_id)
    if plant is None:
        st.info("The plant data for this chat is no longer available.")
        return
    st.session_state.confirmed_plant_id = plant_id
    st.session_state.confirmed_plant_name = str(plant.get("name") or plant_id)
    st.session_state.confirmed_plant = plant
    st.session_state.plant_confirmed = True
    _render_confirmed_profile()


def _render_manual_selection() -> None:
    plants = get_supported_plants()
    if not plants:
        st.info("No trusted plant records are available for manual selection yet.")
        return
    options = {str(plant.get("name", plant.get("id"))): plant for plant in plants}
    selected_name = st.selectbox("Choose the plant", list(options), key="manual_plant_selection")
    selected_plant = options[selected_name]
    if st.button("Use selected plant", key="confirm_manual_plant"):
        st.session_state.confirmed_plant_id = str(selected_plant.get("id", ""))
        st.session_state.confirmed_plant_name = str(
            selected_plant.get("name") or selected_plant.get("id") or "selected plant"
        )
        st.session_state.plant_confirmed = True
    _render_confirmed_profile()


def _render_confirmed_profile() -> None:
    if "confirmed_plant_name" not in st.session_state:
        return
    plant_name = st.session_state.confirmed_plant_name
    plant_id = st.session_state.get("confirmed_plant_id")
    if not plant_id:
        st.info(
            f"We identified {plant_name}, but care information is not currently available "
            "for this plant."
        )
        return
    plant = get_plant_by_id(plant_id)
    if plant is None:
        st.session_state.pop("confirmed_plant", None)
        st.info(
            f"We identified {plant_name}, but care information is not currently available "
            "for this plant."
        )
        return
    st.session_state.confirmed_plant = plant
    st.subheader(f"🌱 {plant.get('name') or 'Confirmed plant'}")
    if plant.get("scientific_name"):
        st.markdown("**Scientific name**")
        st.write(plant["scientific_name"])
    if plant.get("light"):
        st.markdown("**☀️ Light**")
        st.write(plant["light"])
    _render_soil_mix(plant)
    watering = plant.get("watering")
    if isinstance(watering, dict) and watering.get("rule"):
        st.markdown("**💧 Watering**")
        st.write(watering["rule"])
    if plant.get("pot_note"):
        st.markdown("**🪴 Pot and drainage**")
        st.write(plant["pot_note"])
    pot_volume = st.session_state.get(f"soil_volume_{plant.get('id', 'confirmed_plant')}")
    _render_save_to_my_pots(plant, pot_volume)
    _render_assistant(plant_id, plant)


def _render_save_to_my_pots(plant: dict[str, object], pot_volume: object) -> None:
    plant_id = plant.get("id")
    plant_name = plant.get("name")
    if not isinstance(plant_id, str) or not isinstance(plant_name, str):
        return
    saved_notice = st.session_state.pop("my_pots_saved_notice", None)
    if isinstance(saved_notice, str):
        st.success(saved_notice)
    if st.button("Save to My Pots", key=f"save_pot_{plant_id}"):
        try:
            was_saved = save_pot(
                plant_id,
                plant_name,
                plant.get("scientific_name")
                if isinstance(plant.get("scientific_name"), str)
                else None,
                float(pot_volume) if isinstance(pot_volume, (int, float)) else None,
                database_path=_session_database_path(),
            )
        except sqlite3.Error:
            st.error("Could not save this plant right now. Please try again.")
        else:
            if was_saved:
                st.session_state.my_pots_saved_notice = f"{plant_name} was saved to My Pots."
                st.rerun()
            else:
                st.info(f"{plant_name} is already saved in My Pots.")


def _render_my_pots() -> None:
    st.header("My Pots")
    try:
        saved_pots = list_saved_pots(
            database_path=_session_database_path()
        )
    except sqlite3.Error:
        st.info("Saved pots are unavailable right now.")
        return
    if not saved_pots:
        st.info("You have no saved pots yet.")
        return
    for saved_pot in saved_pots:
        with st.container(key=f"my-pot-{saved_pot['plant_id']}"):
            details_col, delete_col = st.columns([5, 1])
            with details_col:
                st.markdown(f"**🌱 {saved_pot['plant_name']}**")
                scientific_name = saved_pot.get("scientific_name")
                if scientific_name:
                    st.caption(f"Scientific name: {scientific_name}")
                pot_volume = saved_pot.get("pot_volume_litres")
                if pot_volume is not None:
                    st.caption(f"Pot capacity: {float(pot_volume):g} L")
            with delete_col:
                with st.container(key=f"my-pot-delete-{saved_pot['plant_id']}"):
                    if st.button(
                        "🗑️",
                        key=f"delete_pot_{saved_pot['plant_id']}",
                        help="Delete this saved pot",
                    ):
                        try:
                            delete_pot(
                                saved_pot["plant_id"],
                                database_path=_session_database_path(),
                            )
                        except sqlite3.Error:
                            st.error("Could not delete this pot right now.")
                        else:
                            st.rerun()


def _render_soil_mix(plant: dict[str, object]) -> None:
    st.markdown("**🪴 Pot Size**")
    total_volume = st.number_input(
        "Total pot volume (litres)",
        min_value=0.1,
        value=3.0,
        step=0.5,
        format="%.1f",
        key=f"soil_volume_{plant.get('id', 'confirmed_plant')}",
    )

    soil_mix = calculate_soil_mix(plant, total_volume)
    if not soil_mix:
        st.info("Soil mix calculation isn't available for this plant yet.")
        return

    st.markdown(f"**🌱 Soil Mix for {plant.get('name') or 'this plant'}**")
    st.caption(f"Pot capacity: {total_volume:g} L")
    for component in soil_mix:
        component_name = _format_soil_component_name(str(component["component"]))
        st.markdown(f"- {component_name} — {float(component['litres']):.1f} L")

    st.markdown("**💡 Soil guidance**")
    st.write("Use a well-draining mix in the proportions shown above.")


def _format_soil_component_name(component: str) -> str:
    words = component.replace("_", " ").split()
    if component == "pumice_or_coarse_grit":
        return "Pumice or coarse grit"
    return " ".join(word.capitalize() for word in words)


def _render_assistant(plant_id: str, plant: dict[str, object]) -> None:
    st.header("🌱 PlantWise Assistant")

    try:
        problems = get_problems_for_plant(plant_id)
    except ProblemDataError:
        problems = []
    try:
        diagnostic_data = load_problem_data()
    except ProblemDataError:
        diagnostic_context = {"plant_problems": problems}
    else:
        diagnostic_context = {
            "global_diagnostic_policy": diagnostic_data.get("global_diagnostic_policy", []),
            "plant_problems": problems,
        }

    conversation_id = st.session_state.get("current_conversation_id")
    try:
        if not isinstance(conversation_id, str):
            conversation_id = create_conversation(
                plant_id,
                str(plant.get("name") or plant_id),
                database_path=_session_database_path(),
            )
            st.session_state.current_conversation_id = conversation_id
        else:
            update_conversation(
                conversation_id,
                plant_id=plant_id,
                plant_name=str(plant.get("name") or plant_id),
                database_path=_session_database_path(),
            )
    except sqlite3.Error:
        st.error("Conversation history is unavailable right now.")
        return

    conversation_changed = (
        st.session_state.get("assistant_plant_id") != plant_id
        or st.session_state.get("assistant_conversation_id") != conversation_id
    )
    try:
        stored_messages = get_conversation_messages(
            conversation_id,
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.error("Conversation history is unavailable right now.")
        return

    # SQLite is the source of truth for messages; transient session state must
    # never allow a previous conversation's messages to remain visible.
    st.session_state.assistant_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in stored_messages
        if item.get("role") in {"user", "assistant"}
        and isinstance(item.get("content"), str)
    ]
    if conversation_changed:
        st.session_state.assistant_plant_id = plant_id
        st.session_state.assistant_conversation_id = conversation_id
        st.session_state.assistant_audio_cache = {}
        st.session_state.assistant_voice_targets = set()
        st.session_state.assistant_voice_attempted = set()
        st.session_state.assistant_voice_autoplayed = set()
        st.session_state.assistant_mic_signature = None
        st.session_state.assistant_mic_recording_bytes = None
        st.session_state.assistant_mic_transcription_attempted = False
        st.session_state.assistant_mic_transcript = None
        st.session_state.assistant_mic_submitted_signature = None
    messages = st.session_state.setdefault("assistant_messages", [])
    audio_cache = st.session_state.setdefault("assistant_audio_cache", {})
    voice_targets = st.session_state.setdefault("assistant_voice_targets", set())
    voice_attempted = st.session_state.setdefault("assistant_voice_attempted", set())
    voice_autoplayed = st.session_state.setdefault("assistant_voice_autoplayed", set())
    assistant_mode = st.radio(
        "Assistant mode",
        ["💬 Text Chat", "🎙️ Mic Assistant"],
        horizontal=True,
        key=f"assistant_mode_{plant_id}",
        label_visibility="collapsed",
    )
    hands_free = st.toggle(
        "🔊 Hands-Free Mode",
        key=f"hands_free_{plant_id}",
        help="Automatically generate and attempt to play audio for new assistant responses.",
    )

    for message_index, message in enumerate(messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                response_id = _assistant_response_id(message_index, message["content"])
                if hands_free and response_id in voice_targets and response_id not in voice_attempted:
                    voice_attempted.add(response_id)
                    with st.spinner("🌱 Preparing your audio response..."):
                        audio_bytes = text_to_speech(message["content"])
                    if audio_bytes:
                        audio_cache[response_id] = audio_bytes
                    else:
                        diagnostic = get_last_voice_error() or "No audio was returned."
                        st.warning(f"Voice playback unavailable: {diagnostic}")

                if (
                    hands_free
                    and response_id in voice_targets
                    and response_id in audio_cache
                    and response_id not in voice_autoplayed
                ):
                    _autoplay_audio(audio_cache[response_id])
                    voice_autoplayed.add(response_id)

                if st.button("🔊 Listen to response", key=f"listen_{response_id[:12]}"):
                    audio_bytes = audio_cache.get(response_id)
                    if audio_bytes is None:
                        audio_bytes = text_to_speech(message["content"])
                        if audio_bytes:
                            audio_cache[response_id] = audio_bytes
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                    else:
                        diagnostic = get_last_voice_error() or "No audio was returned."
                        st.warning(f"Voice playback unavailable: {diagnostic}")

    if assistant_mode == "🎙️ Mic Assistant":
        _render_mic_assistant(
            plant_id,
            plant,
            diagnostic_context,
            conversation_id,
            messages,
            hands_free,
            voice_targets,
        )
        if not problems:
            st.caption("Diagnostic information is unavailable; the assistant will say when the provided context is not enough.")
        return

    with st.form(f"assistant_form_{plant_id}", clear_on_submit=True):
        user_message = st.text_area(
            "Message",
            placeholder="Ask about your plant's symptoms or care...",
            height=90,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", type="primary")

    if not submitted:
        if not problems:
            st.caption("Diagnostic information is unavailable; the assistant will say when the provided context is not enough.")
        return
    if not user_message or not user_message.strip():
        st.warning("Please enter a message first.")
        return

    user_message = user_message.strip()
    messages.append({"role": "user", "content": user_message})
    try:
        save_message(
            conversation_id,
            "user",
            user_message,
            input_method="text",
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.error("Conversation history could not be saved, so this message may not survive a refresh.")
    try:
        with st.spinner("🌱 PotWise is thinking..."):
            assistant_response = chat_with_provider(messages, plant, diagnostic_context)
    except GeminiProviderError as exc:
        st.error(str(exc))
        return
    except OllamaUnavailableError:
        st.error("Ollama is unavailable. Start Ollama and try again.")
        return
    except OllamaModelError:
        st.error("The local Gemma model is unavailable. Check that `gemma3` is installed in Ollama.")
        return
    except AssistantResponseError:
        st.error("The assistant returned an unusable response. Please try again.")
        return

    messages.append({"role": "assistant", "content": assistant_response})
    try:
        save_message(
            conversation_id,
            "assistant",
            assistant_response,
            input_method="text",
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.warning("The response is visible, but conversation history could not be saved.")
    if hands_free:
        response_index = len(messages) - 1
        voice_targets.add(_assistant_response_id(response_index, assistant_response))
    st.rerun()


def _render_mic_assistant(
    plant_id: str,
    plant: dict[str, object],
    diagnostic_context: dict[str, object],
    conversation_id: str,
    messages: list[dict[str, str]],
    hands_free: bool,
    voice_targets: set[str],
) -> None:
    recording_event = record_microphone(key=f"mic_recorder_{plant_id}")
    if isinstance(recording_event, dict) and recording_event.get("status") == "complete":
        try:
            audio_bytes = base64.b64decode(
                recording_event.get("audio_base64", ""),
                validate=True,
            )
        except (ValueError, TypeError):
            audio_bytes = b""
        if audio_bytes:
            signature = hashlib.sha256(audio_bytes).hexdigest()
            if st.session_state.get("assistant_mic_signature") != signature:
                st.session_state.assistant_mic_signature = signature
                st.session_state.assistant_mic_recording_bytes = audio_bytes
                st.session_state.assistant_mic_transcription_attempted = False
                st.session_state.assistant_mic_transcript = None
                st.session_state.assistant_mic_submitted_signature = None
        else:
            st.warning("The microphone returned an empty recording. Please try again.")

    signature = st.session_state.get("assistant_mic_signature")
    audio_bytes = st.session_state.get("assistant_mic_recording_bytes")
    if not isinstance(signature, str) or not isinstance(audio_bytes, bytes) or not audio_bytes:
        return

    st.audio(audio_bytes, format="audio/webm")
    transcription_attempted = bool(
        st.session_state.get("assistant_mic_transcription_attempted")
    )
    retry_transcription = False
    if transcription_attempted and not st.session_state.get("assistant_mic_transcript"):
        retry_transcription = st.button(
            "Retry transcription",
            key=f"retry_transcription_{signature[:12]}",
        )

    if not transcription_attempted or retry_transcription:
        st.session_state.assistant_mic_transcription_attempted = True
        with st.spinner("🎙️ Transcribing your message..."):
            user_message = speech_to_text(audio_bytes)
        if user_message:
            st.session_state.assistant_mic_transcript = user_message
        else:
            diagnostic = get_last_voice_error() or "No transcript was returned."
            st.warning(f"Voice input unavailable: {diagnostic}")
            return

    user_message = st.session_state.get("assistant_mic_transcript")
    if (
        not isinstance(user_message, str)
        or not user_message.strip()
        or st.session_state.get("assistant_mic_submitted_signature") == signature
    ):
        return

    user_message = user_message.strip()
    messages.append({"role": "user", "content": user_message})
    st.session_state.assistant_mic_submitted_signature = signature
    try:
        save_message(
            conversation_id,
            "user",
            user_message,
            input_method="voice",
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.error("Conversation history could not be saved, so this message may not survive a refresh.")
    try:
        with st.spinner("🌱 PotWise is thinking..."):
            assistant_response = chat_with_provider(messages, plant, diagnostic_context)
    except GeminiProviderError as exc:
        st.error(str(exc))
        return
    except OllamaUnavailableError:
        st.error("Ollama is unavailable. Start Ollama and try again.")
        return
    except OllamaModelError:
        st.error("The local Gemma model is unavailable. Check that `gemma3` is installed in Ollama.")
        return
    except AssistantResponseError:
        st.error("The assistant returned an unusable response. Please try again.")
        return

    messages.append({"role": "assistant", "content": assistant_response})
    try:
        save_message(
            conversation_id,
            "assistant",
            assistant_response,
            input_method="voice",
            database_path=_session_database_path(),
        )
    except sqlite3.Error:
        st.warning("The response is visible, but conversation history could not be saved.")
    if hands_free:
        response_index = len(messages) - 1
        voice_targets.add(_assistant_response_id(response_index, assistant_response))
    st.rerun()


def _assistant_response_id(message_index: int, content: str) -> str:
    return hashlib.sha256(f"{message_index}:{content}".encode("utf-8")).hexdigest()


def _autoplay_audio(audio_bytes: bytes) -> None:
    """Attempt one compact browser autoplay using already-generated MP3 bytes."""

    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    components.html(
        f"""
        <div id="autoplay-status" style="font: 0.85rem sans-serif; color: #6b7280; min-height: 20px;"></div>
        <script>
        (() => {{
          const status = document.getElementById("autoplay-status");
          const binary = atob("{encoded_audio}");
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
          const url = URL.createObjectURL(new Blob([bytes], {{ type: "audio/mpeg" }}));
          const audio = new Audio(url);
          const cleanup = () => {{
            audio.pause();
            audio.removeAttribute("src");
            URL.revokeObjectURL(url);
          }};
          audio.addEventListener("ended", cleanup, {{ once: true }});
          audio.addEventListener("error", cleanup, {{ once: true }});
          audio.play().catch(() => {{
            status.textContent = "🔊 Autoplay was blocked. Click Listen to response.";
            cleanup();
          }});
        }})();
        </script>
        """,
        height=28,
        scrolling=False,
    )


if __name__ == "__main__":
    main()
