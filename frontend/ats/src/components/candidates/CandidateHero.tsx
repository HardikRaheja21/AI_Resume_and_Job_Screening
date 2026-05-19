import { motion } from "framer-motion";
import { ArrowLeft, Briefcase, Mail, Phone, Sparkles, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import type { Resume } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScoreBadge } from "@/components/candidates/ScoreBadge";
import { StageBadge } from "@/components/candidates/StageBadge";
import { formatDate } from "@/lib/format";
import { getCandidateName, getCandidateRole } from "@/components/candidates/profileUtils";

export function CandidateHero({ resume }: { resume: Resume }) {
  const name = getCandidateName(resume);
  const role = getCandidateRole(resume);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="border-b bg-muted/30 px-5 py-3">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
              <Link to="/candidates">
                <ArrowLeft className="h-4 w-4" />
                Back to candidates
              </Link>
            </Button>
          </div>
          <div className="flex flex-col gap-5 p-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
                <UserRound className="h-6 w-6" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="truncate text-2xl font-semibold tracking-normal sm:text-3xl">{name}</h1>
                  <StageBadge stage={resume.stage} />
                  <ScoreBadge score={resume.match_score} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Briefcase className="h-4 w-4" />
                    {role}
                  </span>
                  {resume.email ? (
                    <a className="flex items-center gap-1.5 hover:text-foreground" href={`mailto:${resume.email}`}>
                      <Mail className="h-4 w-4" />
                      {resume.email}
                    </a>
                  ) : null}
                  {resume.phone ? (
                    <a className="flex items-center gap-1.5 hover:text-foreground" href={`tel:${resume.phone}`}>
                      <Phone className="h-4 w-4" />
                      {resume.phone}
                    </a>
                  ) : null}
                  <span>Uploaded {formatDate(resume.created_at)}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline">
                <Sparkles className="h-4 w-4" />
                Generate brief
              </Button>
              <Button>Move forward</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
