"""PotWise Streamlit application entry point."""

from __future__ import annotations

import hashlib
import sqlite3

import streamlit as st

from core.identify import (
    IdentificationError,
    OllamaModelError,
    OllamaUnavailableError,
    identify_plant,
)
from core.plant_data import get_plant_by_id, get_supported_plants
from core.assistant import AssistantResponseError, chat_with_gemma
from core.problem_data import ProblemDataError, get_problems_for_plant, load_problem_data
from core.soil import calculate_soil_mix
from core.voice import get_last_voice_error, speech_to_text, text_to_speech
from core.pots import (
    delete_pot,
    get_or_create_conversation,
    list_saved_pots,
    load_conversation_messages,
    save_conversation_message,
    save_pot,
)


def main() -> None:
    st.set_page_config(page_title="PotWise", page_icon="🌿", layout="centered")
    st.title("🌿 PotWise")
    st.write("Offline-first plant identification and care companion.")

    st.header("Identify a plant")
    uploaded_image = st.file_uploader(
        "Upload a plant photo",
        type=["jpg", "jpeg", "png", "webp"],
        help="The image is sent only to your local Ollama instance.",
    )
    if uploaded_image is None:
        st.info("Upload a photo to begin.")
        return

    image_bytes = uploaded_image.getvalue()
    st.image(image_bytes, caption=uploaded_image.name, use_container_width=True)
    image_signature = hashlib.sha256(image_bytes).hexdigest()
    if st.session_state.get("identification_image_signature") != image_signature:
        st.session_state.identification_image_signature = image_signature
        st.session_state.pop("identification", None)
        st.session_state.pop("manual_selection_requested", None)
        st.session_state.pop("confirmed_plant_id", None)
        st.session_state.pop("confirmed_plant_name", None)
        st.session_state.pop("confirmed_plant", None)
        st.session_state.pop("assistant_messages", None)
        st.session_state.pop("assistant_plant_id", None)
        st.session_state.pop("assistant_conversation_id", None)
        st.session_state.pop("assistant_mic_signature", None)
        st.session_state.pop("assistant_mic_recording_bytes", None)
        st.session_state.pop("assistant_mic_transcription_attempted", None)
        st.session_state.pop("assistant_mic_transcript", None)
        st.session_state.pop("assistant_mic_submitted_signature", None)

    if st.button("Identify with local Gemma", type="primary"):
        st.session_state.pop("confirmed_plant_id", None)
        st.session_state.pop("confirmed_plant_name", None)
        st.session_state.pop("confirmed_plant", None)
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
                st.session_state.identification = identify_plant(image_bytes)
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

    confirm_col, manual_col = st.columns(2)
    with confirm_col:
        if st.button("Yes, this is my plant", key="confirm_identification"):
            st.session_state.confirmed_plant_id = result.plant_id
            st.session_state.confirmed_plant_name = result.common_name
    with manual_col:
        if st.button("No, choose manually", key="choose_manual_plant"):
            st.session_state.manual_selection_requested = True
    if st.session_state.get("manual_selection_requested"):
        _render_manual_selection()
    else:
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
    _render_my_pots()


def _render_save_to_my_pots(plant: dict[str, object], pot_volume: object) -> None:
    plant_id = plant.get("id")
    plant_name = plant.get("name")
    if not isinstance(plant_id, str) or not isinstance(plant_name, str):
        return
    if st.button("Save to My Pots", key=f"save_pot_{plant_id}"):
        try:
            was_saved = save_pot(
                plant_id,
                plant_name,
                plant.get("scientific_name")
                if isinstance(plant.get("scientific_name"), str)
                else None,
                float(pot_volume) if isinstance(pot_volume, (int, float)) else None,
            )
        except sqlite3.Error:
            st.error("Could not save this plant right now. Please try again.")
        else:
            if was_saved:
                st.success(f"{plant_name} was saved to My Pots.")
            else:
                st.info(f"{plant_name} is already saved in My Pots.")


def _render_my_pots() -> None:
    st.header("My Pots")
    try:
        saved_pots = list_saved_pots()
    except sqlite3.Error:
        st.info("Saved pots are unavailable right now.")
        return
    if not saved_pots:
        st.info("You have no saved pots yet.")
        return
    for saved_pot in saved_pots:
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
            if st.button("Delete", key=f"delete_pot_{saved_pot['plant_id']}"):
                try:
                    delete_pot(saved_pot["plant_id"])
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

    try:
        conversation_id = get_or_create_conversation(plant_id)
    except sqlite3.Error:
        st.error("Conversation history is unavailable right now.")
        return

    if (
        st.session_state.get("assistant_plant_id") != plant_id
        or st.session_state.get("assistant_conversation_id") != conversation_id
    ):
        try:
            stored_messages = load_conversation_messages(conversation_id)
        except sqlite3.Error:
            st.error("Conversation history is unavailable right now.")
            return
        st.session_state.assistant_plant_id = plant_id
        st.session_state.assistant_conversation_id = conversation_id
        st.session_state.assistant_messages = [
            {"role": item["role"], "content": item["message_text"]}
            for item in stored_messages
            if item.get("role") in {"user", "assistant"}
            and isinstance(item.get("message_text"), str)
        ]
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
                    st.audio(audio_cache[response_id], format="audio/mp3", autoplay=True)
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
        save_conversation_message(conversation_id, "user", user_message, "text")
    except sqlite3.Error:
        st.error("Conversation history could not be saved, so this message may not survive a refresh.")
    try:
        with st.spinner("🌱 PotWise is thinking..."):
            assistant_response = chat_with_gemma(messages, plant, diagnostic_context)
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
        save_conversation_message(conversation_id, "assistant", assistant_response, "text")
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
    recording = st.audio_input(
        "Press the microphone button to record a message",
        key=f"mic_input_{plant_id}",
        sample_rate=16000,
    )
    if recording is not None:
        audio_bytes = recording.getvalue()
        signature = hashlib.sha256(audio_bytes).hexdigest()
        if st.session_state.get("assistant_mic_signature") != signature:
            st.session_state.assistant_mic_signature = signature
            st.session_state.assistant_mic_recording_bytes = audio_bytes
            st.session_state.assistant_mic_transcription_attempted = False
            st.session_state.assistant_mic_transcript = None
            st.session_state.assistant_mic_submitted_signature = None

    signature = st.session_state.get("assistant_mic_signature")
    audio_bytes = st.session_state.get("assistant_mic_recording_bytes")
    if not isinstance(signature, str) or not isinstance(audio_bytes, bytes) or not audio_bytes:
        return

    st.audio(audio_bytes, format="audio/wav")
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
        save_conversation_message(conversation_id, "user", user_message, "voice")
    except sqlite3.Error:
        st.error("Conversation history could not be saved, so this message may not survive a refresh.")
    try:
        with st.spinner("🌱 PotWise is thinking..."):
            assistant_response = chat_with_gemma(messages, plant, diagnostic_context)
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
        save_conversation_message(conversation_id, "assistant", assistant_response, "voice")
    except sqlite3.Error:
        st.warning("The response is visible, but conversation history could not be saved.")
    if hands_free:
        response_index = len(messages) - 1
        voice_targets.add(_assistant_response_id(response_index, assistant_response))
    st.rerun()


def _assistant_response_id(message_index: int, content: str) -> str:
    return hashlib.sha256(f"{message_index}:{content}".encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
