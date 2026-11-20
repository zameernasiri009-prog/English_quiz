import base64
import html
import json
import os
import re
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Speaking Practice Recorder",
    page_icon="🎙️",
    layout="centered",
)

SAVE_DIR = "recordings"
os.makedirs(SAVE_DIR, exist_ok=True)

SPEAKING_SETS = [
    (1, ["What's your name?", "Where are you from?", "How do you spell it?"]),
    (2, ["Are you on holiday?", "Are you late?", "Are you from England?"]),
    (3, ["Who is she?", "How old is she?", "Is she from Russia?"]),
    (4, ["Where's he from?", "Is he married?", "Is he from Egypt?"]),
    (5, ["Who are they?", "Are they Mexican?", "Where are they from?"]),
    (6, ["What's your email?", "What's your friend's phone number?", "When's the concert?"]),
    (7, ["What's the woman's name?", "What's Main's phone number?", "What's Iain's email address?"]),
    (8, ["Who is this?", "Who are those girls over there?", "Is that your brother or sister?"]),
    (9, ["Whose house is this?", "Whose car is that?", "Whose name is Molly?"]),
    (10, ["Do you have a big family?", "What do you have in your bag?", "Are those old houses or new houses?"]),
    (11, ["How much is this book or watch?", "How much are these key rings?", "How much are those tickets?"]),
    (12, ["Can I have an orange juice?", "Is that a Manchester United shirt?", "What do you say at the end?"]),
    (13, ["What time do you get up?", "Where do you live?", "What do you do in the evening?"]),
    (14, ["Where do you work or study?", "Do you speak English?", "Do you go to English classes?"]),
    (15, ["What do you have for breakfast?", "What don't you have for lunch?", "What don't they have for dinner?"]),
    (16, ["Do you live near here?", "Do you watch a lot of TV?", "Do you like children?"]),
    (17, ["What does he do?", "What does she do?", "What do you do or study?"]),
    (18, ["Where does a doctor work?", "Where does a waiter or waitress work?", "Where does she work?"]),
    (19, ["What do you always do in the morning?", "What do you usually do after work or study?", "What do you sometimes do in the evening?"]),
    (20, ["What does he never eat?", "What does she sometimes do in the evening?", "What do you sometimes do?"]),
]


def sanitize_filename_part(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "").strip())
    cleaned = cleaned.strip("_")
    return cleaned or "Student"


def render_html(html_str: str, height: int | str = "content", alt: str = "Widget"):
    if hasattr(st, "iframe"):
        st.iframe(html_str, height=height, alt=alt)
    else:
        components.html(html_str, height=160 if height == "content" else int(height))


def listen_speaker(lines: list[str], key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    payload = json.dumps(lines)
    render_html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;font-family:sans-serif;">
            <button type="button" onclick="speak_{safe_id}()"
                style="background:#2563EB;color:#fff;border:none;padding:9px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">
                🔊 Listen
            </button>
            <span id="spk_status_{safe_id}" style="color:#E2E8F0;font-size:13px;"></span>
        </div>
        <script>
        function speak_{safe_id}() {{
            const items = {payload};
            const el = document.getElementById("spk_status_{safe_id}");
            if (!("speechSynthesis" in window)) {{
                el.textContent = items.join(" ");
                return;
            }}
            window.speechSynthesis.cancel();
            window.speechSynthesis.resume();
            const voices = window.speechSynthesis.getVoices();
            const enVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith("en")) || null;
            el.textContent = "Speaking...";
            items.forEach((line, i) => {{
                const u = new SpeechSynthesisUtterance(line);
                u.lang = "en-US";
                u.rate = 0.95;
                if (enVoice) u.voice = enVoice;
                if (i === items.length - 1) {{
                    u.onend = () => el.textContent = "";
                    u.onerror = () => el.textContent = "";
                }}
                window.speechSynthesis.speak(u);
            }});
        }}
        </script>
        """,
        height=52,
        alt="Speaker button",
    )


def mic_box(set_no: int, key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    render_html(
        f"""
        <div style="font-family:sans-serif;background:#111827;border:1px solid #334155;border-radius:10px;padding:12px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <button type="button" id="mbtn_{safe_id}" onclick="recToggle_{safe_id}()"
                    style="background:#DC2626;color:#fff;border:none;padding:9px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">
                    🎙️ Mic
                </button>
                <span id="mstat_{safe_id}" style="color:#F8FAFC;font-size:13px;">Ready</span>
                <span id="mtimer_{safe_id}" style="color:#FBBF24;font-size:13px;font-weight:700;">00:00</span>
            </div>
            <audio id="mplay_{safe_id}" controls style="width:100%;margin-top:10px;display:none;"></audio>
        </div>
        <script>
        let rec_{safe_id} = null, stream_{safe_id} = null, chunks_{safe_id} = [], iv_{safe_id} = null, sec_{safe_id} = 0;
        function fmt_{safe_id}(s) {{
            return String(Math.floor(s/60)).padStart(2,"0") + ":" + String(s%60).padStart(2,"0");
        }}
        async function recToggle_{safe_id}() {{
            const btn = document.getElementById("mbtn_{safe_id}");
            const stat = document.getElementById("mstat_{safe_id}");
            const timer = document.getElementById("mtimer_{safe_id}");
            const player = document.getElementById("mplay_{safe_id}");
            if (rec_{safe_id} && rec_{safe_id}.state === "recording") {{
                rec_{safe_id}.stop();
                clearInterval(iv_{safe_id});
                btn.textContent = "🎙️ Mic";
                btn.style.background = "#DC2626";
                stat.textContent = "Recorded — now tap Save";
                return;
            }}
            try {{
                stream_{safe_id} = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                chunks_{safe_id} = [];
                rec_{safe_id} = new MediaRecorder(stream_{safe_id});
                rec_{safe_id}.ondataavailable = e => {{ if (e.data && e.data.size > 0) chunks_{safe_id}.push(e.data); }};
                rec_{safe_id}.onstop = () => {{
                    const mime = rec_{safe_id}.mimeType || "audio/webm";
                    const blob = new Blob(chunks_{safe_id}, {{ type: mime }});
                    player.src = URL.createObjectURL(blob);
                    player.style.display = "block";
                    stream_{safe_id}.getTracks().forEach(t => t.stop());
                    const reader = new FileReader();
                    reader.onloadend = () => {{
                        const b64 = (reader.result || "").split(",")[1] || "";
                        if (!window.top.__savedVoice) window.top.__savedVoice = {{}};
                        window.top.__savedVoice[{set_no}] = {{ base64: b64, mime: mime }};
                    }};
                    reader.readAsDataURL(blob);
                }};
                rec_{safe_id}.start();
                sec_{safe_id} = 0;
                timer.textContent = "00:00";
                clearInterval(iv_{safe_id});
                iv_{safe_id} = setInterval(() => {{
                    sec_{safe_id} += 1;
                    timer.textContent = fmt_{safe_id}(sec_{safe_id});
                }}, 1000);
                btn.textContent = "⏹ Stop";
                btn.style.background = "#059669";
                stat.textContent = "Recording...";
            }} catch (e) {{
                stat.textContent = "Mic error: allow microphone permission";
            }}
        }}
        </script>
        """,
        height="content",
        alt="Mic recorder",
    )


if "sp_set_idx" not in st.session_state:
    st.session_state.sp_set_idx = 0
if "last_saved_msg" not in st.session_state:
    st.session_state.last_saved_msg = ""

st.title("🎙️ Speaking Practice Recorder")
student_name = st.text_input("Your Name:", placeholder="Write your name here...")

set_idx = st.session_state.sp_set_idx
set_no, qs = SPEAKING_SETS[set_idx]

st.progress((set_idx + 1) / len(SPEAKING_SETS), text=f"Set {set_no} of {len(SPEAKING_SETS)}")
st.subheader(f"Set {set_no}")
st.caption("Answer each question in one sentence, record your voice, and tap Save.")

for idx, q in enumerate(qs, start=1):
    st.markdown(f"**{idx}. {html.escape(q)}**")

listen_speaker(qs, key_id=f"spk_{set_no}")
mic_box(set_no=set_no, key_id=f"mic_{set_no}")

# Fallback / direct file upload option if browser bridge is blocked on a device
uploaded_audio = st.file_uploader(
    "Or attach/upload your recorded audio file (optional backup):",
    type=["webm", "mp3", "wav", "m4a", "ogg"],
    key=f"upload_{set_no}",
)

if st.button("💾 Save Recording", type="primary", key=f"save_btn_{set_no}"):
    clean_student = sanitize_filename_part(student_name)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = False

    if uploaded_audio is not None:
        ext = os.path.splitext(uploaded_audio.name)[1].lower() or ".webm"
        out_name = f"{clean_student}_Set_{set_no:02d}_{stamp}{ext}"
        out_path = os.path.join(SAVE_DIR, out_name)
        with open(out_path, "wb") as f:
            f.write(uploaded_audio.getbuffer())
        st.session_state.last_saved_msg = f"Saved recording as `{out_name}`."
        saved = True
    else:
        st.session_state.last_saved_msg = (
            f"Ready for `{clean_student}` (Set {set_no}). "
            "If your mic recording doesn't attach automatically in your browser, use the audio upload box above and tap Save Recording."
        )
        saved = True

    if saved:
        st.rerun()

if st.session_state.last_saved_msg:
    st.success(st.session_state.last_saved_msg)

col_prev, col_next = st.columns(2)
with col_prev:
    if st.button("⬅️ Previous Set", disabled=(set_idx == 0)):
        st.session_state.sp_set_idx = max(0, set_idx - 1)
        st.rerun()
with col_next:
    if st.button("Next Set ➡️", disabled=(set_idx == len(SPEAKING_SETS) - 1)):
        st.session_state.sp_set_idx = min(len(SPEAKING_SETS) - 1, set_idx + 1)
        st.rerun()

saved_files = sorted(os.listdir(SAVE_DIR), reverse=True)
if saved_files:
    st.divider()
    st.markdown("### Saved Recordings (Review)")
    filter_name = st.text_input("Filter by student name:", placeholder="Type a name to filter...")
    for fname in saved_files:
        if filter_name.strip() and filter_name.strip().lower() not in fname.lower():
            continue
        fpath = os.path.join(SAVE_DIR, fname)
        st.markdown(f"**{html.escape(fname)}**")
        st.audio(fpath)
