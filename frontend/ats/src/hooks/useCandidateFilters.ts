import { useCallback, useMemo, useState } from "react";
import type { Resume } from "@/api/types";
import { scoreValue } from "@/lib/format";

export type SortField = "name" | "score" | "date" | "experience";
export type SortDirection = "asc" | "desc";

export interface CandidateFilters {
  query: string;
  stage: string;
  job: string;
  minScore: number;
  skills: string[];
}

export interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

export function useCandidateFilters(
  candidates: Resume[],
  initialFilters: Partial<CandidateFilters> = {},
) {
  const [filters, setFilters] = useState<CandidateFilters>({
    query: initialFilters.query ?? "",
    stage: initialFilters.stage ?? "",
    job: initialFilters.job ?? "",
    minScore: initialFilters.minScore ?? 0,
    skills: initialFilters.skills ?? [],
  });

  const [sort, setSort] = useState<SortConfig>({
    field: "score",
    direction: "desc",
  });

  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 15,
  });

  const filtered = useMemo(() => {
    let result = candidates;

    // Search filter
    if (filters.query) {
      const normalized = filters.query.toLowerCase();
      result = result.filter((candidate) => {
        const haystack = `${candidate.name} ${candidate.email} ${candidate.filename} ${candidate.matched_job} ${(candidate.matched_skills || []).join(" ")}`.toLowerCase();
        return haystack.includes(normalized);
      });
    }

    // Stage filter
    if (filters.stage) {
      result = result.filter((c) => c.stage === filters.stage);
    }

    // Job filter
    if (filters.job) {
      result = result.filter(
        (c) =>
          String(c.job_id) === filters.job ||
          c.matched_job === filters.job,
      );
    }

    // Score filter
    result = result.filter((c) => scoreValue(c.match_score) >= filters.minScore);

    // Skills filter
    if (filters.skills.length > 0) {
      result = result.filter((c) => {
        const candidateSkills = (c.matched_skills || []).map((s) => s.toLowerCase());
        return filters.skills.some((skill) =>
          candidateSkills.some((cs) =>
            cs.includes(skill.toLowerCase()),
          ),
        );
      });
    }

    return result;
  }, [candidates, filters]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (sort.field) {
        case "name":
          aVal = (a.name || a.filename).toLowerCase();
          bVal = (b.name || b.filename).toLowerCase();
          break;
        case "score":
          aVal = scoreValue(a.match_score);
          bVal = scoreValue(b.match_score);
          break;
        case "date":
          aVal = new Date(a.updated_at).getTime();
          bVal = new Date(b.updated_at).getTime();
          break;
        case "experience":
          aVal = a.experience_years ?? 0;
          bVal = b.experience_years ?? 0;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sort.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sort.direction === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [filtered, sort]);

  const paged = useMemo(() => {
    const start = (pagination.page - 1) * pagination.pageSize;
    const end = start + pagination.pageSize;
    return sorted.slice(start, end);
  }, [sorted, pagination]);

  const totalPages = Math.ceil(sorted.length / pagination.pageSize);

  const updateFilters = useCallback((updates: Partial<CandidateFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
    setPagination({ page: 1, pageSize: pagination.pageSize });
  }, [pagination.pageSize]);

  const toggleSort = useCallback((field: SortField) => {
    setSort((prev) => {
      if (prev.field === field) {
        return {
          field,
          direction: prev.direction === "asc" ? "desc" : "asc",
        };
      }
      return { field, direction: "desc" };
    });
  }, []);

  const setPageSize = useCallback((size: number) => {
    setPagination({ page: 1, pageSize: size });
  }, []);

  const setPage = useCallback((page: number) => {
    setPagination((prev) => ({ ...prev, page }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({
      query: "",
      stage: "",
      job: "",
      minScore: 0,
      skills: [],
    });
    setSort({ field: "score", direction: "desc" });
    setPagination({ page: 1, pageSize: pagination.pageSize });
  }, [pagination.pageSize]);

  const activeFilterCount = useMemo(() => {
    return (
      (filters.query ? 1 : 0) +
      (filters.stage ? 1 : 0) +
      (filters.job ? 1 : 0) +
      (filters.minScore > 0 ? 1 : 0) +
      filters.skills.length
    );
  }, [filters]);

  return {
    filters,
    updateFilters,
    sort,
    toggleSort,
    pagination,
    setPage,
    setPageSize,
    clearFilters,
    activeFilterCount,
    candidates: paged,
    totalCount: sorted.length,
    totalPages,
    currentPage: pagination.page,
  };
}
