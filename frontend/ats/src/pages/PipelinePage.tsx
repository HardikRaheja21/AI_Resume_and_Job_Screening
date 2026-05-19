import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Columns3 } from "lucide-react";
import { listResumes, updateStage } from "@/api/resumes";
import type { Resume } from "@/api/types";
import { PipelineKanban } from "@/components/pipeline/PipelineKanban";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

export function PipelinePage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: listResumes });
  const move = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: Resume; stage: string }) =>
      updateStage(candidate.id, stage),
    onMutate: async ({ candidate, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["resumes"] });
      const previous = queryClient.getQueryData<Resume[]>(["resumes"]);
      queryClient.setQueryData<Resume[]>(["resumes"], (current = []) =>
        current.map((item) =>
          item.id === candidate.id ? { ...item, stage } : item
        )
      );
      return { previous };
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(["resumes"], context?.previous);
      toast({
        title: "Stage update failed",
        description:
          "The candidate was restored to the previous stage.",
        variant: "destructive",
      });
    },
    onSuccess: () => {
      toast({ title: "Pipeline updated" });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });

  const isMoving = move.isPending;

  return (
    <div className="page-shell space-y-6">
      {isMoving && (
        <div className="rounded-3xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-primary-foreground shadow-sm">
          Updating candidate stage...
        </div>
      )}
      {resumes.isLoading ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          <Skeleton className="h-12 w-64" />
          <div className="grid gap-3 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} className="h-20" />
            ))}
          </div>
          <div className="flex gap-4 overflow-hidden pb-4">
            {Array.from({ length: 6 }).map((_, idx) => (
              <Skeleton key={idx} className="h-96 w-80 flex-shrink-0" />
            ))}
          </div>
        </motion.div>
      ) : resumes.data?.length ? (
        <PipelineKanban
          candidates={resumes.data}
          onMove={(candidate, stage) =>
            move.mutate({ candidate, stage })
          }
          isMoving={isMoving}
        />
      ) : (
        <EmptyState
          icon={Columns3}
          title="No candidates in the pipeline"
          description="Upload resumes to start moving talent through stages."
        />
      )}
    </div>
  );
}
