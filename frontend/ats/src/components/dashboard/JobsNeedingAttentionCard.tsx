import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { AlertCircle, TrendingDown, Clock, ArrowRight } from "lucide-react";
import type { Job, Resume } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface JobAlert {
  job: Job;
  candidateCount: number;
  pendingInterviews: number;
  alertType: "low_candidates" | "pending_interviews" | "stale";
}

export function JobsNeedingAttentionCard({
  jobs,
  candidates,
  isLoading,
}: {
  jobs: Job[];
  candidates: Resume[];
  isLoading: boolean;
}) {
  const getJobAlerts = (): JobAlert[] => {
    const alerts: JobAlert[] = [];

    for (const job of jobs) {
      if (!job.is_active) continue;

      const jobCandidates = candidates.filter(
        (c) => String(c.job_id) === String(job.id) || c.matched_job === job.title,
      );
      const pendingInterviews = jobCandidates.filter(
        (c) => c.stage === "interview",
      ).length;

      if (jobCandidates.length < 5) {
        alerts.push({
          job,
          candidateCount: jobCandidates.length,
          pendingInterviews,
          alertType: "low_candidates",
        });
      } else if (pendingInterviews > 0) {
        alerts.push({
          job,
          candidateCount: jobCandidates.length,
          pendingInterviews,
          alertType: "pending_interviews",
        });
      }
    }

    return alerts.slice(0, 4);
  };

  const alerts = getJobAlerts();

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "low_candidates":
        return <TrendingDown className="h-4 w-4" />;
      case "pending_interviews":
        return <Clock className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getAlertVariant = (type: string): "warning" | "danger" | "secondary" => {
    switch (type) {
      case "low_candidates":
        return "warning";
      case "pending_interviews":
        return "secondary";
      default:
        return "danger";
    }
  };

  const getAlertLabel = (alert: JobAlert) => {
    switch (alert.alertType) {
      case "low_candidates":
        return `${alert.candidateCount} candidate${alert.candidateCount !== 1 ? "s" : ""}`;
      case "pending_interviews":
        return `${alert.pendingInterviews} pending interview${alert.pendingInterviews !== 1 ? "s" : ""}`;
      default:
        return "Needs attention";
    }
  };

  return (
    <Card className="flex flex-col">
      <CardHeader className="border-b bg-muted/30">
        <CardTitle>Jobs Needing Attention</CardTitle>
        <CardDescription>
          Positions with low candidate counts or pending interviews
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 space-y-2 pt-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, idx) => (
            <Skeleton key={idx} className="h-16" />
          ))
        ) : alerts.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-center">
            <p className="text-sm text-muted-foreground">
              All jobs are on track!
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert, idx) => (
              <motion.div
                key={`${alert.job.id}-${alert.alertType}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Link to={`/jobs/${alert.job.id}`}>
                  <div className="group rounded-lg border p-3 transition-all hover:border-primary/50 hover:bg-muted/50">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="truncate font-medium text-sm group-hover:text-primary transition-colors">
                          {alert.job.title}
                        </p>
                        <div className="mt-2 flex items-center gap-2">
                          <Badge
                            variant={getAlertVariant(alert.alertType)}
                            className="text-xs"
                          >
                            {getAlertIcon(alert.alertType)}
                            <span className="ml-1">
                              {getAlertLabel(alert)}
                            </span>
                          </Badge>
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}

        {alerts.length > 0 && (
          <Link to="/jobs">
            <Button variant="outline" className="mt-4 w-full justify-between">
              Manage all jobs
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
