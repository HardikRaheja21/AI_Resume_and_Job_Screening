import { motion } from "framer-motion";
import { BrainCircuit, CheckCircle2, FileUp, GitBranch, MessageSquareText, Timer } from "lucide-react";
import type { Resume } from "@/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatRelative } from "@/lib/format";

export function ActivityTimelineCard({ resume }: { resume: Resume }) {
  const events = [
    {
      label: "Resume uploaded",
      detail: resume.filename,
      time: resume.created_at,
      icon: FileUp,
    },
    {
      label: resume.processing_status === "failed" ? "Processing needs attention" : "Parsing completed",
      detail: resume.processing_error || "Profile fields and skills extracted",
      time: resume.updated_at,
      icon: CheckCircle2,
    },
    {
      label: "AI summary generated",
      detail: "Candidate brief and fit signals prepared",
      time: resume.updated_at,
      icon: BrainCircuit,
    },
    {
      label: "Pipeline stage updated",
      detail: `Candidate is currently in ${resume.stage}`,
      time: resume.updated_at,
      icon: GitBranch,
    },
    {
      label: resume.interview_score ? "Interview evaluated" : "Interview not started",
      detail: resume.interview_score ? `Interview score: ${resume.interview_score}` : "Start interview from the workspace when ready",
      time: resume.updated_at,
      icon: MessageSquareText,
    },
  ];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14 }}>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Activity timeline</CardTitle>
              <CardDescription>Recruiting actions and AI processing milestones.</CardDescription>
            </div>
            <Timer className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-5">
            {events.map((event, index) => (
              <div key={`${event.label}-${index}`} className="relative flex gap-3">
                {index < events.length - 1 ? <span className="absolute left-4 top-8 h-full w-px bg-border" /> : null}
                <div className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-card">
                  <event.icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="min-w-0 pb-1">
                  <p className="text-sm font-medium">{event.label}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{event.detail}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatRelative(event.time)} · {formatDate(event.time)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
