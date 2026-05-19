import type { AiSummary, Resume, ResumeChunk } from "@/api/types";
import { scoreValue } from "@/lib/format";

export type EvidenceSnippet = {
  title: string;
  text: string;
  score?: number;
};

export function getCandidateName(resume: Resume) {
  return resume.name || resume.filename.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
}

export function getCandidateRole(resume: Resume) {
  return resume.matched_job || resume.role || resume.role_category || "Candidate";
}

export function parseSkillList(raw?: string | null) {
  if (!raw) return [];
  return raw
    .split(/[,;\n]/)
    .map((skill) => skill.trim())
    .filter(Boolean);
}

export function getAllSkills(resume: Resume) {
  const combined = [
    ...(resume.matched_skills || []),
    ...(resume.related_skills || []),
    ...parseSkillList(resume.extracted_skills),
  ];
  return Array.from(new Set(combined)).slice(0, 18);
}

export function getSummaryText(summary: AiSummary | undefined, resume: Resume) {
  const maybeSummary = summary?.summary || summary?.candidate_summary || summary?.overview;
  if (typeof maybeSummary === "string" && maybeSummary.trim()) return maybeSummary;
  if (resume.ai_evaluation) return resume.ai_evaluation;
  return `${getCandidateName(resume)} has a ${scoreValue(resume.match_score)}% semantic fit for ${getCandidateRole(
    resume,
  )}. Review matched skills, gaps, and evidence before moving this candidate forward.`;
}

export function getStringList(value: unknown) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value === "string" && value.trim()) {
    return value
      .split(/[,;\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

export function getStrengths(summary: AiSummary | undefined, resume: Resume) {
  return (
    getStringList(summary?.strengths).length ? getStringList(summary?.strengths) : resume.matched_skills || []
  ).slice(0, 5);
}

export function getRisks(summary: AiSummary | undefined, resume: Resume) {
  return (getStringList(summary?.risks).length ? getStringList(summary?.risks) : resume.missing_skills || []).slice(0, 5);
}

export function getRecommendation(summary: AiSummary | undefined, resume: Resume) {
  const recommendation = summary?.recommendation || summary?.decision || resume.final_decision;
  return typeof recommendation === "string" && recommendation.trim() ? recommendation : "Review and shortlist if role priorities match.";
}

export function getEvidenceSnippets(resume: Resume, chunks?: ResumeChunk[]): EvidenceSnippet[] {
  const chunkSnippets = (chunks || [])
    .map((chunk) => ({
      title: chunk.chunk_type ? chunk.chunk_type.replace(/_/g, " ") : "Resume evidence",
      text: chunk.content_snippet,
      score: chunk.score,
    }))
    .filter((chunk) => chunk.text)
    .slice(0, 4);

  if (chunkSnippets.length) return chunkSnippets;

  const text = resume.parsed_text || "";
  return text
    .split(/\n{2,}|\.\s+/)
    .map((snippet) => snippet.trim())
    .filter((snippet) => snippet.length > 80)
    .slice(0, 4)
    .map((snippet, index) => ({
      title: index === 0 ? "Profile evidence" : "Resume excerpt",
      text: snippet.length > 260 ? `${snippet.slice(0, 260)}...` : snippet,
    }));
}

export function getScoreBreakdown(resume: Resume) {
  const existing = Object.entries(resume.score_breakdown || {})
    .filter(([, value]) => typeof value === "number")
    .slice(0, 4)
    .map(([label, value]) => ({
      label: label.replace(/_/g, " "),
      value: Math.round(value <= 1 ? value * 100 : value),
    }));

  if (existing.length) return existing;

  return [
    { label: "semantic fit", value: scoreValue(resume.match_score) },
    { label: "matched skills", value: Math.min(100, (resume.matched_skills?.length || 0) * 12) },
    { label: "experience", value: resume.experience_years ? Math.min(100, Math.round(resume.experience_years * 12)) : 45 },
    { label: "missing gaps", value: Math.max(0, 100 - (resume.missing_skills?.length || 0) * 14) },
  ];
}
