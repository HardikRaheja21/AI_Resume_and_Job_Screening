import type { Resume } from "@/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreBadge } from "@/components/candidates/ScoreBadge";
import { Badge } from "@/components/ui/badge";
import { scoreValue } from "@/lib/format";

export function MatchExplanationPanel({ resume }: { resume: Resume }) {
  const breakdown = resume.score_breakdown || {};
  const rows = Object.entries(breakdown).slice(0, 4);
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>Match explanation</CardTitle>
            <CardDescription>Why this candidate ranks for the selected job.</CardDescription>
          </div>
          <ScoreBadge score={resume.match_score} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {(rows.length ? rows : [["semantic", scoreValue(resume.match_score)], ["skills", resume.matched_skills?.length || 0]]).map(([label, value]) => (
            <div key={label} className="rounded-md border p-3">
              <p className="text-xs uppercase text-muted-foreground">{String(label).replace(/_/g, " ")}</p>
              <p className="mt-1 text-2xl font-semibold">{typeof value === "number" ? Math.round(value) : String(value)}</p>
            </div>
          ))}
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Matched skills</p>
          <div className="flex flex-wrap gap-2">
            {(resume.matched_skills || []).slice(0, 8).map((skill) => <Badge key={skill} variant="success">{skill}</Badge>)}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Missing skills</p>
          <div className="flex flex-wrap gap-2">
            {(resume.missing_skills || []).slice(0, 8).map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
