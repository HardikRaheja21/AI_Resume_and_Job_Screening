from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re

from ..services import ai_assistant
from ..services.embedding_service import cached_embedding, get_model, get_sentence_transformers_utils
from ..utils.config import settings

def extract_tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9\+\#\.-]+", text.lower())

KNOWN_SKILLS = [
    "python", "fastapi", "flask", "django", "java", "spring", "javascript", "typescript", "react", "next.js",
    "node.js", "express", "html", "css", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
    "aws", "azure", "gcp", "machine learning", "deep learning", "nlp", "pandas", "numpy", "scikit-learn", "pytorch",
    "tensorflow", "git", "github", "ci/cd", "pytest", "rest", "graphql",
]

ROLE_KEYWORDS = {
    "backend engineer": ["backend", "fastapi", "django", "flask", "api", "sql"],
    "frontend engineer": ["frontend", "react", "javascript", "typescript", "css", "html"],
    "full stack engineer": ["full stack", "frontend", "backend", "react", "node.js", "sql"],
    "data scientist": ["data scientist", "machine learning", "pandas", "numpy", "tensorflow", "pytorch"],
    "ml engineer": ["ml engineer", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch"],
    "devops engineer": ["devops", "docker", "kubernetes", "aws", "ci/cd", "terraform"],
    "mobile developer": ["android", "ios", "flutter", "react native", "swift", "kotlin"],
}

EDUCATION_KEYWORDS = [
    "b.tech",
    "b.e",
    "bachelor",
    "master",
    "m.tech",
    "mba",
    "computer science",
    "information technology",
]

SKILL_GRAPH = {
    "machine learning": ["deep learning", "nlp", "computer vision"],
    "deep learning": ["tensorflow", "pytorch"],
    "frontend": ["react", "angular", "vue", "javascript", "css", "html"],
    "backend": ["node", "django", "flask", "fastapi", "sql"],
    "javascript": ["typescript", "react", "node.js"],
    "react": ["javascript", "typescript", "next.js"],
    "python": ["fastapi", "flask", "django", "machine learning", "nlp"],
    "docker": ["kubernetes", "aws", "devops"],
}



@dataclass(frozen=True)
class ScoreWeights:
    required_skill: float = 0.45
    optional_skill: float = 0.15
    semantic: float = 0.25
    experience: float = 0.15

    def normalized(self) -> "ScoreWeights":
        total = self.required_skill + self.optional_skill + self.semantic + self.experience
        if total <= 0:
            return ScoreWeights()
        return ScoreWeights(
            required_skill=self.required_skill / total,
            optional_skill=self.optional_skill / total,
            semantic=self.semantic / total,
            experience=self.experience / total,
        )


def _clamp_weight(value: float, default: float) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, weight))


def get_matcher_weights() -> ScoreWeights:
    weights = ScoreWeights(
        required_skill=_clamp_weight(settings.MATCHER_REQUIRED_SKILL_WEIGHT, 0.45),
        optional_skill=_clamp_weight(settings.MATCHER_OPTIONAL_SKILL_WEIGHT, 0.15),
        semantic=_clamp_weight(settings.MATCHER_SEMANTIC_WEIGHT, 0.25),
        experience=_clamp_weight(settings.MATCHER_EXPERIENCE_WEIGHT, 0.15),
    )
    return weights.normalized()


def _normalize_skill(skill: str) -> str:
    return skill.strip().lower().replace("  ", " ")


def _title_skill(skill: str) -> str:
    parts = skill.split()
    return " ".join(p.upper() if p in {"ai", "ml", "nlp", "sql", "aws", "gcp", "ci/cd"} else p.capitalize() for p in parts)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
    return ordered


def extract_skills(text: str) -> List[str]:
    haystack = f" {text.lower()} "
    found: List[str] = []
    for skill in KNOWN_SKILLS:
        s = _normalize_skill(skill)
        pattern = rf"(?<![a-z0-9]){re.escape(s)}(?![a-z0-9])"
        if re.search(pattern, haystack):
            found.append(_title_skill(s))
    # include frequently used abbreviations that may not be explicit in list form
    abbreviations = {
        "ml": "Machine Learning",
        "nlp": "NLP",
        "ai": "AI",
    }
    tokens = set(extract_tokens(text))
    for token, label in abbreviations.items():
        if token in tokens and label not in found:
            found.append(label)
    return sorted(set(found))


def _model_ready() -> bool:
    return not settings.MATCHER_DISABLE_EMBEDDINGS


def warmup_model() -> None:
    if not _model_ready():
        return
    try:
        model = get_model()
        model.encode(["warmup"], convert_to_tensor=True)
    except Exception:
        # Keep service available even if model is unavailable at startup.
        return


def _cached_embedding(text: str):
    return cached_embedding(text)


def _semantic_similarity(job_description: str, resume_text: str) -> float:
    if not _model_ready():
        raise RuntimeError("Semantic model disabled")
    jd_text = (job_description or "").strip()[:8000]
    resume = (resume_text or "").strip()[:8000]
    if not jd_text or not resume:
        return 0.0
    jd_embedding = _cached_embedding(jd_text)
    resume_embedding = _cached_embedding(resume)
    sentence_transformer_util = get_sentence_transformers_utils()
    similarity = sentence_transformer_util.cos_sim(jd_embedding, resume_embedding).item()
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def _skill_neighbors(skill: str) -> set[str]:
    key = _normalize_skill(skill)
    neighbors = set(_normalize_skill(s) for s in SKILL_GRAPH.get(key, []))
    # reverse lookup for graph edges where key appears as a neighbor
    for src, targets in SKILL_GRAPH.items():
        normalized_targets = {_normalize_skill(t) for t in targets}
        if key in normalized_targets:
            neighbors.add(_normalize_skill(src))
    return neighbors


def _extract_skills_from_lines(lines: List[str]) -> List[str]:
    skills: List[str] = []
    for line in lines:
        if not line.strip():
            continue
        # handle bullets like "- React, JavaScript, CSS"
        chunks = re.split(r"[,/|]", line)
        for chunk in chunks:
            extracted = extract_skills(chunk)
            skills.extend(extracted)
    return sorted(set(skills))


def _extract_min_experience_years(text: str) -> Optional[float]:
    lowered = (text or "").lower()
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:-\s*\d+(?:\.\d+)?)?\s+years?",
        r"minimum\s+of\s+(\d+(?:\.\d+)?)\s+years?",
        r"at\s+least\s+(\d+(?:\.\d+)?)\s+years?",
        r"(\d+(?:\.\d+)?)\+?\s+yrs",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def _extract_education_requirements(text: str) -> List[str]:
    lowered = (text or "").lower()
    matches = [_title_skill(keyword.replace(".", "")) for keyword in EDUCATION_KEYWORDS if keyword in lowered]
    if "b.tech" in lowered:
        matches.append("B.Tech")
    if "b.e" in lowered:
        matches.append("B.E")
    if "m.tech" in lowered:
        matches.append("M.Tech")
    if "mba" in lowered:
        matches.append("MBA")
    return _dedupe_keep_order(matches)


def _extract_role_title(job_description: str) -> Optional[str]:
    text = (job_description or "").strip()
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    role_patterns = [
        r"(?:job title|role|position)\s*:\s*([^\n]+)",
        r"hiring\s+for\s+([^\n,.]+)",
        r"looking\s+for\s+(?:an?\s+)?([^\n,.]+)",
        r"seeking\s+(?:an?\s+)?([^\n,.]+)",
    ]
    for pattern in role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .:-").title()[:120]
    for line in lines[:3]:
        if any(token in line.lower() for token in ("engineer", "developer", "scientist", "manager", "analyst")):
            return line.strip(" .:-").title()[:120]
    return None


def _infer_role_category(role_title: Optional[str], jd_skills: List[str], job_description: str) -> str:
    combined = " ".join(filter(None, [role_title or "", job_description or "", " ".join(jd_skills)])).lower()
    best_role = "general"
    best_score = 0
    for role_name, keywords in ROLE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in combined)
        if score > best_score:
            best_score = score
            best_role = role_name
    return best_role.title()


def _extract_jd_keywords(text: str, required_skills: List[str], optional_skills: List[str]) -> List[str]:
    skills_first = required_skills + optional_skills
    tokens = [token for token in extract_tokens(text) if len(token) > 2]
    extra_keywords: List[str] = []
    for token in tokens:
        if token in {"the", "and", "for", "with", "role", "job", "years", "year", "team", "using"}:
            continue
        if token.isdigit():
            continue
        extra_keywords.append(token)
    titled_keywords = [_title_skill(skill.lower()) for skill in skills_first]
    raw_keywords = [keyword.upper() if keyword in {"aws", "gcp", "sql", "api"} else keyword.title() for keyword in extra_keywords]
    return _dedupe_keep_order(titled_keywords + raw_keywords)[:15]


def parse_jd_skill_buckets(job_description: str) -> Tuple[List[str], List[str]]:
    text = (job_description or "").strip()
    if not text:
        return [], []

    lines = [line.strip(" -*\t") for line in text.splitlines()]
    required_lines: List[str] = []
    optional_lines: List[str] = []
    section = "required"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if "required skill" in lower or lower in {"requirements", "must have", "must-have"}:
            section = "required"
            continue
        if "nice to have" in lower or "optional skill" in lower or "preferred" in lower:
            section = "optional"
            continue
        if section == "required":
            required_lines.append(line)
        else:
            optional_lines.append(line)

    required_skills = _extract_skills_from_lines(required_lines)
    optional_skills = _extract_skills_from_lines(optional_lines)

    if ai_assistant.is_ai_enabled():
        try:
            llm_skills = ai_assistant.extract_jd_skills(text)
            if llm_skills:
                normalized = sorted({_title_skill(_normalize_skill(skill)) for skill in llm_skills})
                required_skills = normalized
        except Exception:
            pass

    if not required_skills and not optional_skills:
        try:
            from ..services import nlp_extractor

            if nlp_extractor.is_nlp_available():
                nlp_entities = nlp_extractor.extract_jd_entities(text)
                extracted = nlp_entities.get("technologies") or []
                required_skills = [str(skill) for skill in extracted]
        except Exception:
            pass

    # fallback: if no sectioned skills extracted, treat all detected JD skills as required
    if not required_skills and not optional_skills:
        required_skills = extract_skills(text)

    # remove overlap from optional
    required_set = {s.lower() for s in required_skills}
    optional_skills = [s for s in optional_skills if s.lower() not in required_set]
    return required_skills, optional_skills


def parse_job_description(job_description: str) -> Dict[str, object]:
    text = (job_description or "").strip()
    if not text:
        return {
            "role": None,
            "role_category": "General",
            "required_skills": [],
            "optional_skills": [],
            "keywords": [],
            "minimum_experience_years": None,
            "education_requirements": [],
        }

    required_skills, optional_skills = parse_jd_skill_buckets(text)
    role = _extract_role_title(text)
    if not role:
        try:
            from ..services import nlp_extractor

            if nlp_extractor.is_nlp_available():
                roles = nlp_extractor.extract_jd_entities(text).get("roles")
                if roles:
                    role = roles[0]
        except Exception:
            pass
    jd_skills = required_skills + optional_skills
    return {
        "role": role,
        "role_category": _infer_role_category(role, jd_skills, text),
        "required_skills": required_skills,
        "optional_skills": optional_skills,
        "keywords": _extract_jd_keywords(text, required_skills, optional_skills),
        "minimum_experience_years": _extract_min_experience_years(text),
        "education_requirements": _extract_education_requirements(text),
    }


def compare_resume_to_jd(job_description: str, resume_text: str) -> Dict[str, object]:
    jd = (job_description or "").strip()
    resume = (resume_text or "").strip()
    if not jd or not resume:
        return {
            "score": 0.0,
            "summary": "Insufficient text for skill-based comparison.",
            "jd_analysis": parse_job_description(jd),
            "required_skills": [],
            "optional_skills": [],
            "skills": [],
            "matched_skills": [],
            "related_skills": [],
            "missing_skills": [],
            "score_breakdown": {
                "required_skill_score": 0.0,
                "optional_skill_score": 0.0,
                "semantic_score": 0.0,
                "experience_score": 0.0,
                "final_score": 0.0,
                "semantic_mode": "unavailable",
            },
            "selected": False,
            "selected_threshold": 0.6,
            "ai_evaluation": "Insufficient text for analysis.",
        }

    jd_analysis = parse_job_description(jd)
    required_skills = [str(s) for s in (jd_analysis.get("required_skills") or [])]
    optional_skills = [str(s) for s in (jd_analysis.get("optional_skills") or [])]
    jd_skills = sorted(set(required_skills + optional_skills))
    try:
        from ..services import nlp_extractor

        if nlp_extractor.is_nlp_available():
            resume_skills = nlp_extractor.extract_technologies(resume)
        else:
            resume_skills = extract_skills(resume)
    except Exception:
        resume_skills = extract_skills(resume)
    resume_skill_set = {s.lower() for s in resume_skills}

    required_match = [s for s in required_skills if s.lower() in resume_skill_set]
    optional_match = [s for s in optional_skills if s.lower() in resume_skill_set]
    matched_skills = required_match + optional_match
    matched_set = {s.lower() for s in matched_skills}

    related_skills: List[str] = []
    for jd_skill in jd_skills:
        jd_norm = jd_skill.lower()
        if jd_norm in matched_set:
            continue
        neighbors = _skill_neighbors(jd_skill)
        if neighbors.intersection(resume_skill_set):
            related_skills.append(jd_skill)

    related_set = {s.lower() for s in related_skills}
    missing_skills = [s for s in jd_skills if s.lower() not in matched_set and s.lower() not in related_set]

    required_total = len(required_skills)
    optional_total = len(optional_skills)
    required_match_count = len(required_match)
    optional_match_count = len(optional_match)
    related_count = len(related_skills)

    required_skill_score = (
        (required_match_count + (0.35 * related_count)) / required_total if required_total else 1.0
    )
    optional_skill_score = (
        (optional_match_count + (0.2 * related_count)) / optional_total if optional_total else 1.0
    )
    required_skill_score = max(0.0, min(1.0, required_skill_score))
    optional_skill_score = max(0.0, min(1.0, optional_skill_score))

    semantic_score = 0.0
    semantic_mode = "semantic"
    try:
        semantic_score = _semantic_similarity(jd, resume)
    except Exception:
        semantic_mode = "fallback_token_overlap"
        jd_tokens = set(extract_tokens(jd))
        resume_tokens = set(extract_tokens(resume))
        overlap = len(jd_tokens.intersection(resume_tokens))
        semantic_score = (overlap / len(jd_tokens)) if jd_tokens else 0.0

    resume_experience_years = _extract_min_experience_years(resume)
    jd_min_experience = jd_analysis.get("minimum_experience_years")
    if jd_min_experience is None:
        experience_score = 1.0 if resume_experience_years is not None else 0.6
    elif resume_experience_years is None:
        experience_score = 0.35
    elif float(jd_min_experience) <= 0:
        experience_score = 1.0
    else:
        experience_score = min(float(resume_experience_years) / float(jd_min_experience), 1.0)

    weights = get_matcher_weights()
    final_score = (
        (weights.required_skill * required_skill_score)
        + (weights.optional_skill * optional_skill_score)
        + (weights.semantic * semantic_score)
        + (weights.experience * experience_score)
    )
    score = max(0.0, min(1.0, final_score))
    score = round(score, 4)
    threshold = 0.6
    selected = score >= threshold

    summary = (
        f"Semantic: {round(semantic_score * 100, 1)}% ({semantic_mode}) | "
        f"Required: {round(required_skill_score * 100, 1)}% | "
        f"Optional: {round(optional_skill_score * 100, 1)}% | "
        f"Experience: {round(experience_score * 100, 1)}% | "
        f"Matched: {len(matched_skills)} Related: {len(related_skills)} Missing: {len(missing_skills)}"
    )

    ai_evaluation = (
        f"Role: {jd_analysis.get('role') or jd_analysis.get('role_category')}\n"
        f"Score: {round(score * 100)}%\n"
        f"Matched: {', '.join(matched_skills) if matched_skills else 'None'}\n"
        f"Related: {', '.join(related_skills) if related_skills else 'None'}\n"
        f"Missing: {', '.join(missing_skills) if missing_skills else 'None'}\n"
        f"Experience Fit: {round(experience_score * 100)}%"
    )

    return {
        "score": score,
        "summary": summary,
        "jd_analysis": jd_analysis,
        "required_skills": required_skills,
        "optional_skills": optional_skills,
        "skills": resume_skills,
        "matched_skills": matched_skills,
        "related_skills": related_skills,
        "missing_skills": missing_skills,
        "score_breakdown": {
            "required_skill_score": round(required_skill_score, 4),
            "optional_skill_score": round(optional_skill_score, 4),
            "semantic_score": round(semantic_score, 4),
            "experience_score": round(experience_score, 4),
            "required_skill_weight": round(weights.required_skill, 4),
            "optional_skill_weight": round(weights.optional_skill, 4),
            "semantic_weight": round(weights.semantic, 4),
            "experience_weight": round(weights.experience, 4),
            "total_weight": round(
                weights.required_skill + weights.optional_skill + weights.semantic + weights.experience,
                4,
            ),
            "final_score": round(score, 4),
            "semantic_mode": semantic_mode,
        },
        "semantic_score": semantic_score,
        "selected": selected,
        "selected_threshold": threshold,
        "ai_evaluation": ai_evaluation,
    }
