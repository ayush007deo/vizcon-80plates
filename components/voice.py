"""Voice narration for the guided journey.

Prefers a pre-generated Amazon Polly (generative-voice) MP3 when one exists for the
passage — a warm, human, documentary-style narrator. When no audio file is available
(e.g. dynamically generated text), it falls back to the browser's built-in Web Speech
API so narration always works. Both are rendered inside an iframe (components.html) so
their JavaScript runs and audio can autoplay on click.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit.components.v1 as components

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def narrate(text: str, *, label: str = "Listen to this story", audio_file: str | None = None,
            auto: bool = False, rate: float = 1.05, pitch: float = 1.06,
            height: int = 66) -> None:
    """Render a narration control.

    audio_file : optional path (relative to the project root) to a pre-generated MP3.
                 If it exists, a real audio player is shown; otherwise we fall back to
                 the Web Speech API reading `text`.
    """
    if audio_file:
        path = Path(audio_file)
        if not path.is_absolute():
            path = _PROJECT_ROOT / audio_file
        if path.exists() and path.stat().st_size > 0:
            _render_audio_player(path, label, height)
            return
    _render_webspeech(text, label=label, auto=auto, rate=rate, pitch=pitch, height=height)


def _render_audio_player(path: Path, label: str, height: int) -> None:
    """A themed play/pause bar backed by a pre-generated MP3 (embedded as a data URI)."""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    label_js = json.dumps(label)
    components.html(
        f"""
        <!doctype html><html><head><meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;700&display=swap" rel="stylesheet">
        <style>
          html,body {{ margin:0; padding:0; background:transparent;
            font-family:'Inter',system-ui,sans-serif; }}
          .vn {{ display:flex; align-items:center; gap:12px; }}
          .vn-btn {{ display:inline-flex; align-items:center; gap:9px; cursor:pointer;
            border:none; border-radius:999px; padding:10px 18px; font-weight:700;
            font-size:0.86rem; color:#fff;
            background:linear-gradient(135deg,#C0392B,#E8A317);
            box-shadow:0 6px 18px rgba(192,57,43,0.28); transition:all .18s ease; }}
          .vn-btn:hover {{ transform:translateY(-2px); box-shadow:0 10px 24px rgba(192,57,43,0.36); }}
          .vn-wave {{ display:none; align-items:flex-end; gap:3px; height:20px; }}
          .vn-wave.on {{ display:flex; }}
          .vn-wave i {{ width:3px; background:linear-gradient(180deg,#E8A317,#C0392B);
            border-radius:2px; animation:vnbar 0.9s ease-in-out infinite; }}
          .vn-wave i:nth-child(1){{height:8px;animation-delay:0s}}
          .vn-wave i:nth-child(2){{height:16px;animation-delay:.1s}}
          .vn-wave i:nth-child(3){{height:11px;animation-delay:.2s}}
          .vn-wave i:nth-child(4){{height:19px;animation-delay:.3s}}
          .vn-wave i:nth-child(5){{height:9px;animation-delay:.15s}}
          @keyframes vnbar {{ 0%,100%{{transform:scaleY(0.4)}} 50%{{transform:scaleY(1)}} }}
          .vn-note {{ color:#1F6F5C; font-size:0.7rem; font-weight:700; }}
        </style></head>
        <body>
          <div class="vn">
            <button class="vn-btn" id="p"><span id="ic">🔊</span><span id="lb"></span></button>
            <div class="vn-wave" id="w"><i></i><i></i><i></i><i></i><i></i></div>
            <span class="vn-note">Narrated voice</span>
          </div>
          <audio id="a" src="data:audio/mp3;base64,{b64}" preload="auto"></audio>
          <script>
            const a=document.getElementById('a'), p=document.getElementById('p'),
                  w=document.getElementById('w'), ic=document.getElementById('ic'),
                  lb=document.getElementById('lb');
            lb.textContent = {label_js};
            p.addEventListener('click', () => {{
              if (a.paused) {{ a.play(); }} else {{ a.pause(); }}
            }});
            a.addEventListener('play', () => {{ w.classList.add('on'); ic.textContent='⏸'; }});
            a.addEventListener('pause', () => {{ w.classList.remove('on'); ic.textContent='🔊'; }});
            a.addEventListener('ended', () => {{ w.classList.remove('on'); ic.textContent='🔊'; }});
          </script>
        </body></html>
        """,
        height=height,
    )


def _render_webspeech(text: str, *, label: str, auto: bool, rate: float, pitch: float,
                      height: int) -> None:
    payload = json.dumps(text)
    label_js = json.dumps(label)
    auto_js = "true" if auto else "false"
    rate_js = f"{rate:.3f}"
    pitch_js = f"{pitch:.3f}"

    components.html(
        f"""
        <!doctype html><html><head><meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;700&display=swap" rel="stylesheet">
        <style>
          html,body {{ margin:0; padding:0; background:transparent;
            font-family:'Inter',system-ui,sans-serif; }}
          .vn {{ display:flex; align-items:center; gap:12px; }}
          .vn-btn {{ display:inline-flex; align-items:center; gap:9px; cursor:pointer;
            border:none; border-radius:999px; padding:10px 18px; font-weight:700;
            font-size:0.86rem; color:#fff;
            background:linear-gradient(135deg,#C0392B,#E8A317);
            box-shadow:0 6px 18px rgba(192,57,43,0.28); transition:all .18s ease; }}
          .vn-btn:hover {{ transform:translateY(-2px); box-shadow:0 10px 24px rgba(192,57,43,0.36); }}
          .vn-btn:disabled {{ opacity:0.5; cursor:default; transform:none; box-shadow:none; }}
          .vn-ico {{ font-size:1.05rem; line-height:1; }}
          .vn-wave {{ display:none; align-items:flex-end; gap:3px; height:20px; }}
          .vn-wave.on {{ display:flex; }}
          .vn-wave i {{ width:3px; background:linear-gradient(180deg,#E8A317,#C0392B);
            border-radius:2px; animation:vnbar 0.9s ease-in-out infinite; }}
          .vn-wave i:nth-child(1){{height:8px;animation-delay:0s}}
          .vn-wave i:nth-child(2){{height:16px;animation-delay:.1s}}
          .vn-wave i:nth-child(3){{height:11px;animation-delay:.2s}}
          .vn-wave i:nth-child(4){{height:19px;animation-delay:.3s}}
          .vn-wave i:nth-child(5){{height:9px;animation-delay:.15s}}
          @keyframes vnbar {{ 0%,100%{{transform:scaleY(0.4)}} 50%{{transform:scaleY(1)}} }}
          .vn-stop {{ display:none; cursor:pointer; border:1px solid #E7D6B8; background:#FFF;
            color:#8A3324; border-radius:999px; padding:8px 14px; font-weight:700; font-size:0.8rem; }}
          .vn-stop.on {{ display:inline-block; }}
          .vn-note {{ color:#9A8C7A; font-size:0.72rem; }}
        </style></head>
        <body>
          <div class="vn">
            <button class="vn-btn" id="vnPlay"><span class="vn-ico">🔊</span><span id="vnLabel"></span></button>
            <div class="vn-wave" id="vnWave"><i></i><i></i><i></i><i></i><i></i></div>
            <button class="vn-stop" id="vnStop">■ Stop</button>
            <span class="vn-note" id="vnNote"></span>
          </div>
          <script>
            const TEXT = {payload};
            const LABEL = {label_js};
            const AUTO = {auto_js};
            const synth = window.speechSynthesis;
            const play = document.getElementById('vnPlay');
            const stop = document.getElementById('vnStop');
            const wave = document.getElementById('vnWave');
            const note = document.getElementById('vnNote');
            document.getElementById('vnLabel').textContent = LABEL;

            if (!synth) {{
              play.disabled = true;
              note.textContent = 'Voice not supported in this browser.';
            }}

            // Rank voices so we pick the most natural, warm one available.
            // Names vary by OS/browser: Google & Apple "premium/enhanced" voices and
            // modern natural voices sound far less robotic than the default.
            const PREFERRED = [
              'Google UK English Female','Google US English','Google UK English Male',
              'Samantha','Ava','Allison','Serena','Zoe','Karen','Moira','Fiona','Tessa',
              'Microsoft Aria','Microsoft Jenny','Microsoft Libby','Microsoft Sonia',
              'Natural','Premium','Enhanced'
            ];
            function pickVoice() {{
              const vs = synth.getVoices();
              if (!vs || !vs.length) return null;
              const en = vs.filter(v => /^en/i.test(v.lang));
              const pool = en.length ? en : vs;
              for (const pref of PREFERRED) {{
                const hit = pool.find(v => v.name.toLowerCase().includes(pref.toLowerCase()));
                if (hit) return hit;
              }}
              // Prefer a local, non-default en-GB/US voice, else first English voice.
              return pool.find(v => /en[-_]?(GB|US)/i.test(v.lang)) || pool[0];
            }}

            const BASE_RATE = {rate_js};
            const BASE_PITCH = {pitch_js};

            function splitSentences(t) {{
              // Keep the punctuation so the engine phrases each clause naturally.
              const m = t.match(/[^.!?…]+[.!?…]*/g);
              return (m || [t]).map(s => s.trim()).filter(Boolean);
            }}

            function speak() {{
              if (!synth) return;
              synth.cancel();
              const v = pickVoice();
              const parts = splitSentences(TEXT);
              wave.classList.add('on'); stop.classList.add('on');
              parts.forEach((sentence, i) => {{
                const u = new SpeechSynthesisUtterance(sentence);
                if (v) u.voice = v;
                u.lang = (v && v.lang) || 'en-GB';
                // Gentle, musical rise-and-fall so it doesn't sound flat/monotone.
                const wobble = Math.sin(i * 1.3);          // -1..1, varies per sentence
                const isShort = sentence.split(' ').length <= 6;
                u.rate = BASE_RATE + wobble * 0.05 + (isShort ? 0.02 : 0);
                u.pitch = BASE_PITCH + wobble * 0.10 + (sentence.includes('!') ? 0.06 : 0);
                u.volume = 1.0;
                if (i === parts.length - 1) {{
                  u.onend = () => {{ wave.classList.remove('on'); stop.classList.remove('on'); }};
                }}
                u.onerror = () => {{ wave.classList.remove('on'); stop.classList.remove('on'); }};
                synth.speak(u);   // utterances queue and play in order
              }});
            }}

            play.addEventListener('click', speak);
            stop.addEventListener('click', () => {{ synth.cancel();
              wave.classList.remove('on'); stop.classList.remove('on'); }});

            // Some browsers load voices asynchronously.
            if (synth && synth.onvoiceschanged !== undefined) {{
              synth.onvoiceschanged = () => {{ if (AUTO && !synth.speaking) {{ /* ready */ }} }};
            }}
            if (AUTO) {{ setTimeout(speak, 400); }}
          </script>
        </body></html>
        """,
        height=height,
    )
