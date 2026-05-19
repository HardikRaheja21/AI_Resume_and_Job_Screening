import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SettingsPage() {
  return (
    <div className="page-shell">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Admin settings will be added after the core recruiter workflow is stable.</CardContent>
      </Card>
    </div>
  );
}
