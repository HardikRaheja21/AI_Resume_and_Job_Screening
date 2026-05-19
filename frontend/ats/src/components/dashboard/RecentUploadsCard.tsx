import { motion } from "framer-motion";
import { FileText, CheckCircle, AlertCircle, Clock } from "lucide-react";
import type { Resume } from "@/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelative } from "@/lib/format";

export function RecentUploadsCard({
  uploads,
  isLoading,
}: {
  uploads: Resume[];
  isLoading: boolean;
}) {
  const getStatusIcon = (status?: string | null) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />;
      case "processing":
        return <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status?: string | null) => {
    switch (status) {
      case "completed":
        return <Badge variant="success" className="text-xs">Ready</Badge>;
      case "processing":
        return <Badge variant="warning" className="text-xs">Processing</Badge>;
      case "error":
        return <Badge variant="danger" className="text-xs">Failed</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs">Queued</Badge>;
    }
  };

  return (
    <Card className="flex flex-col">
      <CardHeader className="border-b bg-muted/30">
        <CardTitle>Recent Uploads</CardTitle>
        <CardDescription>
          Latest resume uploads and processing status
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 space-y-2 pt-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <Skeleton key={idx} className="h-12" />
          ))
        ) : uploads.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-center">
            <p className="text-sm text-muted-foreground">
              No uploads yet. Start by uploading resumes.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {uploads.map((upload, idx) => (
              <motion.div
                key={upload.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="group rounded-lg border p-3 transition-all hover:bg-muted/50"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {getStatusIcon(upload.processing_status)}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {upload.name || upload.filename}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatRelative(upload.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {getStatusBadge(upload.processing_status)}
                  </div>
                </div>

                {/* Progress bar for processing uploads */}
                {upload.processing_status === "processing" && (
                  <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <motion.div
                      className="h-full bg-primary"
                      initial={{ width: "10%" }}
                      animate={{ width: "70%" }}
                      transition={{
                        duration: 3,
                        repeat: Infinity,
                        repeatType: "reverse",
                      }}
                    />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
