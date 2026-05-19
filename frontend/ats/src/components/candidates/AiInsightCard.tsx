import { motion } from "framer-motion";
import { BrainCircuit, MessageSquareQuote } from "lucide-react";
import type { AiSummary, Resume } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getRisks, getStringList, getStrengths, getSummaryText } from "@/components/candidates/profileUtils";

export function AiInsightCard({ summary, resume, isLoading }: { summary?: AiSummary; resume: Resume; isLoading?: boolean }) {
  const strengths = getStrengths(summary, resume);
  const risks = getRisks(summary, resume);
  const questions = getStringList(summary?.suggested_questions).slice(0, 3);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
      <Card className="overflow-hidden">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>AI candidate summary</CardTitle>
              <CardDescription>Concise recruiter brief generated from resume signals.</CardDescription>
            </div>
            <div className="rounded-md border bg-muted p-2">
              <BrainCircuit className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="text-sm leading-6 text-muted-foreground">
              {isLoading ? "Generating candidate intelligence..." : getSummaryText(summary, resume)}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <SignalList title="Best signals" items={strengths} variant="success" fallback="No strong signals extracted yet." />
            <SignalList title="Review carefully" items={risks} variant="warning" fallback="No major risks detected." />
          </div>

          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
              <MessageSquareQuote className="h-3.5 w-3.5" />
              Suggested interview probes
            </div>
            <div className="space-y-2">
              {(questions.length ? questions : ["Ask for a recent project where they used the matched skills.", "Validate ownership, impact, and collaboration style."]).map(
                (question) => (
                  <div key={question} className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
                    {question}
                  </div>
                ),
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function SignalList({
  title,
  items,
  variant,
  fallback,
}: {
  title: string;
  items: string[];
  variant: "success" | "warning";
  fallback: string;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.length ? (
          items.slice(0, 6).map((item) => (
            <Badge key={item} variant={variant}>
              {item}
            </Badge>
          ))
        ) : (
          <Badge variant="outline">{fallback}</Badge>
        )}
      </div>
    </div>
  );
}
