import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { Resume } from "@/api/types";
import { PipelineColumn } from "@/components/pipeline/PipelineColumn";
import { PipelineHeader } from "@/components/pipeline/PipelineHeader";
import { STAGES } from "@/lib/constants";
import { usePipelineMetrics } from "@/hooks/usePipelineMetrics";

export function PipelineKanban({
  candidates,
  onMove,
  isMoving,
}: {
  candidates: Resume[];
  onMove: (candidate: Resume, stage: string) => void;
  isMoving: boolean;
}) {
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dropStage, setDropStage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const metrics = usePipelineMetrics(candidates);

  const filteredCandidates = useMemo(() => {
    if (!searchQuery.trim()) return candidates;

    const query = searchQuery.toLowerCase();
    return candidates.filter((c) => {
      const haystack = `${c.name} ${c.email} ${c.filename} ${c.matched_job} ${(c.matched_skills || []).join(" ")}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [candidates, searchQuery]);

  const grouped = useMemo(
    () =>
      STAGES.reduce<Record<string, Resume[]>>((acc, stage) => {
        acc[stage] = filteredCandidates.filter(
          (candidate) => candidate.stage === stage
        );
        return acc;
      }, {}),
    [filteredCandidates],
  );

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const stage = (e.currentTarget as HTMLDivElement).dataset.stage;
    setDropStage(stage || null);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    const stage = (e.currentTarget as HTMLDivElement).dataset.stage;
    setDropStage(stage || null);
  };

  const handleDrop = (stage: string) => (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const candidate = candidates.find((item) => item.id === draggingId);
    if (candidate && candidate.stage !== stage) {
      onMove(candidate, stage);
    }
    setDraggingId(null);
    setDropStage(null);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    if (e.currentTarget === e.target) {
      setDropStage(null);
    }
  };

  return (
    <motion.div className="space-y-6">
      <PipelineHeader
        totalCandidates={metrics.total}
        avgScore={metrics.avgScoreOverall}
        moveRate={metrics.moveRate}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <div className="flex flex-col gap-3 rounded-3xl border border-muted/20 bg-muted/10 p-4 md:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Pipeline guide</p>
            <p className="text-sm text-muted-foreground">
              Drag candidates between stages, preview live updates, and keep your hiring flow moving.
            </p>
          </div>
          <div className="rounded-2xl bg-background px-3 py-2 text-xs font-medium text-muted-foreground ring-1 ring-border">
            {isMoving ? "Saving stage change…" : "Ready to move candidates"}
          </div>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="overflow-x-auto pb-4 -mx-4 px-4 md:mx-0 md:px-0 touch-pan-x"
      >
        <div className="flex gap-4 min-w-full md:min-w-fit snap-x snap-mandatory px-2">
          {STAGES.map((stage) => (
            <motion.div
              key={stage}
              layout
              data-stage={stage}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDrop={handleDrop(stage)}
              onDragLeave={handleDragLeave}
              className={`transition-all snap-start ${
                dropStage === stage && draggingId ? "scale-105" : ""
              }`}
            >
              <PipelineColumn
                stage={stage}
                candidates={grouped[stage]}
                onDragOver={handleDragOver}
                onDrop={handleDrop(stage)}
                draggingId={draggingId}
                onDragStart={setDraggingId}
                onDragEnd={() => {
                  setDraggingId(null);
                  setDropStage(null);
                }}
                isDropTarget={dropStage === stage && draggingId !== null}
              />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {filteredCandidates.length === 0 && searchQuery && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-3xl border border-dashed p-8 text-center"
        >
          <p className="text-sm text-muted-foreground">
            No candidates match "{searchQuery}". Try a different search or reset the filters.
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
