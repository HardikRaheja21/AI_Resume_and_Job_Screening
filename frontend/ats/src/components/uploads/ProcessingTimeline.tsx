import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import type { ProcessingJob } from "@/api/types";
import { PROCESSING_STEPS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { getStageIndex, normalizeStatus } from "@/components/uploads/processingUtils";

export function ProcessingTimeline({ job }: { job?: ProcessingJob }) {
  const current = getStageIndex(job);
  const status = normalizeStatus(job?.status);
  const failed = status === "failed";
  return (
    <div className="space-y-4">
      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className={cn("h-full rounded-full bg-primary", failed && "bg-destructive")}
          initial={{ width: 0 }}
          animate={{ width: `${job?.progress || (current / (PROCESSING_STEPS.length - 1)) * 100}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {PROCESSING_STEPS.map((step, index) => {
          const done = index < current || status === "completed";
          const active = index === current && status !== "completed";
          return (
            <div
              key={step}
              className={cn(
                "flex items-center gap-2 rounded-md border bg-background px-2.5 py-2 text-xs transition-colors",
                active && "border-primary/40 bg-primary/5",
                failed && active && "border-destructive/40 bg-destructive/5",
              )}
            >
              {failed && active ? (
                <XCircle className="h-4 w-4 text-destructive" />
              ) : done ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={cn("text-muted-foreground", (done || active) && "text-foreground")}>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
