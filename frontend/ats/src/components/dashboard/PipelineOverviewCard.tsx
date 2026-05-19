import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { Resume } from "@/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { STAGE_LABELS } from "@/lib/constants";

export function PipelineOverviewCard({
  candidates,
  isLoading,
}: {
  candidates: Resume[];
  isLoading: boolean;
}) {
  const pipelineData = Object.entries(STAGE_LABELS).map(([stage, label]) => ({
    stage: label,
    count: candidates.filter((c) => c.stage === stage).length,
  }));

  const total = candidates.length;

  return (
    <Card className="flex flex-col">
      <CardHeader className="border-b bg-muted/30">
        <CardTitle>Hiring Pipeline</CardTitle>
        <CardDescription>
          Candidate distribution across stages ({total} total)
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pt-6">
        {isLoading ? (
          <Skeleton className="h-80 w-full" />
        ) : candidates.length === 0 ? (
          <div className="flex h-80 items-center justify-center text-center">
            <p className="text-sm text-muted-foreground">
              No candidates yet. Pipeline will appear after uploads.
            </p>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={pipelineData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <defs>
                  <linearGradient id="colorBar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.9} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                <XAxis
                  dataKey="stage"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />
                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid hsl(var(--border))",
                    backgroundColor: "hsl(var(--background))",
                  }}
                  labelStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Bar
                  dataKey="count"
                  fill="url(#colorBar)"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Pipeline Stats */}
        {!isLoading && candidates.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-6 grid grid-cols-2 gap-3 border-t pt-4 sm:grid-cols-3"
          >
            {pipelineData.map((item) => {
              const percentage = total > 0 ? ((item.count / total) * 100).toFixed(0) : "0";
              return (
                <div key={item.stage} className="text-center">
                  <p className="text-xs text-muted-foreground">{item.stage}</p>
                  <p className="mt-1 text-lg font-semibold">{item.count}</p>
                  <p className="text-xs text-muted-foreground">{percentage}%</p>
                </div>
              );
            })}
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
