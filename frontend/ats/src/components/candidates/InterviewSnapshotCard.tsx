import { motion } from "framer-motion";
import { MessageSquareText, TrendingUp } from "lucide-react";
import type { Resume } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function InterviewSnapshotCard({ resume }: { resume: Resume }) {
  const score = resume.interview_score ?? resume.final_score ?? null;
  const hasInterview = score !== null && score !== undefined;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Interview snapshot</CardTitle>
              <CardDescription>Structured evaluation summary when available.</CardDescription>
            </div>
            <MessageSquareText className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border bg-muted/20 p-4">
            <div>
              <p className="text-sm text-muted-foreground">Interview score</p>
              <p className="mt-1 text-3xl font-semibold">{hasInterview ? Math.round(Number(score)) : "--"}</p>
            </div>
            <Badge variant={hasInterview ? "success" : "outline"}>{resume.final_decision || (hasInterview ? "Evaluated" : "Not started")}</Badge>
          </div>
          <div className="rounded-lg border p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              Recommendation
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              {hasInterview
                ? "Use the interview score with resume evidence before making the final hiring decision."
                : "No interview evaluation is attached yet. Start an adaptive interview after shortlist review."}
            </p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
