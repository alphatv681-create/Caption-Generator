import streamlit as st
import whisper
import tempfile
import os
import subprocess

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

burn_in = st.sidebar.checkbox(
    "🔥 Captions ని వీడియో మీద burn చేయాలి (styled)",
    value=False,
    help="ఇది ఎంచుకుంటే, captions ఒక styled బాక్స్‌తో నేరుగా వీడియోలో పొందుపరచబడతాయి. వీడియో ఫైల్స్‌కి మాత్రమే పనిచేస్తుంది, ఎక్కువ సమయం పట్టవచ్చు.",
)

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


def ass_timestamp(seconds: float) -> str:
    """Convert seconds to ASS timestamp format: H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:d}:{minutes:02d}:{secs:05.2f}"


def build_ass(segments, font_size=28) -> str:
    """Build an .ass subtitle file with a styled, boxed caption
    (white bold text, black semi-transparent background, bottom-center)."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans Telugu,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,1,0,2,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segments:
        start = ass_timestamp(seg["start"])
        end = ass_timestamp(seg["end"])
        text = seg["text"].strip().replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
    return "".join(lines)


def burn_captions(video_path: str, ass_path: str, output_path: str):
    """Use ffmpeg to burn styled captions directly onto the video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])

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

                is_video = not uploaded_file.type.startswith("audio")
                if burn_in and is_video:
                    with st.spinner("వీడియో మీద captions burn చేస్తున్నాం... ఇది కొన్ని నిమిషాలు పట్టవచ్చు"):
                        try:
                            ass_content = build_ass(result["segments"])
                            ass_path = tmp_path + ".ass"
                            with open(ass_path, "w", encoding="utf-8") as f:
                                f.write(ass_content)

                            output_path = tmp_path + "_captioned.mp4"
                            burn_captions(tmp_path, ass_path, output_path)

                            st.success("Captions వీడియోలో పొందుపరచబడ్డాయి! ✅")
                            st.video(output_path)

                            with open(output_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Captioned వీడియో డౌన్‌లోడ్ చేయండి",
                                    f.read(),
                                    file_name="captioned_video.mp4",
                                    mime="video/mp4",
                                )
                            os.remove(ass_path)
                            os.remove(output_path)
                        except Exception as e:
                            st.error(f"వీడియోలో captions burn చేయడంలో సమస్య వచ్చింది: {e}")
                elif burn_in and not is_video:
                    st.warning("⚠️ Burn-in ఆప్షన్ వీడియో ఫైల్స్‌కి మాత్రమే పనిచేస్తుంది, ఆడియో ఫైల్స్‌కి కాదు.")
            finally:
                os.remove(tmp_path)

st.markdown("---")
st.caption("ఈ టూల్ OpenAI Whisper తో నడుస్తుంది — పూర్తిగా ఉచితం, ఓపెన్ సోర్స్.")
