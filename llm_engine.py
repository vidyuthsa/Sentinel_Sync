"""
llm_engine.py — AI orchestration layer for Sentinel Sync.

Wraps an OpenAI-compatible chat completion client to power four capabilities:
  1. Job posting parsing + Approval Probability scoring
  2. Technical interview "Blitz Prep Sheets"
  3. Platform-tuned ghosted-application follow-up messages
  4. Counter-offer leverage emails

If no API key is configured, every method falls back to a fully-functional,
deterministic generator so the dashboard remains operational without any
external credentials.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

from currency import CURRENCY_SYMBOLS, LAKH


MODEL_NAME = os.environ.get("SENTINEL_LLM_MODEL", "gpt-4o-mini")


class SentinelLLM:
    """Thin orchestration wrapper around an OpenAI-compatible client."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None):
        self.api_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self.base_url = base_url or os.environ.get("SENTINEL_LLM_BASE_URL")
        self.model = model or os.environ.get("SENTINEL_LLM_MODEL", "gpt-4o-mini")
        self.client = None
        self.last_error: Optional[str] = None  # surfaces to UI instead of silent failure

        if not OPENAI_AVAILABLE:
            self.last_error = "openai package not installed. Run: pip install openai"
            return

        if not self.api_key:
            self.last_error = "No API key provided."
            return

        kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        try:
            self.client = OpenAI(**kwargs)
        except Exception as e:
            self.last_error = f"Client init failed: {e}"
            self.client = None

    @property
    def is_live(self) -> bool:
        return self.client is not None

    def test_connection(self) -> tuple[bool, str]:
        """
        Makes a cheap real API call to verify credentials and model access.
        Returns (success: bool, message: str).
        Call this from the sidebar after the user enters their key.
        """
        if not self.client:
            return False, self.last_error or "No client initialized."
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                max_tokens=5,
                temperature=0,
            )
            reply = resp.choices[0].message.content.strip()
            return True, f"Connected — model `{self.model}` replied: {reply}"
        except Exception as e:
            self.last_error = str(e)
            # If the model doesn't exist, suggest common alternatives
            err_lower = str(e).lower()
            if "model" in err_lower and ("not found" in err_lower or "does not exist" in err_lower):
                return False, (
                    f"Model `{self.model}` not found on your account. "
                    f"Try: gpt-4o-mini, gpt-3.5-turbo, gpt-4o, gpt-4-turbo. "
                    f"Original error: {e}"
                )
            if "auth" in err_lower or "api key" in err_lower or "invalid" in err_lower:
                return False, f"Authentication failed — check your API key. Detail: {e}"
            if "quota" in err_lower or "billing" in err_lower or "rate" in err_lower:
                return False, f"Quota / billing issue on your OpenAI account: {e}"
            return False, f"API call failed: {e}"

    # ------------------------------------------------------------------ #
    # Internal call helpers — now surface errors instead of swallowing them
    # ------------------------------------------------------------------ #
    def _chat_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except Exception as e:
            self.last_error = str(e)
            return None

    def _chat_text(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
            )
            self.last_error = None  # clear on success
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.last_error = str(e)
            return None

    # ------------------------------------------------------------------ #
    # Component A — Ingestion + Matching
    # ------------------------------------------------------------------ #
    def parse_job_posting(self, raw_text: str, resume_text: str) -> dict:
        system_prompt = (
            "You are Sentinel Sync's ingestion parser. Extract structured "
            "fields from a pasted job posting, confirmation email, or log "
            "snippet. Detect the salary's currency from symbols or context "
            "(e.g. $, ₹, €, £, or words like USD, INR, EUR, GBP). If the "
            "text states a value in LPA (Lakhs Per Annum), multiply by "
            "100000 and set currency to INR. Report the salary as a full "
            "annual figure in its OWN detected currency — never convert it "
            "to USD yourself. If salary is not stated at all, estimate a "
            "realistic industry-average annual figure for that title and "
            "seniority, defaulting to USD if no currency signal exists. "
            "Then compare the role against the candidate's resume/skills "
            "and output an Approval Probability (0-100) reflecting match "
            "strength. Respond ONLY with a JSON object with keys: company "
            "(string), title (string), salary (number, full annual amount "
            "in its natural detected currency), currency (3-letter ISO "
            "code such as USD, INR, EUR, GBP, AED, SGD, AUD, CAD), "
            "match_score (number 0-100), rationale (1-2 sentences)."
        )
        user_prompt = (
            f"RAW TEXT:\n{raw_text}\n\n"
            f"CANDIDATE RESUME/SKILLS:\n{resume_text or 'Not provided.'}"
        )
        result = self._chat_json(system_prompt, user_prompt)
        if result:
            return self._sanitize_parse_result(result)
        return self._fallback_parse(raw_text, resume_text)

    @staticmethod
    def _sanitize_parse_result(result: dict) -> dict:
        cur = str(result.get("currency", "USD")).upper().strip()
        if cur not in CURRENCY_SYMBOLS:
            cur = "USD"
        return {
            "company": str(result.get("company", "Unknown Company")).strip() or "Unknown Company",
            "title": str(result.get("title", "Unspecified Role")).strip() or "Unspecified Role",
            "salary": float(result.get("salary", 0) or 0),
            "currency": cur,
            "match_score": max(0.0, min(100.0, float(result.get("match_score", 50) or 50))),
            "rationale": result.get("rationale", ""),
        }

    @staticmethod
    def _detect_currency_and_salary(raw_text: str) -> tuple[str, float]:
        inr_match = re.search(
            r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d+)?)\s?(LPA|lakh|lac|cr|crore)?",
            raw_text, re.IGNORECASE,
        )
        if inr_match:
            value = float(inr_match.group(1).replace(",", ""))
            unit = (inr_match.group(2) or "").lower()
            if unit in ("lpa", "lakh", "lac"):
                return "INR", value * LAKH
            if unit in ("cr", "crore"):
                return "INR", value * LAKH * 100
            return "INR", value

        lpa_match = re.search(r"([\d,]+(?:\.\d+)?)\s?(LPA|lakh|lac)\b", raw_text, re.IGNORECASE)
        if lpa_match:
            value = float(lpa_match.group(1).replace(",", ""))
            return "INR", value * LAKH

        eur_match = re.search(r"(?:€|EUR)\s?([\d,]+(?:\.\d+)?)\s?(k|K)?", raw_text)
        if eur_match:
            value = float(eur_match.group(1).replace(",", ""))
            if (eur_match.group(2) or "").lower() == "k":
                value *= 1000
            return "EUR", value

        gbp_match = re.search(r"(?:£|GBP)\s?([\d,]+(?:\.\d+)?)\s?(k|K)?", raw_text)
        if gbp_match:
            value = float(gbp_match.group(1).replace(",", ""))
            if (gbp_match.group(2) or "").lower() == "k":
                value *= 1000
            return "GBP", value

        usd_match = re.search(r"(?:\$|USD)\s?([\d,]+(?:\.\d+)?)\s?(k|K)?", raw_text)
        if usd_match:
            value = float(usd_match.group(1).replace(",", ""))
            if (usd_match.group(2) or "").lower() == "k":
                value *= 1000
            return "USD", value

        return "USD", 95000.0

    @staticmethod
    def _fallback_parse(raw_text: str, resume_text: str) -> dict:
        company_match = re.search(
            r"\b([A-Z][A-Za-z0-9&.]+(?:\s[A-Z][A-Za-z0-9&.]+){0,2})\b", raw_text
        )
        if company_match:
            company = company_match.group(1)
        elif raw_text.strip():
            company = raw_text.splitlines()[0][:40]
        else:
            company = "Unknown Company"

        title_match = re.search(
            r"(Software Engineer|Data Scientist|Product Manager|SDE[- ]?\w*|"
            r"Backend Engineer|Frontend Engineer|Full[- ]?Stack Engineer|"
            r"ML Engineer|DevOps Engineer|Site Reliability Engineer|Analyst|"
            r"Intern\w*|Developer)",
            raw_text, re.IGNORECASE,
        )
        title = title_match.group(1).title() if title_match else "Software Engineer"
        cur, salary = SentinelLLM._detect_currency_and_salary(raw_text)
        resume_tokens = set(re.findall(r"[A-Za-z+#]{3,}", (resume_text or "").lower()))
        posting_tokens = set(re.findall(r"[A-Za-z+#]{3,}", raw_text.lower()))
        overlap = resume_tokens & posting_tokens
        match_score = (
            35.0 if not resume_tokens
            else min(95.0, 30.0 + 65.0 * (len(overlap) / max(1, len(resume_tokens))))
        )
        return {
            "company": company,
            "title": title,
            "salary": round(salary, 2),
            "currency": cur,
            "match_score": round(match_score, 1),
            "rationale": "Estimated via offline keyword-overlap fallback (no LLM key configured).",
        }

    # ------------------------------------------------------------------ #
    # Component D — Last-Mile Execution Engine
    # ------------------------------------------------------------------ #
    def generate_blitz_prep(self, company: str, title: str) -> str:
        system_prompt = (
            "You write tight, high-signal technical interview prep sheets. "
            "Given a company and role, output exactly 3 specific technical "
            "topics likely to come up, each with one concrete practice "
            "prompt. Keep the whole sheet under 150 words, scannable in "
            "under 30 minutes."
        )
        user_prompt = f"Company: {company}\nRole: {title}\nGenerate the 30-Minute Blitz Prep Sheet."
        text = self._chat_text(system_prompt, user_prompt)
        return text if text else self._fallback_blitz_prep(company, title)

    @staticmethod
    def _fallback_blitz_prep(company: str, title: str) -> str:
        return (
            f"30-MINUTE BLITZ PREP — {company} ({title})\n\n"
            f"1. Data Structures & Complexity\n"
            f"   Practice: Implement an LRU cache and state its time/space complexity.\n\n"
            f"2. System Design Fundamentals\n"
            f"   Practice: Sketch a high-level design for a URL shortener at {company}-scale traffic.\n\n"
            f"3. Role-Specific Coding\n"
            f"   Practice: Solve a medium-difficulty array/string problem relevant to a {title} "
            f"interview, narrating your approach out loud before coding.\n\n"
            f"(Offline fallback sheet — connect an LLM key for company-tailored topics.)"
        )

    def generate_followup_message(
        self, company: str, title: str, platform: str, days_cold: int
    ) -> str:
        system_prompt = (
            "You write concise, warm-but-professional follow-up messages for "
            "job seekers re-engaging a company that has gone quiet. Match the "
            "tone to the requested platform: LinkedIn (light, networking-"
            "savvy), WhatsApp (brief, friendly, no fluff), or Gmail (formal, "
            "structured). Keep it under 120 words and end with a clear, "
            "low-pressure ask."
        )
        user_prompt = (
            f"Company: {company}\nRole: {title}\nPlatform: {platform}\n"
            f"Days since last contact: {days_cold}\nWrite the follow-up message."
        )
        text = self._chat_text(system_prompt, user_prompt)
        return text if text else self._fallback_followup(company, title, platform, days_cold)

    @staticmethod
    def _fallback_followup(company: str, title: str, platform: str, days_cold: int) -> str:
        if platform == "LinkedIn":
            return (
                f"Hi — hope things are going well at {company}! Wanted to check in on the "
                f"{title} process; it's been about {days_cold} days since we last connected. "
                f"Still very excited about the opportunity — happy to share anything else useful "
                f"on my end. Look forward to hearing where things stand!"
            )
        if platform == "WhatsApp":
            return (
                f"Hi! Just following up on the {title} role at {company} — it's been "
                f"{days_cold} days since we last spoke. Any update on next steps? Still very keen :)"
            )
        return (
            f"Hello,\n\nI wanted to follow up on my application for the {title} position at "
            f"{company}. It has been {days_cold} days since our last interaction, and I remain "
            f"very enthusiastic about the opportunity. Could you share an update on timeline or "
            f"next steps when convenient?\n\nThank you for your time,\n[Your Name]"
        )

    def generate_counteroffer_email(
        self, midstage_company: str, midstage_title: str, offer_salary: float
    ) -> str:
        system_prompt = (
            "You write strategic, professional leverage emails for candidates "
            "who have a competing offer and want a mid-stage company to "
            "accelerate their process. The tone must be confident but not "
            "ultimatum-like, preserve goodwill, and avoid naming the "
            "competing company. Keep it under 150 words."
        )
        user_prompt = (
            f"Mid-stage company: {midstage_company}\nMid-stage role: {midstage_title}\n"
            f"Competing offer salary (do not name the competing company): ${offer_salary:,.0f}\n"
            f"Write the acceleration request email."
        )
        text = self._chat_text(system_prompt, user_prompt)
        return text if text else self._fallback_counteroffer(midstage_company, midstage_title, offer_salary)

    @staticmethod
    def _fallback_counteroffer(midstage_company: str, midstage_title: str, offer_salary: float) -> str:
        return (
            f"Subject: Quick update on my timeline — {midstage_title}\n\n"
            f"Hi team,\n\n"
            f"I wanted to give you a heads-up: I've received a competitive offer from another "
            f"process (in the ${offer_salary:,.0f} range) with a decision deadline approaching. "
            f"{midstage_company} remains my top choice given the role and team, so I wanted to "
            f"ask whether it might be possible to accelerate the remaining steps on your end. "
            f"Happy to make myself available at very short notice for anything still needed.\n\n"
            f"Thank you for considering this — I'm genuinely excited about the opportunity.\n\n"
            f"Best,\n[Your Name]"
        )

    def generate_reschedule_request(
        self, company: str, title: str, original_dt_str: str
    ) -> str:
        """
        Drafts a polite request to a lower-priority pipeline company asking
        them to move an interview that collides with a higher-priority one.
        The competing company is never named in the outgoing email.
        """
        system_prompt = (
            "You write polite, professional emails asking an interviewer or "
            "recruiter to reschedule an already-confirmed interview slot. "
            "The candidate has an unavoidable scheduling conflict on that exact "
            "date and needs a different time the SAME day if possible, or the "
            "nearest convenient alternative. Do not invent or name any "
            "competing company or process — keep the reason generic and "
            "professional (e.g. 'an unavoidable scheduling conflict'). Keep "
            "the tone apologetic but not groveling, under 120 words, and end "
            "by inviting them to propose a time that works on their end."
        )
        user_prompt = (
            f"Company: {company}\nRole: {title}\n"
            f"Originally scheduled: {original_dt_str}\n"
            f"Write the reschedule request email, including a short subject line."
        )
        text = self._chat_text(system_prompt, user_prompt)
        return text if text else self._fallback_reschedule_request(company, title, original_dt_str)

    @staticmethod
    def _fallback_reschedule_request(company: str, title: str, original_dt_str: str) -> str:
        return (
            f"Subject: Request to reschedule — {title} interview\n\n"
            f"Hi,\n\n"
            f"Thank you again for scheduling my interview for the {title} role at {company} "
            f"on {original_dt_str}. Unfortunately, an unavoidable scheduling conflict has come "
            f"up at that exact time, and I wanted to reach out as early as possible.\n\n"
            f"Would it be possible to move our conversation to a different time that day, or "
            f"to the nearest slot that works on your end? I'm happy to work around your "
            f"availability and apologize for any inconvenience this causes.\n\n"
            f"Thank you for understanding — I remain very enthusiastic about this opportunity.\n\n"
            f"Best,\n[Your Name]"
        )
