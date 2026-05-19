import { motion } from "framer-motion";
import { FileSearch, Lightbulb, XCircle } from "lucide-react";
import type { Resume, ResumeChunk } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getEvidenceSnippets } from "@/components/candidates/profileUtils";

export function MatchEvidenceCard({ resume, chunks }: { resume: Resume; chunks?: ResumeChunk[] }) {
  const evidence = getEvidenceSnippets(resume, chunks);
  const missing = resume.missing_skills || [];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Match explanation</CardTitle>
              <CardDescription>Evidence-backed reasoning recruiters can inspect quickly.</CardDescription>
            </div>
            <FileSearch className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2">
            <ReasoningCard
              icon={<Lightbulb className="h-4 w-4 text-emerald-500" />}
              title="Why this candidate matched"
              text={
                resume.matched_skills?.length
                  ? `Strong overlap on ${resume.matched_skills.slice(0, 5).join(", ")} with relevant resume evidence.`
                  : "The semantic matcher found useful alignment with the job description."
              }
            />
            <ReasoningCard
              icon={<XCircle className="h-4 w-4 text-amber-500" />}
              title="Missing requirements"
              text={missing.length ? `${missing.slice(0, 5).join(", ")} should be validated before final selection.` : "No critical gaps were detected from the extracted profile."}
            />
          </div>

          <div>
            <p className="mb-3 text-xs font-medium uppercase text-muted-foreground">Evidence snippets</p>
            <div className="space-y-3">
              {evidence.length ? (
                evidence.map((item, index) => (
                  <motion.div
                    key={`${item.title}-${index}`}
                    whileHover={{ x: 2 }}
                    className="rounded-lg border bg-muted/20 p-4"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-sm font-medium capitalize">{item.title}</p>
                      {typeof item.score === "number" ? <Badge variant="outline">{Math.round(item.score * 100)} relevance</Badge> : null}
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{item.text}</p>
                  </motion.div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  Evidence snippets will appear after resume parsing and vector indexing complete.
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ReasoningCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="text-sm leading-5 text-muted-foreground">{text}</p>
    </div>
  );
}
