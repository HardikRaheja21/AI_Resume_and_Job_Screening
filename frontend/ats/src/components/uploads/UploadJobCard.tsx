import { motion } from "framer-motion";
import { Clock3, Eye, RefreshCw, Signal, SignalHigh, SignalLow, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import type { ProcessingJob } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProcessingTimeline } from "@/components/uploads/ProcessingTimeline";
import { useProcessingJobLive } from "@/components/uploads/useProcessingJobLive";
import { getDuration, getLatestEventMessage, normalizeStatus } from "@/components/uploads/processingUtils";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";

export function UploadJobCard({ initialJob, onRetry }: { initialJob: ProcessingJob; onRetry?: (job: ProcessingJob) => void }) {
  const live = useProcessingJobLive(initialJob);
  const job = live.job;
  const status = normalizeStatus(job.status);
  const latestMessage = getLatestEventMessage(live.events);
  const duration = getDuration(job.created_at, status === "completed" || status === "failed" ? job.updated_at : null);

  return (
    <motion.div layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} whileHover={{ y: -2 }}>
      <Card className={cn("overflow-hidden transition-shadow hover:shadow-soft", status === "failed" && "border-destructive/40")}>
        <CardContent className="space-y-5 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold">Processing job #{job.id}</h3>
                <StatusBadge status={status} />
                <StreamBadge state={live.streamState} />
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {job.current_step || "Queued"} · Uploaded {formatDate(job.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm font-semibold">{job.progress || 0}%</div>
              {status === "failed" ? (
                <Button variant="outline" size="sm" onClick={() => onRetry?.(job)}>
                  <RefreshCw className="h-4 w-4" />
                  Retry
                </Button>
              ) : null}
              {status === "completed" && job.resume_id ? (
                <Button asChild size="sm">
                  <Link to={`/candidates/${job.resume_id}`}>
                    <Eye className="h-4 w-4" />
                    View Candidate
                  </Link>
                </Button>
              ) : null}
            </div>
          </div>

          <ProcessingTimeline job={job} />

          <div className="grid gap-3 md:grid-cols-[1fr_180px]">
            <div className="rounded-lg border bg-muted/20 p-3">
              <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">Latest event</p>
              <p className="text-sm leading-6 text-muted-foreground">{latestMessage}</p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <p className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
                <Clock3 className="h-3.5 w-3.5" />
                Duration
              </p>
              <p className="text-sm font-medium">{duration}</p>
            </div>
          </div>

          {status === "failed" ? (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{job.error_message || "Processing failed. Retry or re-upload the resume after checking the file."}</span>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function StatusBadge({ status }: { status: ReturnType<typeof normalizeStatus> }) {
  const variant = status === "completed" ? "success" : status === "failed" ? "danger" : status === "retrying" ? "warning" : "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}

function StreamBadge({ state }: { state: string }) {
  const Icon = state === "live" ? SignalHigh : state === "polling" ? SignalLow : Signal;
  return (
    <Badge variant={state === "live" ? "success" : state === "polling" ? "warning" : "outline"} className="gap-1">
      <Icon className="h-3 w-3" />
      {state}
    </Badge>
  );
}
