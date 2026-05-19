import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useParams } from "react-router-dom";
import type { Resume } from "@/api/types";
import { getAiSummary, getResume, getResumeChunks, updateResumeNotes } from "@/api/resumes";
import { ActivityTimelineCard } from "@/components/candidates/ActivityTimelineCard";
import { AiInsightCard } from "@/components/candidates/AiInsightCard";
import { CandidateHero } from "@/components/candidates/CandidateHero";
import { InterviewSnapshotCard } from "@/components/candidates/InterviewSnapshotCard";
import { MatchEvidenceCard } from "@/components/candidates/MatchEvidenceCard";
import { MatchScoreCard } from "@/components/candidates/MatchScoreCard";
import { RecruiterNotesCard } from "@/components/candidates/RecruiterNotesCard";
import { ResumePreviewCard } from "@/components/candidates/ResumePreviewCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

export function CandidateProfilePage() {
  const id = Number(useParams().id);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const resume = useQuery({
    queryKey: ["resume", id],
    queryFn: () => getResume(id),
    enabled: Number.isFinite(id) && id > 0,
  });

  const summary = useQuery({
    queryKey: ["candidateAiSummary", id],
    queryFn: () => getAiSummary(id),
    enabled: Number.isFinite(id) && id > 0,
    retry: 1,
  });

  const chunks = useQuery({
    queryKey: ["resumeChunks", id],
    queryFn: () => getResumeChunks(id),
    enabled: Number.isFinite(id) && id > 0,
    retry: 1,
  });

  const notes = useMutation({
    mutationFn: (nextNotes: string) => updateResumeNotes(id, nextNotes),
    onMutate: async (nextNotes) => {
      await queryClient.cancelQueries({ queryKey: ["resume", id] });
      const previous = queryClient.getQueryData<Resume>(["resume", id]);
      queryClient.setQueryData<Resume>(["resume", id], (current) =>
        current ? { ...current, notes: nextNotes, updated_at: new Date().toISOString() } : current,
      );
      return { previous };
    },
    onError: (error, _variables, context) => {
      queryClient.setQueryData(["resume", id], context?.previous);
      toast({
        title: "Notes were not saved",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    },
    onSuccess: () => {
      toast({ title: "Notes saved", description: "Recruiter context was updated for this candidate." });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["resume", id] });
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });

  if (resume.isLoading) return <CandidateProfileSkeleton />;

  if (resume.isError || !resume.data) {
    return (
      <div className="page-shell">
        <Card>
          <CardContent className="flex min-h-80 flex-col items-center justify-center p-8 text-center">
            <div className="mb-4 rounded-lg border bg-muted p-3">
              <AlertTriangle className="h-6 w-6 text-amber-500" />
            </div>
            <h1 className="text-lg font-semibold">Candidate profile unavailable</h1>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              The candidate could not be loaded. Check your connection or retry the request.
            </p>
            <Button className="mt-5" variant="outline" onClick={() => resume.refetch()}>
              <RefreshCw className="h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const candidate = resume.data;

  return (
    <div className="page-shell space-y-6">
      <CandidateHero resume={candidate} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
        <div className="space-y-6">
          <MatchScoreCard resume={candidate} summary={summary.data} />
          <ResumePreviewCard resume={candidate} />
          <MatchEvidenceCard resume={candidate} chunks={chunks.data} />
        </div>

        <aside className="space-y-6 xl:sticky xl:top-20 xl:self-start">
          <AiInsightCard summary={summary.data} resume={candidate} isLoading={summary.isLoading} />
          <RecruiterNotesCard notes={candidate.notes} isSaving={notes.isPending} onSave={(nextNotes) => notes.mutate(nextNotes)} />
          <InterviewSnapshotCard resume={candidate} />
          <ActivityTimelineCard resume={candidate} />
        </aside>
      </div>
    </div>
  );
}

function CandidateProfileSkeleton() {
  return (
    <div className="page-shell space-y-6">
      <Skeleton className="h-40 rounded-lg" />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
        <div className="space-y-6">
          <Skeleton className="h-96 rounded-lg" />
          <Skeleton className="h-[560px] rounded-lg" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-80 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-72 rounded-lg" />
        </div>
      </div>
    </div>
  );
}
