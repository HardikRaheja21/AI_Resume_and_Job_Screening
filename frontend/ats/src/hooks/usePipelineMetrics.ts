import { useMemo } from "react";
import type { Resume } from "@/api/types";
import { STAGES } from "@/lib/constants";

export function usePipelineMetrics(candidates: Resume[]) {
  const metrics = useMemo(() => {
    const stageStats = STAGES.reduce<
      Record<string, { count: number; avgScore: number }>
    >((acc, stage) => {
      const stageCandidates = candidates.filter((c) => c.stage === stage);
      const avgScore =
        stageCandidates.length > 0
          ? stageCandidates.reduce((sum, c) => {
              const val =
                (c.match_score ?? 0) <= 1
                  ? (c.match_score ?? 0) * 100
                  : c.match_score ?? 0;
              return sum + val;
            }, 0) / stageCandidates.length
          : 0;

      acc[stage] = {
        count: stageCandidates.length,
        avgScore: Math.round(avgScore),
      };
      return acc;
    }, {});

    const total = candidates.length;
    const avgScoreOverall =
      total > 0
        ? candidates.reduce((sum, c) => {
            const val =
              (c.match_score ?? 0) <= 1
                ? (c.match_score ?? 0) * 100
                : c.match_score ?? 0;
            return sum + val;
          }, 0) / total
        : 0;

    const moveRate =
      candidates.filter((c) => c.stage !== "new").length / Math.max(1, total);

    return {
      total,
      stageStats,
      avgScoreOverall: Math.round(avgScoreOverall),
      moveRate: Math.round(moveRate * 100),
    };
  }, [candidates]);

  return metrics;
}

export function getStageColor(stage: string): string {
  switch (stage) {
    case "new":
      return "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300";
    case "screened":
      return "bg-cyan-500/10 border-cyan-500/30 text-cyan-700 dark:text-cyan-300";
    case "shortlisted":
      return "bg-purple-500/10 border-purple-500/30 text-purple-700 dark:text-purple-300";
    case "interview":
      return "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300";
    case "offer":
      return "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300";
    case "rejected":
      return "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export function getStageColumnColor(stage: string): string {
  switch (stage) {
    case "new":
      return "border-blue-500/20 bg-blue-500/5";
    case "screened":
      return "border-cyan-500/20 bg-cyan-500/5";
    case "shortlisted":
      return "border-purple-500/20 bg-purple-500/5";
    case "interview":
      return "border-amber-500/20 bg-amber-500/5";
    case "offer":
      return "border-emerald-500/20 bg-emerald-500/5";
    case "rejected":
      return "border-red-500/20 bg-red-500/5";
    default:
      return "border-border";
  }
}
