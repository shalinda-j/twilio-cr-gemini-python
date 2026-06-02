# main.py
import os
import json
import uvicorn
from urllib.parse import parse_qs

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response, JSONResponse
from dotenv import load_dotenv

import google.generativeai as genai

# -----------------------------
# Environment / Config
# -----------------------------
load_dotenv()

PORT = int(os.getenv("PORT", "8080"))

DOMAIN = os.getenv("NGROK_URL")  # e.g. postallantoic-audrianna-cognately.ngrok-free.dev
if not DOMAIN:
    raise ValueError("NGROK_URL environment variable not set.")

# Twilio ConversationRelay expects a secure WS endpoint (wss)
WS_URL = f"wss://{DOMAIN}/ws"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

WELCOME_GREETING = (
    "Hi! I am a voice assistant powered by Twilio and Google Gemini. Ask me anything!"
)

SYSTEM_PROMPT = """You are a helpful and friendly voice assistant. This conversation is happening over a phone call, so your responses will be spoken aloud.
Please adhere to the following rules:
1. Provide clear, concise, and direct answers.
2. Spell out all numbers (e.g., say 'one thousand two hundred' instead of 1200).
3. Do not use any special characters like asterisks, bullet points, or emojis.
4. Keep the conversation natural and engaging.
"""

# -----------------------------
# Gemini setup
# -----------------------------
genai.configure(api_key=GOOGLE_API_KEY)

# Use a fast model; the system prompt is passed as a system instruction
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-native-audio-preview-09-2025",
    system_instruction=SYSTEM_PROMPT,
)

# In-memory chat sessions by CallSid
sessions = {}

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()


async def gemini_response(chat_session, user_prompt: str) -> str:
    """Call Gemini asynchronously and return plain text."""
    resp = await chat_session.send_message_async(user_prompt)
    return (resp.text or "").strip()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/twiml")
async def twiml_endpoint():
    """
    Returns TwiML for inbound calls.
    Twilio will fetch this, see <ConversationRelay>, and then open a WS to /ws.
    """
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay
      url="{WS_URL}"
      welcomeGreeting="{WELCOME_GREETING}"
      ttsProvider="ElevenLabs"
      voice="FGY2WhTYpPnrIDTdsKH5" />
  </Connect>
</Response>"""
    # IMPORTANT: return text/xml
    return Response(content=xml_response, media_type="text/xml")


@app.post("/twilio")
async def twilio_endpoint():
    """
    Generic /twilio endpoint for backward compatibility.
    Returns the same TwiML as /twiml endpoint.
    """
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay
      url="{WS_URL}"
      welcomeGreeting="{WELCOME_GREETING}"
      ttsProvider="ElevenLabs"
      voice="FGY2WhTYpPnrIDTdsKH5" />
  </Connect>
</Response>"""
    return Response(content=xml_response, media_type="text/xml")


@app.post("/twilio/voice")
async def twilio_voice_endpoint():
    """
    Alternate endpoint for Twilio voice webhook.
    Returns the same TwiML as /twiml endpoint.
    """
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay
      url="{WS_URL}"
      welcomeGreeting="{WELCOME_GREETING}"
      ttsProvider="ElevenLabs"
      voice="FGY2WhTYpPnrIDTdsKH5" />
  </Connect>
</Response>"""
    return Response(content=xml_response, media_type="text/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint used by Twilio ConversationRelay.
    Messages (JSON) we expect:
      - {"type":"setup","callSid":"CA..."}
      - {"type":"prompt","voicePrompt":"..."}
      - {"type":"interrupt"}  (optional)
    """
    await websocket.accept()
    call_sid = None

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except Exception:
                print("⚠️  Received non-JSON WS message:", msg)
                continue

            mtype = payload.get("type")
            if mtype == "setup":
                call_sid = payload.get("callSid")
                print(f"🔗 WS setup for CallSid={call_sid}")
                sessions[call_sid] = model.start_chat(history=[])  # fresh session

            elif mtype == "prompt":
                if not call_sid or call_sid not in sessions:
                    print(f"❌ Prompt received for unknown CallSid={call_sid}")
                    continue

                user_prompt = (payload.get("voicePrompt") or "").strip()
                print(f"🎙️  User: {user_prompt}")

                chat = sessions[call_sid]
                try:
                    reply = await gemini_response(chat, user_prompt)
                except Exception as e:
                    print("❌ Gemini error:", repr(e))
                    reply = "I'm sorry, I had trouble answering that. Could you please repeat?"

                # Send final chunk as a single 'text' message; ConversationRelay will TTS it.
                await websocket.send_text(
                    json.dumps({"type": "text", "token": reply, "last": True})
                )
                print(f"🗣️  Assistant: {reply}")

            elif mtype == "interrupt":
                print(f"⏸️  Interruption for CallSid={call_sid} (no-op)")

            else:
                print("ℹ️  Unknown WS message type:", mtype, "payload=", payload)

    except WebSocketDisconnect:
        print(f"🔌 WS disconnected for CallSid={call_sid}")
    finally:
        if call_sid and call_sid in sessions:
            sessions.pop(call_sid, None)
            print(f"🧹 Cleared session for CallSid={call_sid}")


@app.post("/twilio/call-status")
async def twilio_call_status(request: Request):
    """
    Twilio StatusCallback for call progress events.
    Twilio Voice sends application/x-www-form-urlencoded by default.
    We also accept JSON just in case.
    Always return 200 so Twilio won't retry.
    """
    try:
        ctype = (request.headers.get("content-type") or "").lower()

        if "application/x-www-form-urlencoded" in ctype:
            form = await request.form()
            data = dict(form)
        elif "application/json" in ctype:
            data = await request.json()
        else:
            # Fallback: parse raw querystring-like body
            raw = await request.body()
            parsed = parse_qs(raw.decode("utf-8", errors="ignore"))
            data = {k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
                    for k, v in parsed.items()}

        # Compact, useful log line
        print(
            "📫 StatusCallback:",
            f"sid={data.get('CallSid')}",
            f"status={data.get('CallStatus')}",
            f"from={data.get('From')}",
            f"to={data.get('To')}",
        )
        # Uncomment for full payload:
        # print("Full payload:", data)

        return Response(status_code=200)

    except Exception as e:
        raw = await request.body()
        print("❌ Error handling /twilio/call-status")
        print("   Exception:", repr(e))
        print("   Content-Type:", request.headers.get("content-type"))
        print("   Raw body:", raw.decode("utf-8", errors="ignore"))
        return JSONResponse(status_code=200, content={"message": "Error logged"})


if __name__ == "__main__":
    print(f"Starting server on port {PORT}")
    print(f"Twilio should call TwiML at: https://{DOMAIN}/twiml  (POST)")
    print(f"Twilio WS will connect to:  {WS_URL}")
    print(f"Call status callback at:    https://{DOMAIN}/twilio/call-status  (POST)")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
