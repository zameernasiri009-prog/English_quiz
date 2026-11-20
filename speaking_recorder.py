import base64
import html
import json
import os
import re
import zipfile
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Speaking Practice Recorder",
    page_icon="🎙️",
    layout="centered",
)

SAVE_DIR = "recordings"
BUNDLE_PATH = os.path.join(SAVE_DIR, "all_speaking_recordings.zip")
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


def ext_from_mime(mime: str) -> str:
    m = (mime or "").lower()
    if "mp4" in m or "m4a" in m:
        return ".m4a"
    if "ogg" in m:
        return ".ogg"
    if "wav" in m:
        return ".wav"
    if "mpeg" in m or "mp3" in m:
        return ".mp3"
    return ".webm"


def iter_all_audio_files():
    items = []
    for root, _, files in os.walk(SAVE_DIR):
        for fname in sorted(files):
            full_path = os.path.join(root, fname)
            if os.path.abspath(full_path) == os.path.abspath(BUNDLE_PATH):
                continue
            rel_path = os.path.relpath(full_path, SAVE_DIR)
            parts = rel_path.split(os.sep)
            student_folder = parts[0] if len(parts) > 1 else fname.split("_Set_")[0]
            items.append((student_folder, fname, full_path))
    return items


def rebuild_combined_zip():
    all_items = iter_all_audio_files()
    with zipfile.ZipFile(BUNDLE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for student_folder, fname, full_path in all_items:
            arcname = os.path.join(student_folder, fname)
            zf.write(full_path, arcname=arcname)


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


def recorder_and_save_component(set_no: int, student_name: str, key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    clean_student = sanitize_filename_part(student_name)
    html_code = f"""
    <div style="font-family:sans-serif;background:#111827;border:1px solid #334155;border-radius:10px;padding:12px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <button type="button" id="mbtn_{safe_id}" onclick="recToggle_{safe_id}()"
                style="background:#DC2626;color:#fff;border:none;padding:9px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">
                🎙️ Mic
            </button>
            <button type="button" id="sbtn_{safe_id}" onclick="sendSave_{safe_id}()"
                style="background:#059669;color:#fff;border:none;padding:9px 18px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">
                💾 Save Recording
            </button>
            <span id="mstat_{safe_id}" style="color:#F8FAFC;font-size:13px;">Ready</span>
            <span id="mtimer_{safe_id}" style="color:#FBBF24;font-size:13px;font-weight:700;">00:00</span>
        </div>
        <audio id="mplay_{safe_id}" controls style="width:100%;margin-top:10px;display:none;"></audio>
    </div>
    <script>
    let rec_{safe_id} = null;
    let stream_{safe_id} = null;
    let chunks_{safe_id} = [];
    let iv_{safe_id} = null;
    let sec_{safe_id} = 0;
    let latestB64_{safe_id} = "";
    let latestMime_{safe_id} = "audio/webm";
    let readySent_{safe_id} = false;

    function postMsg_{safe_id}(msg) {{
        window.parent.postMessage(Object.assign({{ isStreamlitMessage: true }}, msg), "*");
    }}

    function setCompValue_{safe_id}(val) {{
        postMsg_{safe_id}({{
            type: "streamlit:setComponentValue",
            value: val,
            dataType: "json"
        }});
    }}

    function notifyReady_{safe_id}() {{
        if (!readySent_{safe_id}) {{
            readySent_{safe_id} = true;
            postMsg_{safe_id}({{
                type: "streamlit:componentReady",
                apiVersion: 1
            }});
            postMsg_{safe_id}({{
                type: "streamlit:setFrameHeight",
                height: 135
            }});
        }}
    }}

    window.addEventListener("load", notifyReady_{safe_id});
    setTimeout(notifyReady_{safe_id}, 100);

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
            stat.textContent = "Processing audio...";
            return;
        }}
        try {{
            stream_{safe_id} = await navigator.mediaDevices.getUserMedia({{ audio: true }});
            chunks_{safe_id} = [];
            latestB64_{safe_id} = "";
            rec_{safe_id} = new MediaRecorder(stream_{safe_id});
            rec_{safe_id}.ondataavailable = e => {{ if (e.data && e.data.size > 0) chunks_{safe_id}.push(e.data); }};
            rec_{safe_id}.onstop = () => {{
                const mime = rec_{safe_id}.mimeType || "audio/webm";
                latestMime_{safe_id} = mime;
                const blob = new Blob(chunks_{safe_id}, {{ type: mime }});
                player.src = URL.createObjectURL(blob);
                player.style.display = "block";
                stream_{safe_id}.getTracks().forEach(t => t.stop());
                const reader = new FileReader();
                reader.onloadend = () => {{
                    latestB64_{safe_id} = (reader.result || "").split(",")[1] || "";
                    stat.textContent = latestB64_{safe_id} ? "Ready — tap Save Recording" : "Could not read audio";
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

    function sendSave_{safe_id}() {{
        const stat = document.getElementById("mstat_{safe_id}");
        if (!latestB64_{safe_id}) {{
            stat.textContent = "Tap Mic, speak, and tap Stop before Save Recording.";
            return;
        }}
        setCompValue_{safe_id}({{
            set_no: {set_no},
            student: {json.dumps(clean_student)},
            mime: latestMime_{safe_id},
            b64: latestB64_{safe_id},
            ts: Date.now()
        }});
        stat.textContent = "Sent to save!";
    }}
    </script>
    """
    return components.html(html_code, height=135)


if "sp_set_idx" not in st.session_state:
    st.session_state.sp_set_idx = 0
if "last_saved_msg" not in st.session_state:
    st.session_state.last_saved_msg = ""
if "last_processed_ts" not in st.session_state:
    st.session_state.last_processed_ts = None

st.title("🎙️ Speaking Practice Recorder")
student_name = st.text_input("Your Name:", placeholder="Write your name here...")

set_idx = st.session_state.sp_set_idx
set_no, qs = SPEAKING_SETS[set_idx]

st.progress((set_idx + 1) / len(SPEAKING_SETS), text=f"Set {set_no} of {len(SPEAKING_SETS)}")
st.subheader(f"Set {set_no}")
st.caption("Answer each question in one sentence, record your voice, and tap Save Recording.")

for idx, q in enumerate(qs, start=1):
    st.markdown(f"**{idx}. {html.escape(q)}**")

listen_speaker(qs, key_id=f"spk_{set_no}")
comp_val = recorder_and_save_component(set_no=set_no, student_name=student_name, key_id=f"rec_{set_no}")

if isinstance(comp_val, dict) and comp_val.get("b64"):
    ts_val = comp_val.get("ts")
    if ts_val != st.session_state.last_processed_ts:
        st.session_state.last_processed_ts = ts_val
        clean_student = sanitize_filename_part(comp_val.get("student") or student_name)
        target_set = int(comp_val.get("set_no") or set_no)
        ext = ext_from_mime(comp_val.get("mime") or "audio/webm")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        student_dir = os.path.join(SAVE_DIR, clean_student)
        os.makedirs(student_dir, exist_ok=True)
        out_name = f"{clean_student}_Set_{target_set:02d}_{stamp}{ext}"
        out_path = os.path.join(student_dir, out_name)

        try:
            raw_bytes = base64.b64decode(comp_val["b64"])
            with open(out_path, "wb") as f:
                f.write(raw_bytes)
            rebuild_combined_zip()
            st.session_state.last_saved_msg = (
                f"Saved `{out_name}` inside `recordings/{clean_student}/` and updated `all_speaking_recordings.zip`."
            )
            st.rerun()
        except Exception as e:
            st.session_state.last_saved_msg = f"Could not save audio: {e}"

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

all_recordings = iter_all_audio_files()

if os.path.exists(BUNDLE_PATH) and all_recordings:
    st.divider()
    with open(BUNDLE_PATH, "rb") as zf_in:
        st.download_button(
            label="📦 Download All Student Recordings (ZIP)",
            data=zf_in.read(),
            file_name="all_speaking_recordings.zip",
            mime="application/zip",
        )

if all_recordings:
    st.markdown("### Saved Recordings by Student")
    student_names = sorted({item[0] for item in all_recordings})
    selected_student = st.selectbox("Select a student to check their recordings:", ["All Students"] + student_names)

    for s_name in student_names:
        if selected_student != "All Students" and s_name != selected_student:
            continue
        s_files = [item for item in all_recordings if item[0] == s_name]
        with st.expander(f"🧑 {s_name} ({len(s_files)} recording{'s' if len(s_files) != 1 else ''})", expanded=(selected_student != "All Students")):
            for _, fname, fpath in reversed(s_files):
                st.markdown(f"**{html.escape(fname)}**")
                st.audio(fpath)
