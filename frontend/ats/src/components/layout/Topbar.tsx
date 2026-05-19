import { Bell, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useAuth } from "@/auth/useAuth";

export function Topbar() {
  const { user, logout } = useAuth();
  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur-xl lg:pl-64">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <div className="relative hidden w-full max-w-md sm:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search candidates, jobs, skills..." />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </Button>
          <ThemeToggle />
          <div className="hidden items-center gap-3 rounded-md border bg-card px-3 py-1.5 md:flex">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
              {(user?.full_name || user?.email || "R").slice(0, 1).toUpperCase()}
            </div>
            <div className="leading-tight">
              <p className="text-sm font-medium">{user?.full_name || "Recruiter"}</p>
              <p className="text-xs text-muted-foreground">{user?.role || "recruiter"}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={logout}>
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
}
