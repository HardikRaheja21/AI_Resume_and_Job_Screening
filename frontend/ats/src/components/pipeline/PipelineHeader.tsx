import { motion } from "framer-motion";
import {
  TrendingUp,
  Users,
  Target,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

interface PipelineHeaderProps {
  totalCandidates: number;
  avgScore: number;
  moveRate: number;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export function PipelineHeader({
  totalCandidates,
  avgScore,
  moveRate,
  searchQuery,
  onSearchChange,
}: PipelineHeaderProps) {
  const stats = [
    {
      label: "Total Candidates",
      value: totalCandidates,
      icon: Users,
      color: "text-blue-600 dark:text-blue-400",
    },
    {
      label: "Avg Match Score",
      value: `${avgScore}%`,
      icon: Target,
      color: "text-emerald-600 dark:text-emerald-400",
    },
    {
      label: "Move Rate",
      value: `${moveRate}%`,
      icon: TrendingUp,
      color: "text-purple-600 dark:text-purple-400",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Title */}
      <div>
        <p className="text-sm font-medium text-muted-foreground">Workflow</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">
          Hiring Pipeline
        </h1>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Filter candidates..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" disabled className="opacity-80">
          Export
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-3 sm:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="overflow-hidden">
                <div className="flex items-center justify-between p-4">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-1 text-2xl font-bold">{stat.value}</p>
                  </div>
                  <div className={`rounded-lg bg-muted p-3 ${stat.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
