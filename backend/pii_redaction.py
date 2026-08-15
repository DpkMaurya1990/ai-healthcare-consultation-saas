"""Helpers for reducing PII exposure before consultation notes are sent to an LLM."""

import re
from typing import Dict, Iterator, List, Pattern, Tuple


PLACEHOLDER_TOKEN = "[PATIENT_NAME]"
PLACEHOLDER_PATTERN = re.compile(r"\[\s*patient[_ ]?name\s*\]", re.IGNORECASE)


class PIIRedactor:
    """Apply lightweight, deterministic redaction for patient-name and note content."""

    def __init__(self) -> None:
        self._patterns: List[Tuple[Pattern[str], str]] = [
            (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
            (re.compile(r"(?<!\w)(?:\+?\d[\s.-]?){7,15}\d(?!\w)"), "[REDACTED_PHONE]"),
            (re.compile(r"\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b"), "[REDACTED_DOB]"),
            (re.compile(r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b"), "[REDACTED_DOB]"),
            (re.compile(r"(?<!\w)(?:[A-Z]{1,2}\d{4,8}|[A-Z]{2,4}\d{3,6})(?!\w)", re.IGNORECASE), "[REDACTED_ID]"),
        ]

    def mask_patient_name(self, text: str, patient_name: str) -> Tuple[str, Dict[str, str]]:
        """Replace the real patient name with a stable placeholder in the notes."""
        if not text or not patient_name:
            return text, {}

        escaped_name = re.escape(patient_name)
        pattern = re.compile(rf"(?<!\w){escaped_name}(?!\w)", re.IGNORECASE)
        masked_text = pattern.sub(PLACEHOLDER_TOKEN, text)
        return masked_text, {PLACEHOLDER_TOKEN: patient_name}

    def restore_patient_name(self, text: str, patient_name: str) -> str:
        """Restore the real patient name into the response text after the LLM call."""
        if not text or not patient_name:
            return text
        return PLACEHOLDER_PATTERN.sub(patient_name, text)

    def redact_free_text(self, text: str) -> str:
        """Redact common free-text PII patterns with bounded regex rules."""
        if not text:
            return text

        redacted_text = text
        for pattern, replacement in self._patterns:
            redacted_text = pattern.sub(replacement, redacted_text)
        return redacted_text

    def prepare_for_llm(self, text: str, patient_name: str) -> str:
        """Mask the patient name and redact other PII before sending text to the LLM."""
        redacted_text = self.redact_free_text(text)
        masked_text, _ = self.mask_patient_name(redacted_text, patient_name)
        return masked_text

    def restore_in_chunks(self, chunks: Iterator[str], patient_name: str) -> Iterator[str]:
        """Replace the placeholder with the real patient name while buffering chunk boundaries."""
        pending_text = ""
        safe_tail = max(len(PLACEHOLDER_TOKEN) - 1, 0)

        for chunk in chunks:
            if not chunk:
                continue
            pending_text += chunk

            while True:
                match = PLACEHOLDER_PATTERN.search(pending_text)
                if not match:
                    break

                before = pending_text[: match.start()]
                after = pending_text[match.end() :]
                if before:
                    yield before
                yield patient_name
                pending_text = after

            if safe_tail and len(pending_text) > safe_tail:
                emit_text = pending_text[:-safe_tail]
                if emit_text:
                    yield emit_text
                pending_text = pending_text[-safe_tail:]

        if pending_text:
            yield pending_text

    def personalize_signature(self, text: str, sender_name: str) -> str:
        """Replace a generic email-signature placeholder with a clinic/business name."""
        if not text or not sender_name:
            return text

        text = re.sub(r"\[Your Name\]", sender_name, text, flags=re.IGNORECASE)
        if re.search(r"(?im)^(?:Best regards|Kind regards|Thanks|Thank you|Sincerely)\s*,?\s*$", text):
            return text

        if text.strip().endswith(sender_name):
            return text

        if not text.endswith("\n"):
            text = f"{text}\n"

        return f"{text.strip()}\n\nBest regards,\n{sender_name}"

    def personalize_salutation(self, text: str, patient_name: str) -> str:
        """Replace a generic greeting with a personalized patient name greeting."""
        if not text:
            return text

        if not patient_name:
            fallback_patterns = [
                (re.compile(r"(?im)^(\s*)(Dear\s+Patient\s*,?)"), r"\1Hello,"),
                (re.compile(r"(?im)^(\s*)(Dear\s*,?)"), r"\1Hello,"),
                (re.compile(r"(?im)^(\s*)(Hello\s*,?)"), r"\1Hello,"),
                (re.compile(r"(?im)^(\s*)(Hi\s*,?)"), r"\1Hello,"),
            ]
            for pattern, replacement in fallback_patterns:
                if pattern.search(text):
                    return pattern.sub(replacement, text, count=1)
            return text

        patterns = [
            (re.compile(r"(?im)^(\s*)(Dear\s+Patient\s*,?)"), f"\\1Hello {patient_name},"),
            (re.compile(r"(?im)^(\s*)(Dear\s*,?)"), f"\\1Hello {patient_name},"),
            (re.compile(r"(?im)^(\s*)(Hello\s*,?)"), f"\\1Hello {patient_name},"),
            (re.compile(r"(?im)^(\s*)(Hi\s*,?)"), f"\\1Hello {patient_name},"),
        ]

        for pattern, replacement in patterns:
            if pattern.search(text):
                return pattern.sub(replacement, text, count=1)

        return text

    def normalize_email_greeting(self, text: str, patient_name: str) -> str:
        """Force the opening email greeting to Hello-style for deterministic output."""
        if not text:
            return text

        normalized_name = patient_name.strip()
        preferred_greeting = f"Hello {normalized_name}," if normalized_name else "Hello,"
        email_heading_pattern = re.compile(r"(?im)^\s*###\s*Draft of email to patient.*$")
        greeting_pattern = re.compile(r"(?im)^\s*(Dear(?:\s+Patient)?\s*,?|Hello\s*,?|Hi\s*,?)")

        if greeting_pattern.search(text):
            normalized_text = re.sub(
                r"(?im)^\s*(Dear(?:\s+Patient)?\s*,?|Hello\s*,?|Hi\s*,?)",
                preferred_greeting,
                text,
                count=1,
            )
            return normalized_text.replace(f"{preferred_greeting}{normalized_name},", preferred_greeting)

        if not email_heading_pattern.search(text) and "Draft of email" not in text:
            return text

        lines = text.splitlines()
        greeting_index = None
        for index, line in enumerate(lines):
            if line.strip() and not line.startswith("###"):
                greeting_index = index + 1
                break

        if greeting_index is None:
            return text

        if lines[greeting_index - 1].strip() != preferred_greeting:
            lines.insert(greeting_index, preferred_greeting)
            lines.insert(greeting_index + 1, "")
        return "\n".join(lines)

    def prepare_email_payload(self, text: str, patient_name: str) -> Dict[str, str]:
        """Build a cleaner subject and body for the patient email draft."""
        normalized_text = self.normalize_email_greeting(text, patient_name)
        body = normalized_text

        email_section_pattern = re.compile(
            r"(?im)^\s*###\s*Draft of email to patient(?:\s+in\s+patient-friendly\s+language)?\s*$"
        )
        match = email_section_pattern.search(body)
        if match:
            body = body[match.end():].strip()
        else:
            body = body.strip()

        if not body:
            body = "Hello,\n\nThank you for your visit."

        # Drop any leaked subject lines from the body payload.
        body = re.sub(r"(?im)^\s*Subject:\s*.+$", "", body).strip()

        lines = [line.rstrip() for line in body.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)

        preferred_greeting = f"Hello {patient_name.strip()}," if patient_name.strip() else "Hello,"
        if lines:
            first_line = lines[0].strip()
            if re.match(r"^(Dear|Hello|Hi)(?:\s+.+)?$", first_line, flags=re.IGNORECASE):
                lines[0] = preferred_greeting
            else:
                lines.insert(0, preferred_greeting)
        else:
            lines = [preferred_greeting]

        body = "\n".join(lines).strip()

        # Collapse repeated patient names in malformed greetings like
        # "Hello Suraj,Suraj,Suraj," into a single professional greeting.
        body = re.sub(
            r"(?im)^\s*Hello\s+([^,\n]+),(?:\s*\1,)+",
            r"Hello \1,",
            body,
        )
        body = re.sub(r"(?i)\bHello\s+([A-Za-z][A-Za-z0-9\-. ]*?)\s*,\s*\1\b", r"Hello \1,", body)
        body = re.sub(r"(?i)\bHello\s+([A-Za-z][A-Za-z0-9\-. ]*?)(?:,\s*){2,}", r"Hello \1,", body)
        body = re.sub(r"(?i)\bHello\s+" + re.escape(patient_name.strip()) + r"\s*,\s*" + re.escape(patient_name.strip()) + r"\b", f"Hello {patient_name.strip()},", body)
        body = re.sub(r"\bThanks for your visit\.?\b", "Thank you for visiting us today.", body, flags=re.IGNORECASE)
        body = re.sub(r"\bThank you for your visit today\.?\b", "Thank you for visiting us today.", body, flags=re.IGNORECASE)
        body = re.sub(r"\bPlease follow up with us\.?\b", "Please let us know if you have any questions.", body, flags=re.IGNORECASE)
        body = re.sub(r"\bPlease follow up\.?\b", "Please let us know if you have any questions.", body, flags=re.IGNORECASE)
        body = re.sub(r"\bFeel free to reach out if needed\.?\b", "Please let us know if you have any questions.", body, flags=re.IGNORECASE)
        body = re.sub(r"\bin\s+\d+\s+days\b", "in a few days", body, flags=re.IGNORECASE)
        body = re.sub(r"\bif your fever persists\b", "if your fever persists", body, flags=re.IGNORECASE)
        body = re.sub(r"\bPlease let us know if you have any questions\.\s+in a few days\b", "Please let us know if you have any questions. We will review you again in a few days if needed.", body, flags=re.IGNORECASE)
        body = re.sub(
            r"\bPlease let us know if you have any questions\.\s+if your fever persists,?\s*[^.]*\.\s*",
            "Please let us know if you have any questions. If your fever persists, please schedule a follow-up visit with us. ",
            body,
            flags=re.IGNORECASE,
        )
        body = re.sub(r"\bPlease let us know if you have any questions\.\s+so we can reassess your condition and adjust your treatment plan if necessary\b", "Please let us know if you have any questions. If your symptoms continue or worsen, we can reassess your treatment plan.", body, flags=re.IGNORECASE)
        body = re.sub(
            r"(?i)\bWe will review you again in a few days if needed\.\s*if your fever persists\.",
            "We will review you again in a few days if your fever persists.",
            body,
        )
        body = re.sub(
            r"(?i)\bif your fever persists,?\s*please schedule a follow-up visit with us after\s*3\s*days\.\s*",
            "If your fever persists, please schedule a follow-up visit with us in 3 days. ",
            body,
        )
        body = re.sub(
            r"(?i)\bafter\s*3\s*days\s*if your fever persists\.\s*",
            "If your fever persists after 3 days, please schedule a follow-up visit with us. ",
            body,
        )

        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        body = re.sub(r"[ \t]+\n", "\n", body)
        body = re.sub(r"\n{2,}", "\n\n", body).strip()
        body = re.sub(r"\s+([,.;:!?])", r"\1", body)
        body = re.sub(r"\s{2,}", " ", body)

        # Keep dash-prefixed recommendation lines readable by separating them
        # from the next statement with a blank line.
        bullet_spaced_lines = []
        body_lines = body.splitlines()
        for index, line in enumerate(body_lines):
            bullet_spaced_lines.append(line)
            stripped_line = line.strip()
            if not stripped_line.startswith("-") or stripped_line == "-":
                continue

            next_line = body_lines[index + 1].strip() if index + 1 < len(body_lines) else ""
            if next_line:
                bullet_spaced_lines.append("")
        body = "\n".join(bullet_spaced_lines)

        if patient_name.strip():
            escaped_name = re.escape(patient_name.strip())
            body = re.sub(
                rf"(?im)^\s*Hello\s+{escaped_name}(?:\s*,\s*{escaped_name})+\s*,",
                f"Hello {patient_name.strip()},",
                body,
            )

        # Keep only the first greeting line if the model emits repeated greetings.
        greeting_pattern = re.compile(r"(?im)^\s*Hello(?:\s+[^,\n]+)?\s*,\s*$")
        kept_first_greeting = False
        deduped_lines = []
        for line in body.splitlines():
            if greeting_pattern.match(line):
                if kept_first_greeting:
                    continue
                kept_first_greeting = True
            deduped_lines.append(line)
        body = "\n".join(deduped_lines).strip()

        body = re.sub(
            r"(?im)\s*(Best regards,|Kind regards,|Sincerely,|Best,)\s*\n?\s*(Dr\.\s*Sharma\s*Clinic)\s*$",
            r"\n\n\1\n\2",
            body,
        ).strip()

        body = re.sub(r"(?i)\bDr\. Sharma Clinic\b", "Dr. Sharma Clinic", body)

        # Ensure the first sentence after the greeting starts with a capital letter.
        body_lines = body.splitlines()
        if body_lines:
            for idx in range(1, len(body_lines)):
                candidate = body_lines[idx].strip()
                if candidate:
                    body_lines[idx] = f"{candidate[0].upper()}{candidate[1:]}"
                    break
            body = "\n".join(body_lines)

        # Add paragraph breaks for better email readability.
        body = re.sub(r"\.\s+(As discussed)\b", r".\n\n\1", body)
        body = re.sub(r"\.\s+(Please let us know if you have any questions\.)", r".\n\n\1", body)
        body = re.sub(r"\.\s+(If your [^.]+\.)", r".\n\n\1", body)
        body = re.sub(r"\.\s+(We will [^.]+\.)", r".\n\n\1", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        subject = "Follow-up from your recent visit"

        return {"subject": subject, "body": body}

    def redact_dict(self, payload: Dict[str, object]) -> Dict[str, object]:
        """Recursively redact string values inside a dictionary payload."""
        redacted: Dict[str, object] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                redacted[key] = self.redact_free_text(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_free_text(item) if isinstance(item, str) else self.redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted
