export type UserRole = "recruiter" | "admin" | string;

export type User = {
  id: number;
  email: string;
  full_name?: string | null;
  role: UserRole;
  is_active?: boolean;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type Job = {
  id: number;
  owner_id: number;
  title: string;
  description: string;
  role?: string | null;
  role_category?: string | null;
  required_skills: string[];
  optional_skills: string[];
  keywords: string[];
  education_requirements: string[];
  minimum_experience_years?: number | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type Resume = {
  id: number;
  owner_id: number;
  job_id?: number | null;
  filename: string;
  filepath?: string;
  parsed_text?: string | null;
  email?: string | null;
  phone?: string | null;
  name?: string | null;
  education?: string | null;
  experience_years?: number | null;
  extracted_skills?: string | null;
  created_at: string;
  updated_at: string;
  matched_job?: string | null;
  match_score?: number | null;
  role?: string | null;
  role_category?: string | null;
  required_skills?: string[];
  optional_skills?: string[];
  matched_skills?: string[];
  related_skills?: string[];
  missing_skills?: string[];
  jd_keywords?: string[];
  score_breakdown?: Record<string, number>;
  jd_analysis?: Record<string, unknown>;
  ai_evaluation?: string | null;
  interview_score?: number | null;
  final_score?: number | null;
  final_decision?: string | null;
  stage: string;
  notes?: string | null;
  tags?: string | null;
  is_starred?: boolean;
  assigned_to_email?: string | null;
  processing_status?: string | null;
  processing_error?: string | null;
};

export type ProcessingJob = {
  id: number;
  owner_id: number;
  resume_id?: number | null;
  job_id?: number | null;
  job_type: string;
  queue_name: string;
  status: string;
  current_step: string;
  progress: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type ProcessingEvent = {
  id: number;
  processing_job_id: number;
  event_type: string;
  step: string;
  status: string;
  message?: string | null;
  detail?: Record<string, unknown>;
  created_at: string;
};

export type AsyncUploadResponse = {
  batch_job_id?: string | null;
  total_resumes: number;
  jobs: ProcessingJob[];
};

export type ResumeStats = {
  total: number;
  selected: number;
  rejected: number;
  average_score: number;
};

export type AiSummary = {
  summary?: string;
  strengths?: string[];
  risks?: string[];
  suggested_questions?: string[];
  recommendation?: string;
  confidence?: number;
  [key: string]: unknown;
};

export type ResumeChunk = {
  chunk_type: string;
  content_snippet: string;
  score?: number;
  metadata?: Record<string, unknown>;
};
