import os
import json
import re
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)

EXPECTED_KEYS = {
    "score",
    "feedback",
    "strengths",
    "improvements",
}

def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"```(?:json)?\s*",
        "",
        text
    ).replace(
        "```",
        ""
    ).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(
        r"\{.*\}",
        cleaned,
        re.DOTALL
    )
    if match:
        return json.loads(match.group())
    raise ValueError(
        f"Could not parse JSON.\n{text}"
    )
def evaluate_answer(
    question: str,
    answer: str
) -> dict:
    if not answer.strip():
        return {
            "score": 0,
            "feedback": "No answer provided.",
            "strengths": "None",
            "improvements": "Write an answer before evaluation."
        }
    prompt = f"""
You are a technical interviewer.
Question:
{question}
Candidate Answer:
{answer}
Return ONLY valid JSON:
{{
  "score": 0-10,
  "feedback": "overall feedback",
  "strengths": "strengths",
  "improvements": "improvements"
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        raw_text = response.text.strip()
        logger.info(
            "Gemini Response: %s",
            raw_text
        )
        result = _extract_json(raw_text)
        missing = (
            EXPECTED_KEYS -
            set(result.keys())
        )
        if missing:
            raise ValueError(
                f"Missing keys: {missing}"
            )
        result["score"] = int(
            result["score"]
        )
        return result
    except Exception as e:
        logger.exception(
            "Gemini evaluation failed"
        )
        raise Exception(
            f"Gemini Error: {str(e)}"
        )