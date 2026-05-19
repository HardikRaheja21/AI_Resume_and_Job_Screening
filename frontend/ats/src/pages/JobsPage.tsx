import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Briefcase, Plus, Search, Trash2 } from "lucide-react";
import { archiveJob, createJob, listJobs, updateJob } from "@/api/jobs";
import type { Job } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/format";

export function JobsPage() {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Job | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: listJobs });

  const save = useMutation({
    mutationFn: () => (editing ? updateJob(editing.id, { title, description }) : createJob({ title, description })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setEditing(null);
      setTitle("");
      setDescription("");
      toast({ title: "Job saved", description: "The job description is ready for candidate matching." });
    },
  });

  const archive = useMutation({
    mutationFn: archiveJob,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast({ title: "Job archived" });
    },
  });

  const filtered = useMemo(() => {
    const normalized = query.toLowerCase();
    return (jobs.data || []).filter((job) => job.is_active && `${job.title} ${job.description}`.toLowerCase().includes(normalized));
  }, [jobs.data, query]);

  function startEdit(job: Job) {
    setEditing(job);
    setTitle(job.title);
    setDescription(job.description);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <div className="page-shell space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Job description management</p>
          <h1 className="text-2xl font-semibold">Jobs</h1>
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>{editing ? "Edit job" : "Create job"}</CardTitle>
            <CardDescription>Paste a detailed JD so the AI matching layer has strong context.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input id="title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Senior Frontend Engineer" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Responsibilities, required skills, experience..." required />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={save.isPending}>
                  <Plus className="h-4 w-4" />
                  {save.isPending ? "Saving..." : editing ? "Update job" : "Create job"}
                </Button>
                {editing ? (
                  <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                ) : null}
              </div>
            </form>
          </CardContent>
        </Card>
        <div className="space-y-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="pl-9" placeholder="Search jobs..." value={query} onChange={(event) => setQuery(event.target.value)} />
          </div>
          {filtered.length === 0 ? (
            <EmptyState icon={Briefcase} title="No active jobs" description="Create your first job description to start ranking candidates." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filtered.map((job) => (
                <Card key={job.id} className="transition-shadow hover:shadow-soft">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle>{job.title}</CardTitle>
                        <CardDescription>{job.role_category || "Recruiting role"}</CardDescription>
                      </div>
                      <Badge variant="success">Active</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="line-clamp-3 text-sm text-muted-foreground">{job.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {(job.required_skills || []).slice(0, 4).map((skill) => (
                        <Badge key={skill} variant="outline">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Created {formatDate(job.created_at)}</span>
                      <span>0 candidates</span>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => startEdit(job)}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => archive.mutate(job.id)}>
                        <Trash2 className="h-4 w-4" />
                        Archive
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
