"""Pretends to be Twilio ConversationRelay so you can test without a phone number.

Start the server first (python main.py), then in another terminal:

    python test_local.py
    python test_local.py "your own question" "and another"
"""
import asyncio
import json
import os
import sys

import websockets
from dotenv import load_dotenv

load_dotenv()

WS_URL = f"ws://localhost:{os.getenv('PORT', '8080')}/ws"

PROMPTS = sys.argv[1:] or [
    "Hello, who are you?",
    "What is two hundred plus fifty?",
    "What did I just ask you?",  # checks the chat session keeps history
]


async def main():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": "CAtest123"}))

        for prompt in PROMPTS:
            await ws.send(json.dumps({"type": "prompt", "voicePrompt": prompt}))
            reply = json.loads(await ws.recv())
            assert reply["type"] == "text", reply
            assert reply["last"] is True, reply
            assert reply["token"].strip(), "empty reply from Gemini"
            print(f"\n  YOU: {prompt}\nGEMINI: {reply['token']}")

    print("\nOK - setup, prompt, reply and history all work.")


if __name__ == "__main__":
    asyncio.run(main())
