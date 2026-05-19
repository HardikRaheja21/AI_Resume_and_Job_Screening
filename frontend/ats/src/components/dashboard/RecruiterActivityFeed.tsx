import { motion } from "framer-motion";
import {
  FileText,
  User,
  CheckCircle,
  MessageSquare,
  Upload,
  Zap,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelative } from "@/lib/format";

export type ActivityEvent = {
  id: string | number;
  type: "moved_stage" | "ai_summary" | "interview" | "note" | "upload" | "scored";
  candidateName: string;
  details: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

const activityIcons: Record<string, typeof FileText> = {
  moved_stage: CheckCircle,
  ai_summary: Zap,
  interview: User,
  note: MessageSquare,
  upload: Upload,
  scored: Clock,
};

const activityLabels: Record<string, string> = {
  moved_stage: "Candidate moved",
  ai_summary: "AI summary",
  interview: "Interview",
  note: "Note added",
  upload: "Uploaded",
  scored: "Scored",
};

const activityColors: Record<string, string> = {
  moved_stage: "text-blue-600 dark:text-blue-400 bg-blue-500/10",
  ai_summary: "text-purple-600 dark:text-purple-400 bg-purple-500/10",
  interview: "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10",
  note: "text-amber-600 dark:text-amber-400 bg-amber-500/10",
  upload: "text-cyan-600 dark:text-cyan-400 bg-cyan-500/10",
  scored: "text-rose-600 dark:text-rose-400 bg-rose-500/10",
};

export function RecruiterActivityFeed({
  activities,
  isLoading,
}: {
  activities: ActivityEvent[];
  isLoading: boolean;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="border-b bg-muted/30">
        <CardTitle>Activity Feed</CardTitle>
        <CardDescription>Recent recruiter actions and AI insights</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pt-4">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, idx) => (
              <Skeleton key={idx} className="h-12" />
            ))}
          </div>
        ) : activities.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-center">
            <p className="text-sm text-muted-foreground">
              No activity yet. Start reviewing candidates.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {activities.map((activity, idx) => {
              const Icon = activityIcons[activity.type] || FileText;
              const color = activityColors[activity.type] || "text-muted-foreground bg-muted";

              return (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="relative flex gap-3 pb-4 last:pb-0"
                >
                  {/* Timeline line */}
                  {idx < activities.length - 1 && (
                    <div className="absolute left-4 top-10 h-6 w-px bg-border" />
                  )}

                  {/* Icon */}
                  <div className={`flex-shrink-0 rounded-full p-2 ${color}`}>
                    <Icon className="h-4 w-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">
                          {activityLabels[activity.type]}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {activity.candidateName}
                        </p>
                        {activity.details && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {activity.details}
                          </p>
                        )}
                      </div>
                      <time className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                        {formatRelative(activity.timestamp)}
                      </time>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
