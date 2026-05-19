import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function ActiveFilters({
  filters,
  onRemove,
  stageLabels,
  jobsMap,
}: {
  filters: {
    stage?: string;
    job?: string;
    minScore?: number;
    skills?: string[];
  };
  onRemove: (key: string, value?: string) => void;
  stageLabels: Record<string, string>;
  jobsMap: Record<string, string>;
}) {
  if (!Object.values(filters).some((v) => v)) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {filters.stage && (
        <Badge variant="secondary" className="gap-1">
          {stageLabels[filters.stage]}
          <button
            onClick={() => onRemove("stage")}
            className="ml-1 hover:opacity-70"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}
      {filters.job && (
        <Badge variant="secondary" className="gap-1">
          {jobsMap[filters.job] || "Job"}
          <button
            onClick={() => onRemove("job")}
            className="ml-1 hover:opacity-70"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}
      {filters.minScore ? (
        <Badge variant="secondary" className="gap-1">
          {filters.minScore}%+ match
          <button
            onClick={() => onRemove("minScore")}
            className="ml-1 hover:opacity-70"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ) : null}
      {filters.skills?.map((skill) => (
        <Badge key={skill} variant="secondary" className="gap-1">
          {skill}
          <button
            onClick={() => onRemove("skills", skill)}
            className="ml-1 hover:opacity-70"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
    </div>
  );
}
