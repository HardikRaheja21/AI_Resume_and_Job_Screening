export const STAGES = ["new", "screened", "shortlisted", "interview", "offer", "rejected"] as const;

export const STAGE_LABELS: Record<string, string> = {
  new: "New",
  screened: "Screened",
  shortlisted: "Shortlisted",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

export const PROCESSING_STEPS = [
  "Queued",
  "Parsing",
  "OCR",
  "Skill Extraction",
  "Match Scoring",
  "Embedding",
  "AI Summary",
  "Completed",
];
