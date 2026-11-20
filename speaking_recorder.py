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

# Replace or add your sets here: (set_number, [q1, q2, q3])
SPEAKING_SETS = [
    (1, ["What's your name?", "Where are you from?", "How do you spell it?"]),
    (2, ["Are you on holiday?", "Are you late?", "Are you from England?"]),
]


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


def save_button(set_no: int, student_name: str, key_id: str):
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", key_id)
    clean_name = re.sub(r"[^A-Za-z0-9_-]", "_", (student_name or "").strip()) or "Student"
    render_html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;font-family:sans-serif;">
            <button type="button" onclick="saveVoice_{safe_id}()"
                style="background:#059669;color:#fff;border:none;padding:9px 18px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">
                💾 Save
            </button>
            <span id="save_msg_{safe_id}" style="color:#4ADE80;font-size:13px;font-weight:600;"></span>
        </div>
        <script>
        function saveVoice_{safe_id}() {{
            const msg = document.getElementById("save_msg_{safe_id}");
            const store = (window.top && window.top.__savedVoice) ? window.top.__savedVoice[{set_no}] : null;
            if (!store || !store.base64) {{
                msg.style.color = "#F87171";
                msg.textContent = "Record with Mic first, then tap Save.";
                return;
            }}
            const targetWin = window.top || window;
            const url = new URL(targetWin.location.href);
            url.searchParams.set("save_set", String({set_no}));
            url.searchParams.set("student", {json.dumps(clean_name)});
            url.searchParams.set("ts", String(Date.now()));
            if (!window.top.__pendingUpload) window.top.__pendingUpload = {{}};
            window.top.__pendingUpload[{set_no}] = store.base64;
            targetWin.location.assign(url.toString());
        }}
        </script>
        """,
        height=46,
        alt="Save button",
    )


st.title("🎙️ Speaking Practice Recorder")
student_name = st.text_input("Your Name:", placeholder="Write your name here...")

set_no, qs = SPEAKING_SETS[0]
st.subheader(f"Set {set_no}")
st.caption("Answer each question in one sentence, record your voice, and tap Save.")
for idx, q in enumerate(qs, start=1):
    st.markdown(f"**{idx}. {html.escape(q)}**")

listen_speaker(qs, key_id=f"spk_{set_no}")
mic_box(set_no=set_no, key_id=f"mic_{set_no}")
save_button(set_no=set_no, student_name=student_name, key_id=f"save_{set_no}")

saved_files = sorted(os.listdir(SAVE_DIR))
if saved_files:
    st.divider()
    st.markdown("### Saved Recordings")
    for fname in saved_files:
        fpath = os.path.join(SAVE_DIR, fname)
        st.write(fname)
        st.audio(fpath)
