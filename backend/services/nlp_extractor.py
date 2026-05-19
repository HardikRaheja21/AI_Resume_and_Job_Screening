import logging
import re
from functools import lru_cache
from typing import Dict, List, Optional, Set

from ..resume_parser_service.matcher import KNOWN_SKILLS, _normalize_skill, _title_skill, extract_skills as regex_extract_skills
from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.nlp_extractor")

try:
    import spacy
    from spacy.language import Language
    from spacy.matcher import PhraseMatcher
except ImportError:  # pragma: no cover
    spacy = None
    Language = None
    PhraseMatcher = None
    logger.warning("spacy_unavailable", extra={"note": "spaCy not installed"})
    try:
        metrics.inc_spacy_fallback()
    except Exception:
        pass

SKILL_SYNONYMS: Dict[str, str] = {
    "js": "JavaScript",
    "reactjs": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "gcp": "GCP",
    "aws": "AWS",
    "ci/cd": "CI/CD",
    "ml": "Machine Learning",
    "ai": "AI",
    "nlp": "NLP",
    "sql": "SQL",
    "py": "Python",
}

ROLE_PATTERNS = [
    r"(?:senior|sr|lead|principal|staff)\s+(?:software\s+)?(?:engineer|developer|scientist|architect|manager|analyst)",
    r"(?:software|backend|frontend|full[- ]stack|devops|data|machine learning|ml|cloud|platform).*?(?:engineer|developer|scientist|architect|manager|analyst)",
    r"(?:engineer|developer|scientist|architect|manager|analyst|consultant|specialist)",
]

CERTIFICATION_PATTERNS = [
    r"aws certified [a-z ]+",
    r"google cloud certified [a-z ]+",
    r"microsoft certified [a-z ]+",
    r"pmp(?: certification)?",
    r"ccna",
    r"ccnp",
    r"cissp",
    r"certified .* engineer",
    r"certified .* developer",
    r"(?:certificate|certified) in [a-z0-9 ]+",
]

PROJECT_SECTION_HEADERS = ["project", "projects", "experience", "work experience", "professional experience"]


def is_nlp_available() -> bool:
    if not settings.NLP_ENABLE:
        return False
    if spacy is None:
        return False
    try:
        return _get_nlp_model() is not None
    except Exception as exc:
        logger.warning("NLP availability check failed: %s", exc)
        return False


@lru_cache(maxsize=1)
def _get_nlp_model() -> Optional[Language]:
    if spacy is None:
        return None
    try:
        return spacy.load(settings.NLP_MODEL_NAME)
    except Exception as exc:
        logger.warning("spaCy model %s unavailable: %s", settings.NLP_MODEL_NAME, exc)
        try:
            blank = spacy.blank("en")
            return blank
        except Exception as inner_exc:
            logger.warning("Could not load spaCy blank model: %s", inner_exc)
            return None


def _spacy_doc(text: str):
    model = _get_nlp_model()
    if not model:
        return None
    return model(text)


def _normalize_phrase(text: str) -> str:
    text = text.strip().lower()
    if text in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[text]
    return _title_skill(_normalize_skill(text))


@lru_cache(maxsize=1)
def _build_skill_matcher():
    model = _get_nlp_model()
    if not model or PhraseMatcher is None:
        return None
    matcher = PhraseMatcher(model.vocab, attr="LOWER")
    patterns = []
    for skill in KNOWN_SKILLS:
        patterns.append(model.make_doc(skill))
    for alias in SKILL_SYNONYMS:
        patterns.append(model.make_doc(alias))
    matcher.add("SKILL", patterns)
    return matcher


def _extract_skills_from_doc(doc) -> Set[str]:
    found: Set[str] = set()
    matcher = _build_skill_matcher()
    if matcher and doc is not None:
        for _, start, end in matcher(doc):
            span = doc[start:end]
            found.add(_normalize_phrase(span.text))
    if doc is not None:
        for token in doc:
            token_text = token.text.lower().strip()
            if token_text in SKILL_SYNONYMS:
                found.add(SKILL_SYNONYMS[token_text])
    return found


def extract_technologies(text: str) -> List[str]:
    if not text:
        return []
    doc = _spacy_doc(text)
    found = _extract_skills_from_doc(doc)
    found.update({skill for skill in regex_extract_skills(text)})
    normalized: List[str] = sorted(found)
    return normalized


def extract_organizations(text: str) -> List[str]:
    if not text:
        return []
    doc = _spacy_doc(text)
    organizations: Set[str] = set()
    if doc is not None:
        for ent in doc.ents:
            if ent.label_ in {"ORG", "GPE", "NORP"}:
                organizations.add(ent.text.strip())
    patterns = [r"\bat\s+([A-Z][A-Za-z0-9&\.\- ]+)", r"\bfrom\s+([A-Z][A-Za-z0-9&\.\- ]+)"
               ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            organizations.add(match.group(1).strip())
    return sorted({org for org in organizations if len(org) > 2})[:8]


def extract_roles(text: str) -> List[str]:
    if not text:
        return []
    roles: Set[str] = set()
    lower_text = text.lower()
    for pattern in ROLE_PATTERNS:
        match = re.search(pattern, lower_text)
        if match:
            roles.add(_title_skill(match.group(0)))
    doc = _spacy_doc(text)
    if doc is not None:
        if doc.has_annotation("DEP"):
            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.strip()
                if any(keyword in chunk_text.lower() for keyword in ["engineer", "developer", "scientist", "manager", "architect", "analyst", "specialist", "consultant"]):
                    roles.add(_title_skill(chunk_text.lower()))
        else:
            for token in doc:
                if token.pos_ in {"NOUN", "PROPN"} and token.text.lower() in {
                    "engineer", "developer", "scientist", "manager", "architect", "analyst", "specialist", "consultant"
                }:
                    start = max(0, token.i - 2)
                    phrase = " ".join([t.text for t in doc[start : token.i + 1]])
                    roles.add(_title_skill(phrase.lower()))
    return sorted(roles)[:5]


def extract_certifications(text: str) -> List[str]:
    if not text:
        return []
    certifications: Set[str] = set()
    for pattern in CERTIFICATION_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            certifications.add(match.group(0).strip().title())
    if not certifications:
        doc = _spacy_doc(text)
        if doc is not None:
            for ent in doc.ents:
                if ent.label_ in {"ORG", "PRODUCT"} and "cert" in ent.text.lower():
                    certifications.add(ent.text.strip())
    return sorted(certifications)[:8]


def _extract_project_section(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    collected: List[str] = []
    capture = False
    for line in lines:
        if any(header in line.lower() for header in PROJECT_SECTION_HEADERS):
            capture = True
            collected.append(line)
            continue
        if capture and (not line or re.match(r"^[A-Z][A-Za-z0-9 ]{0,40}:$", line)):
            break
        if capture:
            collected.append(line)
    if collected:
        return "\n".join(collected)
    return text[:2000]


def extract_project_keywords(text: str) -> List[str]:
    if not text:
        return []
    section_text = _extract_project_section(text)
    doc = _spacy_doc(section_text)
    candidates: Set[str] = set()
    if doc is not None:
        for token in doc:
            if token.pos_ in {"NOUN", "PROPN", "VERB"} and len(token.text) > 3:
                candidates.add(token.lemma_.title())
        if doc.has_annotation("DEP"):
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip()
                if len(phrase) > 3 and not phrase.lower().startswith("the "):
                    candidates.add(_title_skill(phrase.lower()))
    tokens = re.findall(r"[A-Za-z0-9\+\#\.\-]{4,}", section_text)
    for token in tokens:
        if token.lower() in SKILL_SYNONYMS:
            candidates.add(SKILL_SYNONYMS[token.lower()])
    return sorted({keyword for keyword in candidates if len(keyword) > 3})[:12]


def extract_resume_entities(text: str) -> Dict[str, List[str]]:
    return {
        "technologies": extract_technologies(text),
        "organizations": extract_organizations(text),
        "roles": extract_roles(text),
        "certifications": extract_certifications(text),
        "project_keywords": extract_project_keywords(text),
    }


def extract_jd_entities(text: str) -> Dict[str, List[str]]:
    return extract_resume_entities(text)
