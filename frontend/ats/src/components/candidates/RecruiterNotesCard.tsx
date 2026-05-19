import { FormEvent, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Save, StickyNote } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export function RecruiterNotesCard({
  notes,
  isSaving,
  onSave,
}: {
  notes?: string | null;
  isSaving: boolean;
  onSave: (notes: string) => void;
}) {
  const [draft, setDraft] = useState(notes || "");

  useEffect(() => {
    setDraft(notes || "");
  }, [notes]);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave(draft);
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Recruiter notes</CardTitle>
              <CardDescription>Private decision context for this candidate.</CardDescription>
            </div>
            <StickyNote className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={submit}>
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Add screening notes, follow-up questions, compensation flags, or next steps..."
              className="min-h-32"
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">{draft.length} characters</p>
              <Button type="submit" disabled={isSaving || draft === (notes || "")}>
                <Save className="h-4 w-4" />
                {isSaving ? "Saving..." : "Save notes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  );
}
