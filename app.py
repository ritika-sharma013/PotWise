"""PotWise Streamlit application entry point."""

from __future__ import annotations

import streamlit as st

from core.identify import (
    IdentificationError,
    OllamaModelError,
    OllamaUnavailableError,
    identify_plant,
    load_known_plants,
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

    if st.button("Identify with local Gemma", type="primary"):
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
    st.success(f"Likely plant: {result.predicted_name}")
    if result.plant_id:
        st.caption(f"Matched trusted plant ID: `{result.plant_id}`")
    else:
        st.warning(
            "This prediction did not match a plant ID in data/plants.json. "
            "Confirm it manually before using it in a future workflow."
        )

    plants = load_known_plants()
    if plants:
        options = {str(plant.get("name", plant.get("id"))): plant for plant in plants}
        selected_name = st.selectbox("Confirm or correct the plant", list(options))
        st.caption(f"Selected plant ID: `{options[selected_name].get('id')}`")
    else:
        st.info("Manual correction options will appear once trusted plant records exist.")


if __name__ == "__main__":
    main()
