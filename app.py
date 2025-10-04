import streamlit as st
import os
from pipeline import main  # imports your pipeline

st.set_page_config(page_title="AI Reel Generator", layout="centered")

st.title("🎬 AI Reel Generator")
st.markdown("Generate cinematic short reels using **Gemini** and **Hugging Face**.")

theme = st.text_input("Enter your reel theme:", "An Adventurous Holiday Story")

if st.button("Generate Reel"):
    st.info("Running the full AI generation pipeline... please wait ⏳")
    try:
        main(theme)  # Run your existing function
        output_path = "data/generated_reel.mp4"
        if os.path.exists(output_path):
            st.success("✅ Generation complete!")
            st.video(output_path)
            with open(output_path, "rb") as f:
                st.download_button("Download Reel", f, file_name="generated_reel.mp4")
        else:
            st.error("No video file found. Check logs for details.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
