import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Briefcase, Clock, Target, Users } from "lucide-react";
import { listJobs } from "@/api/jobs";
import { listResumes, getResumeStats } from "@/api/resumes";
import { seedDemoData } from "@/api/demo";
import { EnhancedKpiCard, type KpiData } from "@/components/dashboard/EnhancedKpiCard";
import { TopCandidatesCard } from "@/components/dashboard/TopCandidatesCard";
import { RecentUploadsCard } from "@/components/dashboard/RecentUploadsCard";
import { RecruiterActivityFeed, type ActivityEvent } from "@/components/dashboard/RecruiterActivityFeed";
import { PipelineOverviewCard } from "@/components/dashboard/PipelineOverviewCard";
import { JobsNeedingAttentionCard } from "@/components/dashboard/JobsNeedingAttentionCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { scoreValue } from "@/lib/format";

export function DashboardPage() {
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: listJobs });
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: listResumes });
  const stats = useQuery({ queryKey: ["resumeStats"], queryFn: getResumeStats });

  const candidates = resumes.data || [];
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const allJobs = jobs.data || [];
  const activeJobs = allJobs.filter((job) => job.is_active).length;
  const avgScore = scoreValue(stats.data?.average_score);
  const interviewPending = candidates.filter(
    (candidate) => candidate.stage === "interview",
  ).length;

  const seedMutation = useMutation({
    mutationFn: () => seedDemoData(18),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast({
        title: "Demo data seeded",
        description: `${data.created} candidates were added and the dashboard was refreshed.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Unable to seed demo data",
        description:
          error instanceof Error
            ? error.message
            : "The demo seed endpoint failed.",
        variant: "destructive",
      });
    },
  });

  // Top candidates
  const topCandidates = [...candidates]
    .sort((a, b) => scoreValue(b.match_score) - scoreValue(a.match_score))
    .slice(0, 5);

  // Recent uploads (sorted by created_at desc)
  const recentUploads = [...candidates]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
    .slice(0, 5);

  // Activity feed (mock data based on candidates)
  const activities: ActivityEvent[] = candidates
    .slice(0, 6)
    .map((candidate, idx) => {
      const types: ActivityEvent["type"][] = [
        "moved_stage",
        "ai_summary",
        "interview",
        "note",
        "upload",
        "scored",
      ];
      return {
        id: candidate.id,
        type: types[idx % types.length],
        candidateName: candidate.name || candidate.filename,
        details:
          candidate.stage === "interview"
            ? "Moved to interview stage"
            : `Score: ${scoreValue(candidate.match_score)}%`,
        timestamp: candidate.updated_at,
      };
    });

  // KPI data
  const kpiCards: KpiData[] = [
    {
      title: "Active Jobs",
      value: activeJobs,
      detail: "Open positions",
      icon: Briefcase,
      trend: { value: 0, label: "vs last month", direction: "neutral" },
      variant: "default",
    },
    {
      title: "Candidates",
      value: candidates.length,
      detail: "Processed & reviewed",
      icon: Users,
      trend: { value: 12, label: "new this week", direction: "up" },
      variant: "success",
    },
    {
      title: "Avg Match Score",
      value: `${avgScore}%`,
      detail: "Semantic accuracy",
      icon: Target,
      trend: { value: 5, label: "vs last week", direction: "up" },
      variant: "success",
    },
    {
      title: "Interviews",
      value: interviewPending,
      detail: "Pending interviews",
      icon: Clock,
      trend: { value: 2, label: "this week", direction: "up" },
      variant: "warning",
    },
  ];

  const isLoading =
    jobs.isLoading || resumes.isLoading || stats.isLoading;

  return (
    <div className="page-shell space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Recruiter Command Center
            </p>
            <h1 className="mt-1 text-4xl font-bold tracking-tight">
              Hiring Overview
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {candidates.length === 0
                ? "Get started by uploading resumes or seed demo data"
                : `${candidates.length} candidate${candidates.length !== 1 ? "s" : ""} processed • ${activeJobs} active job${activeJobs !== 1 ? "s" : ""}`}
            </p>
          </div>

          {candidates.length === 0 && (
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => seedMutation.mutate()}
                disabled={seedMutation.isPending}
              >
                {seedMutation.isPending ? "Seeding demo data..." : "Seed demo data"}
              </Button>
            </div>
          )}
        </div>
      </motion.div>

      {/* KPI Cards */}
      <motion.div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, idx) => (
              <Skeleton key={idx} className="h-32" />
            ))
          : kpiCards.map((card, idx) => (
              <EnhancedKpiCard key={card.title} data={card} delay={idx} />
            ))}
      </motion.div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Pipeline + Jobs */}
        <div className="space-y-6 lg:col-span-2">
          {/* Pipeline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <PipelineOverviewCard
              candidates={candidates}
              isLoading={isLoading}
            />
          </motion.div>

          {/* Jobs Needing Attention */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            <JobsNeedingAttentionCard
              jobs={allJobs}
              candidates={candidates}
              isLoading={isLoading}
            />
          </motion.div>
        </div>

        {/* Right Column - Candidates */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col"
        >
          <TopCandidatesCard
            candidates={topCandidates}
            isLoading={isLoading}
          />
        </motion.div>
      </div>

      {/* Bottom Row - Uploads & Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <RecentUploadsCard
            uploads={recentUploads}
            isLoading={isLoading}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <RecruiterActivityFeed
            activities={activities}
            isLoading={isLoading}
          />
        </motion.div>
      </div>
    </div>
  );
}
