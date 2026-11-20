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


def parse_set_from_filename(fname: str) -> int | None:
    match = re.search(r"_Set_(\d+)_", fname)
    return int(match.group(1)) if match else None


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
            set_num = parse_set_from_filename(fname)
            items.append((set_num, student_folder, fname, full_path))
    return items


def rebuild_combined_zip():
    all_items = iter_all_audio_files()
    with zipfile.ZipFile(BUNDLE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for _, student_folder, fname, full_path in all_items:
            zf.write(full_path, arcname=os.path.join(student_folder, fname))


def listen_speaker(lines: list[str], key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    payload = json.dumps(lines)
    components.html(
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
    )


def mic_recorder_widget(set_no: int, key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    components.html(
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
        let rec_{safe_id} = null;
        let stream_{safe_id} = null;
        let chunks_{safe_id} = [];
        let iv_{safe_id} = null;
        let sec_{safe_id} = 0;

        function fmt_{safe_id}(s) {{
            return String(Math.floor(s/60)).padStart(2,"0") + ":" + String(s%60).padStart(2,"0");
        }}

        function findAudioPayloadInput_{safe_id}() {{
            try {{
                const doc = window.parent ? window.parent.document : document;
                const inputs = doc.querySelectorAll('input[aria-label="AUDIO_PAYLOAD_BRIDGE"]');
                return inputs.length > 0 ? inputs[0] : null;
            }} catch (e) {{
                return null;
            }}
        }}

        function setReactInputValue_{safe_id}(el, nextVal) {{
            if (!el) return false;
            try {{
                const prevVal = el.value;
                const proto = window.parent && window.parent.HTMLInputElement
                    ? window.parent.HTMLInputElement.prototype
                    : HTMLInputElement.prototype;
                const nativeSetter = Object.getOwnPropertyDescriptor(proto, "value").set;
                nativeSetter.call(el, nextVal);
                if (el._valueTracker) {{
                    el._valueTracker.setValue(prevVal);
                }}
                el.focus();
                el.dispatchEvent(new Event("input", {{ bubbles: true }}));
                el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                el.blur();
                return true;
            }} catch (e) {{
                return false;
            }}
        }}

        function writeAudioBridge_{safe_id}(b64, mime) {{
            const target = findAudioPayloadInput_{safe_id}();
            if (!target) return false;
            const val = b64 ? JSON.stringify({{ set_no: {set_no}, b64: b64, mime: mime }}) : "";
            return setReactInputValue_{safe_id}(target, val);
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
                stat.textContent = "Preparing recording...";
                return;
            }}
            try {{
                stream_{safe_id} = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                chunks_{safe_id} = [];
                writeAudioBridge_{safe_id}("", "audio/webm");
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
                        if (!b64) {{
                            stat.textContent = "Could not read audio";
                            return;
                        }}
                        const ok = writeAudioBridge_{safe_id}(b64, mime);
                        stat.textContent = ok
                            ? "Audio ready — tap Save Recording below"
                            : "Bridge blocked by browser frame";
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
        height=120,
    )


if "sp_set_idx" not in st.session_state:
    st.session_state.sp_set_idx = 0
if "last_saved_msg" not in st.session_state:
    st.session_state.last_saved_msg = ""
if "last_error_msg" not in st.session_state:
    st.session_state.last_error_msg = ""

st.title("🎙️ Speaking Practice Recorder")
student_name = st.text_input("Your Name:", placeholder="Write your name here...")

set_idx = st.session_state.sp_set_idx
set_no, qs = SPEAKING_SETS[set_idx]

st.progress((set_idx + 1) / len(SPEAKING_SETS), text=f"Set {set_no} of {len(SPEAKING_SETS)}")
st.subheader(f"Set {set_no}")
st.caption("Answer each question in one sentence, tap Listen or Mic, and click Save Recording.")

for idx, q in enumerate(qs, start=1):
    st.markdown(f"**{idx}. {html.escape(q)}**")

listen_speaker(qs, key_id=f"spk_{set_no}")
mic_recorder_widget(set_no=set_no, key_id=f"mic_{set_no}")

audio_payload_raw = st.text_input(
    "AUDIO_PAYLOAD_BRIDGE",
    key=f"audio_bridge_{set_no}",
    label_visibility="collapsed",
)

if st.button("💾 Save Recording", type="primary", key=f"save_btn_{set_no}"):
    st.session_state.last_error_msg = ""
    payload_data = None
    if audio_payload_raw:
        try:
            payload_data = json.loads(audio_payload_raw)
        except Exception:
            payload_data = None

    if not payload_data or not payload_data.get("b64"):
        st.session_state.last_error_msg = (
            "No recording captured yet. Tap 🎙️ Mic, speak, tap ⏹ Stop, wait for 'Audio ready', and then click 💾 Save Recording."
        )
    else:
        clean_student = sanitize_filename_part(student_name)
        target_set = int(payload_data.get("set_no") or set_no)
        ext = ext_from_mime(payload_data.get("mime") or "audio/webm")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        student_dir = os.path.join(SAVE_DIR, clean_student)
        os.makedirs(student_dir, exist_ok=True)
        out_name = f"{clean_student}_Set_{target_set:02d}_{stamp}{ext}"
        out_path = os.path.join(student_dir, out_name)

        try:
            raw_bytes = base64.b64decode(payload_data["b64"])
            with open(out_path, "wb") as f:
                f.write(raw_bytes)
            rebuild_combined_zip()
            st.session_state.last_saved_msg = (
                f"Saved `{clean_student}`'s voice clip for **Set {target_set}** (`{out_name}`)."
            )
            st.rerun()
        except Exception as e:
            st.session_state.last_error_msg = f"Could not save audio: {e}"

if st.session_state.last_error_msg:
    st.warning(st.session_state.last_error_msg)

if st.session_state.last_saved_msg:
    st.success(st.session_state.last_saved_msg)

col_prev, col_next = st.columns(2)
with col_prev:
    if st.button("⬅️ Previous Set", disabled=(set_idx == 0)):
        st.session_state.sp_set_idx = max(0, set_idx - 1)
        st.session_state.last_saved_msg = ""
        st.session_state.last_error_msg = ""
        st.rerun()
with col_next:
    if st.button("Next Set ➡️", disabled=(set_idx == len(SPEAKING_SETS) - 1)):
        st.session_state.sp_set_idx = min(len(SPEAKING_SETS) - 1, set_idx + 1)
        st.session_state.last_saved_msg = ""
        st.session_state.last_error_msg = ""
        st.rerun()

all_recordings = iter_all_audio_files()
current_set_recordings = [item for item in all_recordings if item[0] == set_no]

st.divider()
st.markdown(f"### Set {set_no} — All Student Recordings ({len(current_set_recordings)})")
if current_set_recordings:
    for order_num, (_, s_name, fname, fpath) in enumerate(current_set_recordings, start=1):
        st.markdown(f"**{order_num}. {html.escape(s_name)}** — `{html.escape(fname)}`")
        st.audio(fpath)
else:
    st.caption(f"No voice clips saved for Set {set_no} yet. Record and click Save Recording to add the first one.")

if os.path.exists(BUNDLE_PATH) and all_recordings:
    st.divider()
    with open(BUNDLE_PATH, "rb") as zf_in:
        st.download_button(
            label="📦 Download All Recordings Across All Sets (ZIP)",
            data=zf_in.read(),
            file_name="all_speaking_recordings.zip",
            mime="application/zip",
        )
