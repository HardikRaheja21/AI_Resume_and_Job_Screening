import { Badge } from "@/components/ui/badge";
import { scoreValue } from "@/lib/format";

export function ScoreBadge({ score }: { score?: number | null }) {
  const value = scoreValue(score);
  const variant = value >= 75 ? "success" : value >= 50 ? "warning" : "danger";
  return <Badge variant={variant}>{value}% match</Badge>;
}
