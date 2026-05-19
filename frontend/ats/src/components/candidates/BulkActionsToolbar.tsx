import { FileDown, Share2, Star, Trash2, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { updateStage } from "@/api/resumes";
import { STAGE_LABELS } from "@/lib/constants";

export function BulkActionsToolbar({
  selectedCount,
  onDeselect,
  selectedIds,
}: {
  selectedCount: number;
  onDeselect: () => void;
  selectedIds: number[];
}) {
  const queryClient = useQueryClient();

  const stageUpdateMutation = useMutation({
    mutationFn: async ({ id, stage }: { id: number; stage: string }) => {
      return updateStage(id, stage);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });

  const handleBulkStageUpdate = async (stage: string) => {
    for (const id of selectedIds) {
      await stageUpdateMutation.mutateAsync({ id, stage });
    }
    onDeselect();
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <div className="text-sm font-medium text-blue-900 dark:text-blue-100">
          {selectedCount} selected
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onDeselect}
          className="h-6 w-6 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 sm:flex-nowrap">
        <div className="flex items-center gap-1">
          <label className="text-xs font-medium text-blue-900 dark:text-blue-100">
            Move to:
          </label>
          <Select
            onChange={(e) => {
              if (e.target.value) {
                handleBulkStageUpdate(e.target.value);
              }
            }}
            className="h-8 text-sm"
            defaultValue=""
          >
            <option value="">Select stage...</option>
            {Object.entries(STAGE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </div>

        <Button size="sm" variant="ghost" className="h-8 gap-1 text-xs">
          <Star className="h-4 w-4" />
          Star
        </Button>

        <Button size="sm" variant="ghost" className="h-8 gap-1 text-xs">
          <Share2 className="h-4 w-4" />
          Assign
        </Button>

        <Button size="sm" variant="ghost" className="h-8 gap-1 text-xs">
          <FileDown className="h-4 w-4" />
          Export
        </Button>

        <Button
          size="sm"
          variant="ghost"
          className="h-8 gap-1 text-xs text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
          Reject
        </Button>
      </div>
    </div>
  );
}
