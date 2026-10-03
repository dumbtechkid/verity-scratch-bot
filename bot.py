import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv
import scratchattach as sa

load_dotenv()

SCRATCH_USERNAME   = os.environ.get("SCRATCH_USERNAME", "")
SCRATCH_PASSWORD   = os.environ.get("SCRATCH_PASSWORD", "")
SCRATCH_PROJECT_ID = os.environ.get("SCRATCH_PROJECT_ID", "")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
GROQ_MODEL         = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
PORT               = int(os.environ.get("PORT", 8080))

INPUT_VAR  = "INPUT"
OUTPUT_VAR = "OUTPUT"

KEY_CHARS = list(
    "abcdefghijklmnopqrstuvwxyz "
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    ".,?!:;'\"()-/+=*@#%_&"
)
MAX_RESPONSE_CHARS = 127

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("VerityCloudBot")


def encode(text: str) -> str:
    replacements = {
        "’": "'", "‘": "'", "`": "'",
        "“": '"', "”": '"',
        "—": "-", "–": "-",
        "²": "2", "³": "3",
        "\n": " ", "\r": " ", "\t": " ",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)

    result = "1"
    for ch in text:
        try:
            idx = KEY_CHARS.index(ch) + 1
            result += str(idx).zfill(2)
        except ValueError:
            pass
    return result


def decode(raw_value) -> str:
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
        return


def start_health_server(port):
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    log.info(f"Health check HTTP server listening on port {port}.")
    server.serve_forever()


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are Verity, a friendly, intelligent, and helpful AI assistant. "
    "Speak naturally, normally, and conversationally. "
    "Do NOT use weird roleplay, gibberish, exaggerated slang, or repetitive mannerisms. "
    "Answer questions directly, accurately, and clearly. "
    "Use only standard plain text (no emojis or unicode symbols). "
    "Keep every response strictly under 120 characters and do not use newlines."
)
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def ask_ai(question: str) -> str:
    global chat_history

    models_to_try = [GROQ_MODEL]
    for fallback in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    if len(chat_history) > 11:
        chat_history = [chat_history[0]] + chat_history[-10:]

    chat_history.append({"role": "user", "content": question})
    answer = None

    for model_name in models_to_try:
        try:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": chat_history,
            }
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                answer = data["choices"][0]["message"]["content"].strip()
                chat_history.append({"role": "assistant", "content": answer})
                break
            else:
                log.warning(f"Model {model_name} status {res.status_code}: {res.text}")
        except Exception as e:
            log.warning(f"Model {model_name} error ({e}), trying fallback...")

    if not answer:
        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
        answer = "Sorry, I could not get a response. Please try again."

    if len(answer) > MAX_RESPONSE_CHARS:
        answer = answer[:MAX_RESPONSE_CHARS - 3] + "..."

    return answer


def run_scratch_loop():
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

                try:
                    cloud.set_var(OUTPUT_VAR, "0")
                except Exception as e:
                    log.warning(f"Could not reset OUTPUT to 0: {e}")

                answer = ask_ai(question)
                log.info(f"Answer: {answer!r}")

                encoded = encode(answer)
                try:
                    cloud.set_var(OUTPUT_VAR, encoded)
                    log.info(f"Sent {len(encoded)} digits to ☁ {OUTPUT_VAR}")
                except Exception as err:
                    log.warning(f"cloud.set_var error: {err}. Retrying once...")
                    try:
                        time.sleep(0.3)
                        cloud.set_var(OUTPUT_VAR, encoded)
                        log.info(f"Retry sent {len(encoded)} digits to ☁ {OUTPUT_VAR}")
                    except Exception as err2:
                        log.error(f"Failed to send to cloud var: {err2}")

            log.info("Listening for Scratch cloud events...")
            events.start(thread=False)

        except Exception as e:
            log.error(f"Scratch connection dropped: {e}")
            log.info("Reconnecting in 10 seconds...")
            time.sleep(10)


def main():
    log.info("Starting Verity 24/7 Cloud Service...")

    if not all([SCRATCH_USERNAME, SCRATCH_PASSWORD, SCRATCH_PROJECT_ID, GROQ_API_KEY]):
        log.error("Missing required environment variables! Check .env or cloud config.")
        return

    health_thread = threading.Thread(target=start_health_server, args=(PORT,), daemon=True)
    health_thread.start()

    run_scratch_loop()


if __name__ == "__main__":
    main()
