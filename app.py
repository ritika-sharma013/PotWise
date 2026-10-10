"""PotWise Streamlit application entry point."""

from __future__ import annotations

import hashlib

import streamlit as st

from core.identify import (
    IdentificationError,
    OllamaModelError,
    OllamaUnavailableError,
    identify_plant,
)
from core.plant_data import get_plant_by_id, get_supported_plants


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

    if st.button("Identify with local Gemma", type="primary"):
        st.session_state.pop("confirmed_plant_id", None)
        st.session_state.pop("confirmed_plant_name", None)
        st.session_state.pop("confirmed_plant", None)
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
    if result.plant_id:
        st.caption(f"Matched trusted plant ID: `{result.plant_id}`")
    else:
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
    st.caption(f"Selected plant ID: `{selected_plant.get('id')}`")
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
    st.subheader("Plant profile")
    st.json(plant)


if __name__ == "__main__":
    main()
