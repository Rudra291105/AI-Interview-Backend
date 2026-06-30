import os
import json
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-2.5-flash"


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ──────────────────────────────────────────────────────────────────
# Generate Greeting
# ──────────────────────────────────────────────────────────────────
def generate_greeting(profile: dict) -> str:
    resume_section = ""
    if profile.get("resume") and profile["resume"] != "Not uploaded":
        resume_section = f"""
The candidate has uploaded their resume. Here is a summary of it:
{profile['resume'][:500]}

Reference specific details from their resume (e.g. their college, skills, or projects) 
to make the greeting feel personalised and show you've reviewed their profile.
"""

    prompt = f"""
You are a professional technical interviewer at {profile.get('company', 'a top tech company')}.

You are about to interview a candidate named {profile.get('name', 'the candidate')} 
for the role of {profile['role']}.
The candidate's primary skill is {profile.get('skill', 'Software Engineering')}.
{resume_section}

Write a warm, professional greeting (2-3 sentences) to open the interview.
Address the candidate by their FIRST NAME only — their name is "{profile.get('name', 'there')}",
so use "{profile.get('name', 'there').split()[0]}".
Mention the role they are interviewing for.
Do NOT ask a question yet — just greet and set the tone.

CRITICAL: 
- Use the ACTUAL name "{profile.get('name', 'there').split()[0]}" — never write [Candidate Name] or any placeholder.
- Use the ACTUAL company "{profile.get('company', 'our company')}" — never write [Company Name] or any placeholder.

Return ONLY the greeting text. No JSON, no quotes, no extra formatting.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


# ──────────────────────────────────────────────────────────────────
# Generate First Question
# ──────────────────────────────────────────────────────────────────
def generate_first_question(profile: dict) -> dict:
    resume_section = ""
    if profile.get("resume") and profile["resume"] != "Not uploaded":
        resume_section = f"""
Candidate Resume:
{profile['resume'][:1500]}

Use the resume to ask a specific, personalised warm-up question — for example,
ask about a specific project, technology, or experience mentioned in the resume.
This shows the interviewer has reviewed their background.
"""
    else:
        resume_section = "No resume uploaded. Ask a general warm-up question like 'Tell me about yourself'."

    prompt = f"""
You are a professional technical interviewer at {profile.get('company', 'a top tech company')}.

Candidate Profile:
- Name: {profile.get('name', 'the candidate')}
- Role: {profile['role']}
- Primary Skill: {profile.get('skill', 'Not specified')}

{resume_section}

Return ONLY valid JSON — no extra text, no markdown fences:
{{"question": "<question text>", "question_type": "Introduction", "difficulty": "Easy"}}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    try:
        return _parse_json(response.text)
    except Exception:
        return {
            "question": f"Tell me about yourself, {profile.get('name', '').split()[0] or 'and your background'}.",
            "question_type": "Introduction",
            "difficulty": "Easy",
        }


# ──────────────────────────────────────────────────────────────────
# Generate Next Question (context-aware, follow-up logic)
# ──────────────────────────────────────────────────────────────────
def generate_next_question(profile: dict, history: list) -> dict:
    last_score = history[-1].get("score", 7) if history else 7

    resume_section = ""
    if profile.get("resume") and profile["resume"] != "Not uploaded":
        resume_section = f"""
Candidate Resume (for reference — use this to ask resume-specific questions if relevant):
{profile['resume'][:1000]}
"""

    prompt = f"""
You are a professional technical interviewer at {profile.get('company', 'a top tech company')}.

Candidate Profile:
- Name: {profile.get('name', 'the candidate')}
- Role: {profile['role']}
- Primary Skill: {profile.get('skill', 'Not specified')}
{resume_section}

Interview Conversation So Far:
{json.dumps(history, indent=2)}

Instructions:
1. Analyze the LAST answer carefully. Its score was {last_score}/10.
2. If score < 6 (weak/incomplete): generate a FOLLOW-UP that probes the same topic more deeply.
   Set "is_followup" to true.
3. If score >= 6 (good answer): move to a NEW topic. Progressively increase difficulty.
4. If the resume is available, occasionally ask questions based on specific technologies,
   projects, or experiences mentioned in the resume.
5. Cover: Technical concepts, DSA, System Design, Behavioral, Problem Solving.
6. Do NOT repeat any question already in the history above.

Return ONLY valid JSON — no extra text, no markdown fences:
{{"question": "<question>", "question_type": "<Technical|DSA|System Design|Behavioral|HR|Resume|Follow-up>", "difficulty": "<Easy|Medium|Hard>", "is_followup": <true|false>}}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    try:
        return _parse_json(response.text)
    except Exception:
        return {
            "question": "Can you describe a challenging technical problem you solved recently?",
            "question_type": "Behavioral",
            "difficulty": "Medium",
            "is_followup": False,
        }


# ──────────────────────────────────────────────────────────────────
# Evaluate Answer
# ──────────────────────────────────────────────────────────────────
def evaluate_answer(question: str, answer: str) -> dict:
    prompt = f"""
You are a senior software engineer at a top-tier tech company conducting a technical interview.

Question Asked:
{question}

Candidate's Answer:
{answer}

Evaluate the answer professionally and rigorously.

Scoring Guide (0-10):
- 0-3: Very weak or no real answer
- 4-5: Partially correct, missing key concepts
- 6-7: Good answer with minor gaps
- 8-9: Strong, well-explained answer
- 10: Exceptional — covers edge cases and depth

Return ONLY valid JSON — no extra text, no markdown fences:
{{"score": <integer 0-10>, "feedback": "<2-3 sentence feedback>", "strengths": "<what the candidate did well>", "improvements": "<what to improve or study>"}}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    try:
        return _parse_json(response.text)
    except Exception:
        return {
            "score": 5,
            "feedback": "Your answer was recorded. Evaluation parsing encountered an issue.",
            "strengths": "Answer submitted successfully.",
            "improvements": "Please review core concepts for this topic.",
        }


# ──────────────────────────────────────────────────────────────────
# Generate Final Detailed Report
# ──────────────────────────────────────────────────────────────────
def generate_final_report(profile: dict, history: list) -> dict:
    resume_section = ""
    if profile.get("resume") and profile["resume"] != "Not uploaded":
        resume_section = f"""
Candidate Resume:
{profile['resume'][:1000]}

Factor resume content into your evaluation — did the candidate's answers align 
with the skills and experiences they claimed on their resume?
"""

    prompt = f"""
You are an expert technical interview evaluator.

Candidate Profile:
- Name: {profile.get('name', 'the candidate')}
- Role: {profile['role']}
- Company: {profile.get('company', 'Not specified')}
- Primary Skill: {profile.get('skill', 'Not specified')}
{resume_section}

Complete Interview Transcript:
{json.dumps(history, indent=2)}

Generate a comprehensive, personalised evaluation report. All scores are 0-100.

Return ONLY valid JSON — no extra text, no markdown fences:
{{
  "overall_score": <0-100>,
  "technical_knowledge": <0-100>,
  "communication": <0-100>,
  "confidence": <0-100>,
  "problem_solving": <0-100>,
  "strengths": ["<specific strength 1>", "<specific strength 2>", "<specific strength 3>"],
  "weaknesses": ["<specific weakness 1>", "<specific weakness 2>"],
  "suggested_improvements": ["<actionable improvement 1>", "<actionable improvement 2>", "<actionable improvement 3>"],
  "topics_to_study": ["<topic 1>", "<topic 2>", "<topic 3>"],
  "final_feedback": "<3-5 sentence personalised closing summary addressing the candidate by name>"
}}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    try:
        return _parse_json(response.text)
    except Exception:
        scores = [h.get("score", 5) for h in history]
        avg = round(sum(scores) / len(scores) * 10) if scores else 50
        return {
            "overall_score": avg,
            "technical_knowledge": avg,
            "communication": avg,
            "confidence": avg,
            "problem_solving": avg,
            "strengths": ["Completed the interview session"],
            "weaknesses": ["Report generation encountered a temporary issue"],
            "suggested_improvements": ["Review core concepts of your primary skill"],
            "topics_to_study": ["Data Structures", "System Design", "Behavioral Questions"],
            "final_feedback": "You completed the interview. Please review individual question feedback for detailed insights.",
        }