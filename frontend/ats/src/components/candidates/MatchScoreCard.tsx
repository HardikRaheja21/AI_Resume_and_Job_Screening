import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Sparkles, Target } from "lucide-react";
import type { AiSummary, Resume } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getRecommendation, getRisks, getScoreBreakdown, getStrengths } from "@/components/candidates/profileUtils";
import { scoreValue } from "@/lib/format";

export function MatchScoreCard({ resume, summary }: { resume: Resume; summary?: AiSummary }) {
  const score = scoreValue(resume.match_score);
  const strengths = getStrengths(summary, resume);
  const risks = getRisks(summary, resume);
  const breakdown = getScoreBreakdown(resume);

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>Semantic match</CardTitle>
            <CardDescription>Role fit calculated from skills, evidence, and job context.</CardDescription>
          </div>
          <Target className="h-5 w-5 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-[180px_1fr]">
          <div className="flex items-center justify-center">
            <motion.div
              className="relative grid h-40 w-40 place-items-center rounded-full"
              initial={{ background: "conic-gradient(hsl(var(--primary)) 0deg, hsl(var(--muted)) 0deg)" }}
              animate={{
                background: `conic-gradient(hsl(var(--primary)) ${score * 3.6}deg, hsl(var(--muted)) 0deg)`,
              }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <div className="grid h-32 w-32 place-items-center rounded-full border bg-card">
                <div className="text-center">
                  <p className="text-4xl font-semibold">{score}%</p>
                  <p className="text-xs text-muted-foreground">match</p>
                </div>
              </div>
            </motion.div>
          </div>
          <div className="grid content-center gap-3">
            {breakdown.map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-medium capitalize text-muted-foreground">{item.label}</span>
                  <span>{item.value}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    className="h-full rounded-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, item.value))}%` }}
                    transition={{ duration: 0.55, ease: "easeOut" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <InsightCard icon={<Sparkles className="h-4 w-4" />} title="Recommendation" text={getRecommendation(summary, resume)} />
          <InsightCard
            icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />}
            title="Strengths"
            text={strengths.length ? strengths.slice(0, 3).join(", ") : "Review resume evidence for role alignment."}
          />
          <InsightCard
            icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
            title="Risks"
            text={risks.length ? risks.slice(0, 3).join(", ") : "No major missing requirements detected."}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SkillGroup title="Matched skills" skills={resume.matched_skills || []} variant="success" fallback="No matched skills yet" />
          <SkillGroup title="Missing skills" skills={resume.missing_skills || []} variant="warning" fallback="No major gaps detected" />
        </div>
      </CardContent>
    </Card>
  );
}

function InsightCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="rounded-lg border bg-muted/30 p-3 transition-colors hover:bg-muted/50">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="text-sm leading-5 text-muted-foreground">{text}</p>
    </motion.div>
  );
}

function SkillGroup({
  title,
  skills,
  variant,
  fallback,
}: {
  title: string;
  skills: string[];
  variant: "success" | "warning";
  fallback: string;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-2">
        {skills.length ? (
          skills.slice(0, 10).map((skill) => (
            <Badge key={skill} variant={variant}>
              {skill}
            </Badge>
          ))
        ) : (
          <Badge variant="outline">{fallback}</Badge>
        )}
      </div>
    </div>
  );
}
