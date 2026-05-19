import { DragEvent, useState } from "react";
import { motion } from "framer-motion";
import { FileUp, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import type { Job } from "@/api/types";
import { cn } from "@/lib/utils";

export function UploadDropzone({
  files,
  jobs,
  jobId,
  isUploading,
  onFiles,
  onRemove,
  onJobChange,
  onUpload,
}: {
  files: File[];
  jobs: Job[];
  jobId: string;
  isUploading: boolean;
  onFiles: (files: File[]) => void;
  onRemove: (name: string) => void;
  onJobChange: (jobId: string) => void;
  onUpload: () => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    onFiles(Array.from(event.dataTransfer.files || []));
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>New upload batch</CardTitle>
        <CardDescription>Select a job, then upload resumes for AI parsing and matching.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Select value={jobId} onChange={(event) => onJobChange(event.target.value)}>
          <option value="">Select job</option>
          {jobs
            .filter((job) => job.is_active)
            .map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
        </Select>

        <motion.label
          whileHover={{ y: -2 }}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-muted/30 p-6 text-center transition-colors",
            isDragging && "border-primary bg-primary/5",
          )}
        >
          <div className="mb-4 rounded-lg border bg-card p-3 shadow-sm">
            <UploadCloud className="h-7 w-7 text-muted-foreground" />
          </div>
          <span className="text-sm font-medium">Drop resumes here or browse files</span>
          <span className="mt-1 text-xs text-muted-foreground">PDF, DOCX, DOC, TXT. Multiple files supported.</span>
          <input
            className="sr-only"
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.txt"
            onChange={(event) => onFiles(Array.from(event.target.files || []))}
          />
        </motion.label>

        {files.length ? (
          <div className="space-y-2">
            {files.map((file) => (
              <motion.div
                key={`${file.name}-${file.size}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between gap-3 rounded-md border p-2 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <FileUp className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate">{file.name}</span>
                </span>
                <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => onRemove(file.name)}>
                  <X className="h-4 w-4" />
                </Button>
              </motion.div>
            ))}
          </div>
        ) : null}

        <Button className="w-full" disabled={!files.length || !jobId || isUploading} onClick={onUpload}>
          {isUploading ? "Queueing resumes..." : `Start AI processing${files.length ? ` (${files.length})` : ""}`}
        </Button>
      </CardContent>
    </Card>
  );
}
