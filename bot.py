"""
Scratch AI Backend — Stage 2 (24/7 Cloud Deployment)
====================================================
Designed to run continuously on free cloud hosts (Koyeb, Hugging Face Spaces,
Render, Railway, Fly.io) with:
1. Self-healing auto-reconnect loop (never crashes on disconnects).
2. Embedded lightweight HTTP health check on $PORT (keeps hosting providers happy).
3. OpenRouter multi-model fallback with fast free models.
4. Verity Minecraft system prompt with 127-character response limit.
5. Guaranteed delivery with retry logic for Scratch cloud variables.
"""

import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv
import scratchattach as sa

# ── Load environment variables ──────────────────────────────────
load_dotenv()

SCRATCH_USERNAME   = os.environ.get("SCRATCH_USERNAME", "")
SCRATCH_PASSWORD   = os.environ.get("SCRATCH_PASSWORD", "")
SCRATCH_PROJECT_ID = os.environ.get("SCRATCH_PROJECT_ID", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.environ.get("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")
PORT               = int(os.environ.get("PORT", 8080))

# Cloud variable names (must exactly match Scratch project)
INPUT_VAR  = "INPUT"
OUTPUT_VAR = "OUTPUT"

# ── Encoding key (identical to generate_scratch.py) ──────────────
KEY_CHARS = list(
    "abcdefghijklmnopqrstuvwxyz "   # codes 01-27
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"    # codes 28-53
    "0123456789"                     # codes 54-63
    ".,?!:;'\"()-/+=*@#%_&"         # codes 64-83
)
MAX_RESPONSE_CHARS = 127

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("VerityCloudBot")


# ══════════════════════════════════════════════════════════════════
# Encoding / Decoding
# ══════════════════════════════════════════════════════════════════

def encode(text: str) -> str:
    """Encode text string into numeric cloud-safe string with sentinel '1'."""
    result = "1"
    for ch in text:
        if ch == "\n":
            ch = " "
        try:
            idx = KEY_CHARS.index(ch) + 1
            result += str(idx).zfill(2)
        except ValueError:
            pass
    return result


def decode(raw_value) -> str:
    """Decode numeric string back to plaintext."""
    num_str = str(raw_value).strip()
    if "." in num_str:
        num_str = num_str.split(".")[0]
    if len(num_str) < 3:
        return ""
    data = num_str[1:]
    result = ""
    for i in range(0, len(data) - 1, 2):
        chunk = data[i : i + 2]
        try:
            idx = int(chunk) - 1
            if 0 <= idx < len(KEY_CHARS):
                result += KEY_CHARS[idx]
        except ValueError:
            pass
    return result


# ══════════════════════════════════════════════════════════════════
# Embedded HTTP Health Check Server
# ══════════════════════════════════════════════════════════════════

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            "<html><body style='font-family:sans-serif; text-align:center; padding:50px; background:#f4f6f8;'>"
            "<h1>🤖 Verity Scratch AI Bot is Live!</h1>"
            "<p>Connected to Scratch project <b>" + str(SCRATCH_PROJECT_ID) + "</b></p>"
            "<p style='color:green; font-weight:bold;'>Status: 24/7 Online</p>"
            "</body></html>"
        )
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        # Silence access logs to keep console clean
        return


def start_health_server(port):
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    log.info(f"Health check HTTP server listening on port {port}.")
    server.serve_forever()


# ══════════════════════════════════════════════════════════════════
# OpenRouter AI Logic
# ══════════════════════════════════════════════════════════════════

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_PROMPT = "act like verity, the minecraft one. and also keep responses STRICTLY within 127 characters"
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def ask_ai(question: str) -> str:
    """Call OpenRouter with multi-model fallback and auto-pruning."""
    global chat_history

    models_to_try = [OPENROUTER_MODEL]
    for fallback in [
        "liquid/lfm-2.5-2.6b:free",
        "apodex/apodex-1.1-mini:free",
        "qwen/qwen3.8-27b:free",
    ]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    # Prune history if it exceeds 10 turns to keep cloud memory clean
    if len(chat_history) > 11:
        chat_history = [chat_history[0]] + chat_history[-10:]

    chat_history.append({"role": "user", "content": question})
    answer = None

    for model_name in models_to_try:
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://scratch.mit.edu",
                "X-Title": "Scratch Verity AI",
            }
            payload = {
                "model": model_name,
                "messages": chat_history,
            }
            res = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                answer = data["choices"][0]["message"]["content"].strip()
                chat_history.append({"role": "assistant", "content": answer})
                break
            else:
                log.warning(f"Model {model_name} status {res.status_code}, trying fallback...")
        except Exception as e:
            log.warning(f"Model {model_name} error/timeout ({e}), trying fallback...")

    if not answer:
        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
        answer = "Sorry, I could not get a response. Please try again."

    if len(answer) > MAX_RESPONSE_CHARS:
        answer = answer[:MAX_RESPONSE_CHARS - 3] + "..."

    return answer


# ══════════════════════════════════════════════════════════════════
# Scratch Cloud Manager (Self-Healing Loop)
# ══════════════════════════════════════════════════════════════════

def run_scratch_loop():
    """Runs the Scratch event listener with automatic reconnection on drops."""
    import warnings
    warnings.filterwarnings("ignore", category=sa.LoginDataWarning)

    last_raw = None

    while True:
        try:
            log.info("Connecting to Scratch session...")
            session = sa.login(SCRATCH_USERNAME, SCRATCH_PASSWORD)
            cloud = session.connect_cloud(SCRATCH_PROJECT_ID)
            log.info(f"Connected to Scratch project {SCRATCH_PROJECT_ID} as '{SCRATCH_USERNAME}'.")

            events = cloud.events()

            @events.event
            def on_set(activity):
                nonlocal last_raw
                if activity.var != INPUT_VAR:
                    return

                raw_val = str(activity.value).strip()
                if raw_val == last_raw or raw_val in ("", "0"):
                    return
                last_raw = raw_val

                question = decode(raw_val)
                if not question.strip():
                    return

                log.info(f"Question: {question!r}")
                answer = ask_ai(question)
                log.info(f"Answer: {answer!r}")

                encoded = encode(answer)
                for attempt in range(3):
                    try:
                        cloud.set_var(OUTPUT_VAR, encoded)
                        time.sleep(0.2)
                    except Exception as err:
                        log.warning(f"cloud.set_var error (attempt {attempt+1}): {err}")
                        time.sleep(0.4)
                log.info(f"Broadcasted {len(encoded)} digits to ☁ {OUTPUT_VAR}")

            log.info("Listening for Scratch cloud events...")
            events.start(thread=False)

        except Exception as e:
            log.error(f"Scratch connection dropped: {e}")
            log.info("Reconnecting in 10 seconds...")
            time.sleep(10)


# ══════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════

def main():
    log.info("Starting Verity 24/7 Cloud Service...")

    if not all([SCRATCH_USERNAME, SCRATCH_PASSWORD, SCRATCH_PROJECT_ID, OPENROUTER_API_KEY]):
        log.error("Missing required environment variables! Check .env or cloud config.")
        return

    # Start health check server on background daemon thread
    health_thread = threading.Thread(target=start_health_server, args=(PORT,), daemon=True)
    health_thread.start()

    # Run the self-healing Scratch loop on the main thread
    run_scratch_loop()


if __name__ == "__main__":
    main()
