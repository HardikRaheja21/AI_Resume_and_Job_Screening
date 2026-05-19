import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, UploadCloud } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listJobs } from "@/api/jobs";
import { enqueueResumeProcessing, uploadResumes } from "@/api/processing";
import type { ProcessingJob } from "@/api/types";
import { UploadDropzone } from "@/components/uploads/UploadDropzone";
import { UploadJobCard } from "@/components/uploads/UploadJobCard";
import { UploadQueueOverview } from "@/components/uploads/UploadQueueOverview";
import { averageProgress, normalizeStatus } from "@/components/uploads/processingUtils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

export function UploadPage() {
  const [jobId, setJobId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [lastBatchCount, setLastBatchCount] = useState(0);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const jobQuery = useQuery({ queryKey: ["jobs"], queryFn: listJobs });
  const selectedJobId = useMemo(() => (jobId ? Number(jobId) : undefined), [jobId]);

  const upload = useMutation({
    mutationFn: () => uploadResumes(files, selectedJobId),
    onMutate: () => {
      setLastBatchCount(files.length);
    },
    onSuccess: (data) => {
      setJobs((current) => mergeJobs(data.jobs, current));
      setFiles([]);
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
      toast({
        title: "AI processing started",
        description: `${data.total_resumes} resume(s) queued for parsing, matching, and summary generation.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Check the files and try again.",
        variant: "destructive",
      });
    },
  });

  const retry = useMutation({
    mutationFn: (job: ProcessingJob) => {
      if (!job.resume_id) throw new Error("This job is not linked to a candidate yet. Re-upload the source file to retry.");
      return enqueueResumeProcessing(job.resume_id, job.job_id || undefined);
    },
    onSuccess: (data) => {
      setJobs((current) => mergeJobs([data.processing_job], current));
      toast({ title: "Reprocessing queued", description: "A new processing job was started for this candidate." });
    },
    onError: (error) => {
      toast({
        title: "Retry failed",
        description: error instanceof Error ? error.message : "Re-upload the file and try again.",
        variant: "destructive",
      });
    },
  });

  const completed = jobs.filter((job) => normalizeStatus(job.status) === "completed").length;
  const failed = jobs.filter((job) => normalizeStatus(job.status) === "failed").length;
  const avgProgress = averageProgress(jobs);
  const showSuccess = jobs.length > 0 && completed + failed === jobs.length && completed > 0;

  function addFiles(nextFiles: File[]) {
    setFiles((current) => {
      const byKey = new Map(current.map((file) => [`${file.name}-${file.size}`, file]));
      nextFiles.forEach((file) => byKey.set(`${file.name}-${file.size}`, file));
      return Array.from(byKey.values());
    });
  }

  function retryJob(job: ProcessingJob) {
    retry.mutate(job);
  }

  return (
    <div className="page-shell space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">AI resume ingestion</p>
          <h1 className="text-2xl font-semibold tracking-normal">Upload workflow</h1>
        </div>
        {jobs.length ? (
          <div className="rounded-lg border bg-card px-4 py-2 text-sm text-muted-foreground">
            Batch progress <span className="font-semibold text-foreground">{avgProgress}%</span>
          </div>
        ) : null}
      </motion.div>

      {jobs.length ? <UploadQueueOverview jobs={jobs} /> : null}

      <AnimatePresence>
        {showSuccess ? (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4"
          >
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-500" />
              <div>
                <p className="text-sm font-medium">Batch completed</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {completed} candidate{completed === 1 ? "" : "s"} processed successfully
                  {failed ? `, ${failed} need attention` : ""}.
                </p>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-6">
          {jobQuery.isLoading ? (
            <Skeleton className="h-[520px] rounded-lg" />
          ) : (
            <UploadDropzone
              files={files}
              jobs={jobQuery.data || []}
              jobId={jobId}
              isUploading={upload.isPending}
              onFiles={addFiles}
              onRemove={(name) => setFiles((current) => current.filter((file) => file.name !== name))}
              onJobChange={setJobId}
              onUpload={() => upload.mutate()}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle>Workflow stages</CardTitle>
              <CardDescription>Every upload moves through parsing, semantic matching, indexing, and AI summary generation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Use this page during demos to show the backend intelligence as a recruiter-friendly live workflow.</p>
              {lastBatchCount ? <p>Last batch queued {lastBatchCount} file(s).</p> : null}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">Processing queue</h2>
            <p className="text-sm text-muted-foreground">Authenticated SSE runs first; polling takes over automatically if the stream disconnects.</p>
          </div>

          <AnimatePresence mode="popLayout">
            {jobs.length ? (
              jobs.map((job) => <UploadJobCard key={job.id} initialJob={job} onRetry={retryJob} />)
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <EmptyState
                  icon={UploadCloud}
                  title="No uploads in this session"
                  description="Select a job and upload resumes to watch the AI processing pipeline in realtime."
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function mergeJobs(incoming: ProcessingJob[], current: ProcessingJob[]) {
  const byId = new Map<number, ProcessingJob>();
  [...incoming, ...current].forEach((job) => byId.set(job.id, job));
  return Array.from(byId.values()).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}
