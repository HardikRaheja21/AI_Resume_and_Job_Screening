import re
from typing import List, Dict

def extract_tokens(text: str) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"\w+", text.lower())
    # simple heuristics: remove tiny tokens and common stop words (short list)
    tokens = [t for t in tokens if len(t) > 2]
    stop = {"and", "the", "for", "with", "that", "this", "from", "your", "you"}
    return [t for t in tokens if t not in stop]

def match_resume(resume_text: str, jd_text: str = "") -> Dict:
    """
    Return a dict {score: float, title: Optional[str]}.
    Score is token-overlap ratio between resume and JD (0..1).
    """
    if not jd_text:
        return {"score": 0.0, "title": None}
    jd_tokens = set(extract_tokens(jd_text))
    resume_tokens = set(extract_tokens(resume_text))
    if not jd_tokens:
        return {"score": 0.0, "title": None}
    matches = resume_tokens.intersection(jd_tokens)
    score = len(matches) / len(jd_tokens)
    return {"score": round(score, 4), "title": None}
