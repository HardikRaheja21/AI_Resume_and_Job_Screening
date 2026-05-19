import { Badge } from "@/components/ui/badge";
import { STAGE_LABELS } from "@/lib/constants";

export function StageBadge({ stage }: { stage?: string }) {
  return <Badge variant={stage === "rejected" ? "danger" : stage === "offer" ? "success" : "secondary"}>{STAGE_LABELS[stage || "new"] || stage}</Badge>;
}
