import streamlit as st
import whisper
import tempfile
import os

st.set_page_config(page_title="Free Caption Generator", page_icon="🎬")

st.title("🎬 ఉచిత Caption Generator")
st.write("Video లేదా Audio ఫైల్ అప్‌లోడ్ చేయండి — automatic captions పొందండి (SRT ఫైల్‌తో సహా)")

# ---------- Sidebar settings ----------
st.sidebar.header("సెట్టింగ్స్")

lang_options = {
    "Telugu (తెలుగు)": "te",
    "English": "en",
    "Hindi (हिन्दी)": "hi",
    "Tamil (தமிழ்)": "ta",
    "Auto Detect": None,
}
lang_choice = st.sidebar.selectbox("భాష ఎంచుకోండి", list(lang_options.keys()))
selected_lang = lang_options[lang_choice]

model_choice = st.sidebar.selectbox(
    "మోడల్ సైజ్ (పెద్దది = accurate, కానీ నెమ్మది)",
    ["tiny", "base", "small", "medium"],
    index=1,
)

st.sidebar.info("CPU మీద నడుస్తుంది కాబట్టి 'base' లేదా 'small' recommend చేస్తున్నాం.")

# ---------- Load model (cached so it doesn't reload every time) ----------
@st.cache_resource
def load_model(name):
    return whisper.load_model(name)

# ---------- File upload ----------
uploaded_file = st.file_uploader(
    "ఫైల్ అప్‌లోడ్ చేయండి",
    type=["mp4", "mov", "mkv", "avi", "mp3", "wav", "m4a"],
)

def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def build_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)

if uploaded_file is not None:
    st.audio(uploaded_file) if uploaded_file.type.startswith("audio") else st.video(uploaded_file)

    if st.button("Captions తయారు చేయండి 🚀"):
        with st.spinner("Processing... ఫైల్ పెద్దదైతే కొంచెం సమయం పట్టవచ్చు"):
            # Save uploaded file to a temp path (whisper needs a file path)
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                model = load_model(model_choice)
                result = model.transcribe(tmp_path, language=selected_lang)

                st.success("పూర్తయింది! ✅")

                st.subheader("పూర్తి టెక్స్ట్")
                st.text_area("Transcript", result["text"], height=200)

                srt_content = build_srt(result["segments"])

                st.subheader("డౌన్‌లోడ్ ఆప్షన్స్")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "⬇️ SRT ఫైల్ డౌన్‌లోడ్ (subtitles)",
                        srt_content,
                        file_name="captions.srt",
                        mime="text/plain",
                    )
                with col2:
                    st.download_button(
                        "⬇️ TXT ఫైల్ డౌన్‌లోడ్ (plain text)",
                        result["text"],
                        file_name="transcript.txt",
                        mime="text/plain",
                    )
            finally:
                os.remove(tmp_path)

st.markdown("---")
st.caption("ఈ టూల్ OpenAI Whisper తో నడుస్తుంది — పూర్తిగా ఉచితం, ఓపెన్ సోర్స్.")
