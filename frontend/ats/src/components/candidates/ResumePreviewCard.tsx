import { motion } from "framer-motion";
import { FileText, GraduationCap, Layers3, Timer, UserCheck } from "lucide-react";
import type { Resume } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAllSkills } from "@/components/candidates/profileUtils";

export function ResumePreviewCard({ resume }: { resume: Resume }) {
  const skills = getAllSkills(resume);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Resume preview</CardTitle>
              <CardDescription>Parsed profile and extracted resume content.</CardDescription>
            </div>
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <ProfileStat icon={<Timer className="h-4 w-4" />} label="Experience" value={`${resume.experience_years ?? "N/A"} yrs`} />
            <ProfileStat icon={<GraduationCap className="h-4 w-4" />} label="Education" value={resume.education || "Not extracted"} />
            <ProfileStat icon={<UserCheck className="h-4 w-4" />} label="Decision" value={resume.final_decision || "Pending"} />
          </div>

          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
              <Layers3 className="h-3.5 w-3.5" />
              Extracted skills
            </div>
            <div className="flex flex-wrap gap-2">
              {skills.length ? (
                skills.map((skill) => (
                  <Badge key={skill} variant="outline">
                    {skill}
                  </Badge>
                ))
              ) : (
                <Badge variant="outline">Skills will appear after parsing</Badge>
              )}
            </div>
          </div>

          <div className="max-h-[560px] overflow-auto rounded-lg border bg-muted/20 p-5 subtle-scrollbar">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-6 text-muted-foreground">
              {resume.parsed_text || "Parsed resume text will appear here after processing completes."}
            </pre>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ProfileStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="rounded-lg border bg-muted/20 p-3">
      <div className="mb-2 flex items-center gap-2 text-xs uppercase text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="line-clamp-2 text-sm font-medium">{value}</p>
    </motion.div>
  );
}
