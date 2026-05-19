import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import type { Resume } from "@/api/types";
import { ScoreBadge } from "@/components/candidates/ScoreBadge";
import { Badge } from "@/components/ui/badge";
import { formatRelative } from "@/lib/format";
import { getStageColor } from "@/hooks/usePipelineMetrics";

interface KanbanCardProps {
  candidate: Resume;
  isDragging: boolean;
  onDragStart: (id: number) => void;
  onDragEnd: () => void;
}

export function KanbanCard({
  candidate,
  isDragging,
  onDragStart,
  onDragEnd,
}: KanbanCardProps) {
  const initials = (candidate.name || candidate.filename)
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const stageColor = getStageColor(candidate.stage);
  const roleLabel = candidate.role || candidate.matched_job || "Candidate";

  const handleDragStart = (event: React.DragEvent<HTMLDivElement>) => {
    const element = event.currentTarget as HTMLElement;
    event.dataTransfer.effectAllowed = "move";
    const clone = element.cloneNode(true) as HTMLElement;
    clone.style.position = "absolute";
    clone.style.top = "-9999px";
    clone.style.left = "-9999px";
    clone.style.width = `${element.offsetWidth}px`;
    clone.style.boxShadow = "0 20px 60px rgba(15, 23, 42, 0.18)";
    clone.style.borderRadius = "18px";
    document.body.appendChild(clone);
    event.dataTransfer.setDragImage(clone, element.offsetWidth / 2, 24);
    requestAnimationFrame(() => {
      if (clone.parentElement) clone.parentElement.removeChild(clone);
    });
    onDragStart(candidate.id);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
    >
      <Link to={`/candidates/${candidate.id}`}>
        <motion.div
          whileHover={{ y: -3, boxShadow: "0 18px 35px rgba(15,23,42,0.12)" }}
          whileTap={{ scale: 0.98 }}
          className={`group cursor-grab rounded-3xl border border-border bg-card p-4 shadow-sm transition-all duration-200 hover:shadow-lg active:cursor-grabbing ${
            isDragging ? "opacity-60 scale-95" : ""
          }`}
        >
          <div
            draggable
            onDragStart={handleDragStart}
            onDragEnd={onDragEnd}
            className="space-y-3"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-600 text-sm font-semibold text-white shadow-sm">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate text-foreground transition-colors group-hover:text-primary">
                  {candidate.name || candidate.filename}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {roleLabel}
                </p>
              </div>
            </div>
            <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </div>

          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <ScoreBadge score={candidate.match_score} />
            <span className={`rounded-full border px-2 py-1 text-[11px] font-medium ${stageColor}`}>
              {candidate.stage === "new"
                ? "New"
                : candidate.stage.charAt(0).toUpperCase() + candidate.stage.slice(1)}
            </span>
          </div>

          {(candidate.matched_skills || []).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {(candidate.matched_skills || []).slice(0, 3).map((skill) => (
                <Badge key={skill} variant="outline" className="text-xs">
                  {skill}
                </Badge>
              ))}
              {(candidate.matched_skills || []).length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{(candidate.matched_skills || []).length - 3}
                </Badge>
              )}
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-xs text-muted-foreground">
            <span>{formatRelative(candidate.updated_at)}</span>
            <span className="rounded-full border px-2 py-1 text-[11px] font-medium text-muted-foreground">
              Updated
            </span>
          </div>
          {candidate.notes && (
            <p className="mt-3 text-xs leading-5 text-muted-foreground line-clamp-2">
              {candidate.notes}
            </p>
          )}
          </div>
        </motion.div>
      </Link>
    </motion.div>
  );
}
