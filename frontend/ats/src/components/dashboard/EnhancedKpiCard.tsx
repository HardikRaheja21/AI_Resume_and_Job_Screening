import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export interface KpiData {
  title: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
    direction: "up" | "down" | "neutral";
  };
  variant?: "default" | "success" | "warning" | "danger";
}

export function EnhancedKpiCard({ data, delay = 0 }: { data: KpiData; delay?: number }) {
  const getTrendColor = () => {
    if (!data.trend) return "";
    if (data.trend.direction === "up") return "text-emerald-600 dark:text-emerald-400";
    if (data.trend.direction === "down") return "text-red-600 dark:text-red-400";
    return "text-muted-foreground";
  };

  const getTrendIcon = () => {
    if (!data.trend) return null;
    if (data.trend.direction === "up") return <TrendingUp className="h-3 w-3" />;
    if (data.trend.direction === "down") return <TrendingDown className="h-3 w-3" />;
    return null;
  };

  const getBgColor = () => {
    switch (data.variant) {
      case "success":
        return "bg-emerald-500/10";
      case "warning":
        return "bg-amber-500/10";
      case "danger":
        return "bg-red-500/10";
      default:
        return "bg-muted";
    }
  };

  const getIconColor = () => {
    switch (data.variant) {
      case "success":
        return "text-emerald-600 dark:text-emerald-400";
      case "warning":
        return "text-amber-600 dark:text-amber-400";
      case "danger":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.1 }}
    >
      <Card className="relative overflow-hidden hover:shadow-lg transition-shadow">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-muted-foreground">{data.title}</p>
              <p className="mt-3 text-4xl font-bold tracking-tight">
                {data.value}
              </p>
              <div className="mt-3 flex items-center gap-2">
                {data.trend && (
                  <div className={`flex items-center gap-1 text-xs font-medium ${getTrendColor()}`}>
                    {getTrendIcon()}
                    <span>{data.trend.value > 0 ? "+" : ""}{data.trend.value}%</span>
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  {data.detail}
                </p>
              </div>
            </div>
            <div className={`rounded-lg ${getBgColor()} p-3`}>
              <data.icon className={`h-5 w-5 ${getIconColor()}`} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
