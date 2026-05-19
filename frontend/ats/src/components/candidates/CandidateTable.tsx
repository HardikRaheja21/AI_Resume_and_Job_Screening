import { Link } from "react-router-dom";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import { motion } from "framer-motion";
import type { Resume } from "@/api/types";
import { Checkbox } from "@/components/ui/checkbox";
import { ScoreBadge } from "@/components/candidates/ScoreBadge";
import { StageBadge } from "@/components/candidates/StageBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatRelative } from "@/lib/format";
import type { SortField, SortDirection } from "@/hooks/useCandidateFilters";

export function CandidateTable({
  candidates,
  selected,
  onSelected,
  sort,
  onSort,
}: {
  candidates: Resume[];
  selected: number[];
  onSelected: (ids: number[]) => void;
  sort: { field: SortField; direction: SortDirection };
  onSort: (field: SortField) => void;
}) {
  function toggle(id: number) {
    onSelected(
      selected.includes(id)
        ? selected.filter((item) => item !== id)
        : [...selected, id],
    );
  }

  function toggleAll() {
    onSelected(selected.length === candidates.length ? [] : candidates.map((c) => c.id));
  }

  const SortIcon = ({
    field,
  }: {
    field: SortField;
  }) => {
    if (sort.field !== field) return <ArrowUpDown className="h-3 w-3 opacity-40" />;
    return sort.direction === "asc" ? (
      <ArrowUp className="h-3 w-3" />
    ) : (
      <ArrowDown className="h-3 w-3" />
    );
  };

  return (
    <div className="w-full overflow-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-background">
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={selected.length === candidates.length && candidates.length > 0}
                onChange={toggleAll}
              />
            </TableHead>
            <TableHead
              className="cursor-pointer select-none"
              onClick={() => onSort("name")}
            >
              <button className="flex items-center gap-2 font-semibold">
                Candidate
                <SortIcon field="name" />
              </button>
            </TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Current Role</TableHead>
            <TableHead
              className="cursor-pointer select-none"
              onClick={() => onSort("score")}
            >
              <button className="flex items-center gap-2 font-semibold">
                Match
                <SortIcon field="score" />
              </button>
            </TableHead>
            <TableHead>Stage</TableHead>
            <TableHead className="hidden sm:table-cell">Skills</TableHead>
            <TableHead
              className="cursor-pointer select-none"
              onClick={() => onSort("date")}
            >
              <button className="flex items-center gap-2 font-semibold">
                Updated
                <SortIcon field="date" />
              </button>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {candidates.map((candidate, idx) => (
            <motion.tr
              key={candidate.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.02 }}
              className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
            >
              <TableCell className="w-10">
                <Checkbox
                  checked={selected.includes(candidate.id)}
                  onChange={() => toggle(candidate.id)}
                />
              </TableCell>
              <TableCell>
                <Link
                  to={`/candidates/${candidate.id}`}
                  className="block font-medium text-foreground transition-colors hover:text-primary"
                >
                  <div className="truncate">{candidate.name || candidate.filename}</div>
                  <div className="text-xs text-muted-foreground">
                    {candidate.email || "No email"}
                  </div>
                </Link>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {candidate.email ? (
                  <a href={`mailto:${candidate.email}`} className="hover:underline">
                    {candidate.email}
                  </a>
                ) : (
                  "—"
                )}
              </TableCell>
              <TableCell>
                {candidate.role ? (
                  <div className="text-sm">{candidate.role}</div>
                ) : (
                  <div className="text-xs text-muted-foreground">—</div>
                )}
              </TableCell>
              <TableCell>
                <ScoreBadge score={candidate.match_score} />
              </TableCell>
              <TableCell>
                <StageBadge stage={candidate.stage} />
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <div className="flex flex-wrap gap-1">
                  {(candidate.matched_skills || []).slice(0, 2).map((skill) => (
                    <Badge key={skill} variant="outline" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                  {(candidate.matched_skills || []).length > 2 && (
                    <Badge variant="secondary" className="text-xs">
                      +{(candidate.matched_skills || []).length - 2}
                    </Badge>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatRelative(candidate.updated_at)}
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
