import { motion } from "framer-motion";
import { CheckCircle2, CircleDashed, Loader2, TrendingUp, XCircle } from "lucide-react";
import type { ProcessingJob } from "@/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { averageProgress, normalizeStatus } from "@/components/uploads/processingUtils";

export function UploadQueueOverview({ jobs }: { jobs: ProcessingJob[] }) {
  const completed = jobs.filter((job) => normalizeStatus(job.status) === "completed").length;
  const failed = jobs.filter((job) => normalizeStatus(job.status) === "failed").length;
  const processing = jobs.filter((job) => ["running", "queued", "retrying"].includes(normalizeStatus(job.status))).length;
  const avg = averageProgress(jobs);
  const items = [
    { label: "Total uploads", value: jobs.length, icon: CircleDashed },
    { label: "Processing", value: processing, icon: Loader2 },
    { label: "Completed", value: completed, icon: CheckCircle2 },
    { label: "Failed", value: failed, icon: XCircle },
    { label: "Average progress", value: `${avg}%`, icon: TrendingUp },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {items.map((item, index) => (
        <motion.div key={item.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.03 }}>
          <Card>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="mt-1 text-2xl font-semibold">{item.value}</p>
              </div>
              <div className="rounded-md border bg-muted p-2">
                <item.icon className="h-4 w-4 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
