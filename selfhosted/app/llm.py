# llm.py - Gemini wrapper. One chat session per phone call keeps context.
import warnings

# The google.generativeai package prints a noisy deprecation FutureWarning on
# import; it still works fine. Silence it so container logs stay clean.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import google.generativeai as genai

from . import config


class LLM:
    def __init__(self):
        if not config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            system_instruction=config.SYSTEM_PROMPT,
        )

    def new_session(self):
        """Fresh conversation for a new call."""
        return self.model.start_chat(history=[])

    async def reply(self, chat_session, user_prompt: str) -> str:
        resp = await chat_session.send_message_async(user_prompt)
        return (resp.text or "").strip()
