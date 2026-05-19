import type { AiSummary, Resume } from "@/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function AISummaryPanel({ summary, resume }: { summary?: AiSummary; resume: Resume }) {
  const strengths = (summary?.strengths as string[] | undefined) || resume.matched_skills?.slice(0, 5) || [];
  const risks = (summary?.risks as string[] | undefined) || resume.missing_skills?.slice(0, 4) || [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>AI candidate summary</CardTitle>
        <CardDescription>Recruiter-readable fit, strengths, and caution areas.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-muted-foreground">
          {summary?.summary || resume.ai_evaluation || `${resume.name || "This candidate"} appears aligned with ${resume.matched_job || "the selected role"} based on extracted skills and semantic match signals.`}
        </p>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Strengths</p>
          <div className="flex flex-wrap gap-2">
            {strengths.length ? strengths.map((item) => <Badge key={item} variant="success">{item}</Badge>) : <Badge variant="outline">Needs review</Badge>}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Risks / gaps</p>
          <div className="flex flex-wrap gap-2">
            {risks.length ? risks.map((item) => <Badge key={item} variant="warning">{item}</Badge>) : <Badge variant="success">No major gaps detected</Badge>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
