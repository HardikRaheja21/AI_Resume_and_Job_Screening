import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Users } from "lucide-react";
import { motion } from "framer-motion";
import { listJobs } from "@/api/jobs";
import { listResumes } from "@/api/resumes";
import { useCandidateFilters } from "@/hooks/useCandidateFilters";
import { CandidateTable } from "@/components/candidates/CandidateTable";
import { SearchInput } from "@/components/candidates/SearchInput";
import { CandidatePagination } from "@/components/candidates/CandidatePagination";
import { BulkActionsToolbar } from "@/components/candidates/BulkActionsToolbar";
import { ActiveFilters } from "@/components/candidates/ActiveFilters";
import { FilterDrawer } from "@/components/candidates/FilterDrawer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { STAGE_LABELS } from "@/lib/constants";

export function CandidatesPage() {
  const [selected, setSelected] = useState<number[]>([]);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);

  const resumes = useQuery({ queryKey: ["resumes"], queryFn: listResumes });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: listJobs });

  const {
    filters,
    updateFilters,
    sort,
    toggleSort,
    candidates,
    pagination,
    setPage,
    setPageSize,
    totalCount,
    totalPages,
    currentPage,
    activeFilterCount,
    clearFilters,
  } = useCandidateFilters(resumes.data || []);

  const jobsMap = (jobs.data || []).reduce(
    (acc, job) => {
      acc[String(job.id)] = job.title;
      return acc;
    },
    {} as Record<string, string>,
  );

  useEffect(() => {
    setSelected([]);
  }, [currentPage, filters, sort]);

  const handleRemoveFilter = (key: string, value?: string) => {
    if (key === "skills" && value) {
      updateFilters({
        skills: filters.skills.filter((s) => s !== value),
      });
    } else {
      updateFilters({ [key as keyof typeof filters]: "" });
    }
  };

  return (
    <div className="page-shell space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <p className="text-sm text-muted-foreground">
            {totalCount} {totalCount === 1 ? "candidate" : "candidates"}
          </p>
          <h1 className="text-3xl font-bold">Talent Database</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </motion.div>

      {/* Main Content Card */}
      <Card className="border">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="text-base">Candidates</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {/* Search & Filters */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="space-y-3"
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:gap-3">
              <div className="flex-1 lg:max-w-md">
                <SearchInput
                  value={filters.query}
                  onChange={(q) => updateFilters({ query: q })}
                  placeholder="Search candidates, skills, emails..."
                />
              </div>

              <div className="flex gap-2">
                <Select
                  value={filters.stage}
                  onChange={(e) => updateFilters({ stage: e.target.value })}
                  className="h-10"
                >
                  <option value="">All stages</option>
                  {Object.entries(STAGE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>

                <Select
                  value={filters.job}
                  onChange={(e) => updateFilters({ job: e.target.value })}
                  className="h-10"
                >
                  <option value="">All jobs</option>
                  {(jobs.data || []).map((item) => (
                    <option key={item.id} value={String(item.id)}>
                      {item.title}
                    </option>
                  ))}
                </Select>

                <Select
                  value={String(filters.minScore)}
                  onChange={(e) =>
                    updateFilters({ minScore: Number(e.target.value) })
                  }
                  className="h-10 hidden sm:block"
                >
                  <option value="0">Any score</option>
                  <option value="50">50%+</option>
                  <option value="70">70%+</option>
                  <option value="85">85%+</option>
                </Select>

                <Button
                  variant="outline"
                  onClick={() => setShowFilterDrawer(true)}
                  className="lg:hidden"
                >
                  More
                </Button>
              </div>
            </div>

            {/* Active Filters */}
            {activeFilterCount > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                <div className="flex flex-col gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-blue-900 dark:text-blue-100">
                      {activeFilterCount} filter{activeFilterCount !== 1 ? "s" : ""} active
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={clearFilters}
                      className="h-6 px-2 text-xs"
                    >
                      Clear all
                    </Button>
                  </div>
                  <ActiveFilters
                    filters={{
                      stage: filters.stage,
                      job: filters.job,
                      minScore: filters.minScore,
                      skills: filters.skills,
                    }}
                    onRemove={handleRemoveFilter}
                    stageLabels={STAGE_LABELS}
                    jobsMap={jobsMap}
                  />
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* Bulk Actions Toolbar */}
          {selected.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <BulkActionsToolbar
                selectedCount={selected.length}
                onDeselect={() => setSelected([])}
                selectedIds={selected}
              />
            </motion.div>
          )}

          {/* Table or Loading/Empty */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            {resumes.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: Math.min(5, pagination.pageSize) }).map(
                  (_, idx) => (
                    <Skeleton key={idx} className="h-14" />
                  ),
                )}
              </div>
            ) : candidates.length > 0 ? (
              <div className="space-y-4">
                <CandidateTable
                  candidates={candidates}
                  selected={selected}
                  onSelected={setSelected}
                  sort={sort}
                  onSort={toggleSort}
                />

                {/* Pagination */}
                <CandidatePagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  pageSize={pagination.pageSize}
                  onPageChange={setPage}
                  onPageSizeChange={setPageSize}
                  totalCount={totalCount}
                />
              </div>
            ) : (
              <EmptyState
                icon={Users}
                title="No candidates found"
                description={
                  activeFilterCount > 0
                    ? "Adjust your filters or search query."
                    : "Upload resumes to get started."
                }
              />
            )}
          </motion.div>
        </CardContent>
      </Card>

      {/* Filter Drawer for Mobile */}
      <FilterDrawer
        isOpen={showFilterDrawer}
        onClose={() => setShowFilterDrawer(false)}
        filters={filters}
        onFiltersChange={(updates) => {
          updateFilters(updates);
          setShowFilterDrawer(false);
        }}
        jobs={jobs.data || []}
      />
    </div>
  );
}
