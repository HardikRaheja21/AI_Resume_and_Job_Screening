import { Filter, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { STAGE_LABELS } from "@/lib/constants";
import type { Job } from "@/api/types";
import type { CandidateFilters } from "@/hooks/useCandidateFilters";

export function FilterDrawer({
  isOpen,
  onClose,
  filters,
  onFiltersChange,
  jobs,
}: {
  isOpen: boolean;
  onClose: () => void;
  filters: CandidateFilters;
  onFiltersChange: (updates: Partial<CandidateFilters>) => void;
  jobs: Job[];
}) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-background sm:w-96">
        <div className="border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Filters</h2>
          <Button
            size="icon"
            variant="ghost"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-auto px-6 py-4 space-y-4">
          <div>
            <label className="text-sm font-medium">Stage</label>
            <Select
              value={filters.stage}
              onChange={(e) => onFiltersChange({ stage: e.target.value })}
              className="mt-2 w-full"
            >
              <option value="">All stages</option>
              {Object.entries(STAGE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Job</label>
            <Select
              value={filters.job}
              onChange={(e) => onFiltersChange({ job: e.target.value })}
              className="mt-2 w-full"
            >
              <option value="">All jobs</option>
              {jobs.map((job) => (
                <option key={job.id} value={String(job.id)}>
                  {job.title}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Minimum Match Score</label>
            <Select
              value={String(filters.minScore)}
              onChange={(e) =>
                onFiltersChange({ minScore: Number(e.target.value) })
              }
              className="mt-2 w-full"
            >
              <option value="0">Any score</option>
              <option value="50">50%+</option>
              <option value="70">70%+</option>
              <option value="85">85%+</option>
            </Select>
          </div>
        </div>

        <div className="border-t px-6 py-4 space-y-2">
          <Button
            onClick={onClose}
            className="w-full"
          >
            Apply Filters
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              onFiltersChange({
                stage: "",
                job: "",
                minScore: 0,
                skills: [],
              });
            }}
            className="w-full"
          >
            Clear All
          </Button>
        </div>
      </div>
    </>
  );
}

export function FilterButton({ activeCount }: { activeCount: number }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setIsOpen(true)}
        className="relative"
      >
        <Filter className="h-4 w-4" />
        {activeCount > 0 && (
          <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {activeCount}
          </span>
        )}
      </Button>

      {isOpen && (
        <FilterDrawer
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          filters={{} as CandidateFilters}
          onFiltersChange={() => {}}
          jobs={[]}
        />
      )}
    </>
  );
}
