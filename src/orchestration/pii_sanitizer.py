import re
from typing import Dict, Any, List

EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")

def mask_email_match(match: re.Match) -> str:
    first_char = match.group(1)
    domain = match.group(2)
    return f"{first_char}***@{domain}"

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    # Mask emails
    text = EMAIL_PATTERN.sub(mask_email_match, text)
    # Remove phone numbers
    text = PHONE_PATTERN.sub("[phone redacted]", text)
    return text

def sanitize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for k, v in args.items():
        if isinstance(v, str):
            cleaned[k] = sanitize_text(v)
        elif isinstance(v, dict):
            cleaned[k] = sanitize_args(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_args(x) if isinstance(x, dict) else (sanitize_text(x) if isinstance(x, str) else x) for x in v]
        else:
            cleaned[k] = v
    return cleaned

INJECTION_PATTERNS = [
    r"ignore (all|previous|prior) instructions",
    r"system prompt",
    r"hidden prompt",
    r"you are now an unrestricted",
    r"reveal (the|your) instructions",
    r"override security",
    r"grant me hr access",
    r"grant me manager access",
    r"act as admin",
    r"sudo ",
    r"jailbreak"
]

def check_prompt_injection(message: str) -> bool:
    msg_lower = message.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False
