import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, ExternalLink } from "lucide-react";
import type { Resume } from "@/api/types";
import { ScoreBadge } from "@/components/candidates/ScoreBadge";
import { StageBadge } from "@/components/candidates/StageBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function TopCandidatesCard({
  candidates,
  isLoading,
}: {
  candidates: Resume[];
  isLoading: boolean;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="border-b bg-muted/30">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Top Candidates</CardTitle>
            <CardDescription>
              Highest semantic matches ready for review
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-2 pt-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <Skeleton key={idx} className="h-20" />
          ))
        ) : candidates.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-center">
            <p className="text-sm text-muted-foreground">
              No candidates yet. Upload resumes to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {candidates.map((candidate, idx) => (
              <motion.div
                key={candidate.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Link
                  to={`/candidates/${candidate.id}`}
                  className="group block rounded-lg border p-3 transition-all hover:border-primary/50 hover:bg-muted/50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-sm group-hover:text-primary transition-colors">
                        {candidate.name || candidate.filename}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <p className="truncate text-xs text-muted-foreground">
                          {candidate.role || candidate.matched_job || "Reviewing..."}
                        </p>
                        <StageBadge stage={candidate.stage} />
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <ScoreBadge score={candidate.match_score} />
                      <button className="text-muted-foreground hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
        {candidates.length > 0 && (
          <Link to="/candidates">
            <Button
              variant="outline"
              className="mt-4 w-full justify-between"
            >
              View all candidates
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
