import { motion } from "framer-motion";
import { AnimatePresence } from "framer-motion";
import type { Resume } from "@/api/types";
import { KanbanCard } from "@/components/pipeline/KanbanCard";
import { Badge } from "@/components/ui/badge";
import { STAGE_LABELS } from "@/lib/constants";
import {
  getStageColumnColor,
  getStageColor,
} from "@/hooks/usePipelineMetrics";

interface PipelineColumnProps {
  stage: string;
  candidates: Resume[];
  onDragOver: (e: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  draggingId: number | null;
  onDragStart: (id: number) => void;
  onDragEnd: () => void;
  isDropTarget: boolean;
}

export function PipelineColumn({
  stage,
  candidates,
  onDragOver,
  onDrop,
  draggingId,
  onDragStart,
  onDragEnd,
  isDropTarget,
}: PipelineColumnProps) {
  const avgScore = 
    candidates.length > 0
      ? Math.round(
          candidates.reduce((sum, c) => {
            const val =
              (c.match_score ?? 0) <= 1
                ? (c.match_score ?? 0) * 100
                : c.match_score ?? 0;
            return sum + val;
          }, 0) / candidates.length
        )
      : 0;

  const stageColorClass = getStageColumnColor(stage);
  const stageTagColor = getStageColor(stage);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 28 }}
      className={`flex flex-col min-w-[280px] max-w-[320px] rounded-3xl border-2 transition-all shadow-sm ${stageColorClass} ${
        isDropTarget ? "border-primary ring-2 ring-primary/20 bg-primary/5 shadow-lg" : ""
      }`}
      role="region"
      aria-labelledby={`pipeline-column-${stage}`}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <div className="border-b px-4 py-4 bg-gradient-to-r from-background to-muted/50">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div>
            <h2 id={`pipeline-column-${stage}`} className="text-sm font-semibold tracking-tight">
              {STAGE_LABELS[stage]}
            </h2>
            <p className="text-xs text-muted-foreground">
              {candidates.length} candidate{candidates.length !== 1 ? "s" : ""}
            </p>
          </div>
          <Badge variant="secondary" className="text-xs">
            {candidates.length}
          </Badge>
        </div>
        {candidates.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className={`rounded-full border px-2 py-1 ${stageTagColor}`}>
              Avg: {avgScore}%
            </span>
            <span className="rounded-full border px-2 py-1 text-muted-foreground">
              {candidateCountLabel(candidates.length)}
            </span>
          </div>
        )}
      </div>

      <motion.div
        className="flex-1 space-y-3 overflow-y-auto p-3 max-h-[calc(100vh-300px)]"
        layout
      >
        <AnimatePresence mode="popLayout">
          {candidates.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex min-h-[180px] flex-col items-center justify-center rounded-3xl border border-dashed border-muted/40 bg-muted/20 p-5 text-center"
            >
              <p className="text-sm font-semibold">No candidates yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Drag resumes into this stage to organize hiring progress.
              </p>
            </motion.div>
          ) : (
            candidates.map((candidate) => (
              <KanbanCard
                key={candidate.id}
                candidate={candidate}
                isDragging={draggingId === candidate.id}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
              />
            ))
          )}
        </AnimatePresence>
      </motion.div>

      {candidates.length > 0 && (
        <div className="border-t px-4 py-3 text-xs text-muted-foreground text-center bg-muted/20">
          {candidates.length === 1
            ? "1 candidate in this stage"
            : `${candidates.length} candidates in this stage`}
        </div>
      )}
    </motion.div>
  );
}

function candidateCountLabel(count: number) {
  return count === 1 ? "1 candidate" : `${count} candidates`;
}
