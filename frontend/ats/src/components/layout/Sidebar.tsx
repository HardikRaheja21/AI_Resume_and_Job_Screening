import { Briefcase, Columns3, LayoutDashboard, Settings, UploadCloud, Users } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

const items = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Jobs", to: "/jobs", icon: Briefcase },
  { label: "Uploads", to: "/uploads", icon: UploadCloud },
  { label: "Candidates", to: "/candidates", icon: Users },
  { label: "Pipeline", to: "/pipeline", icon: Columns3 },
  { label: "Settings", to: "/settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r bg-card/80 backdrop-blur-xl lg:block">
      <div className="flex h-16 items-center border-b px-5">
        <div>
          <p className="text-sm font-semibold">AI Recruiter ATS</p>
          <p className="text-xs text-muted-foreground">Recruitment intelligence</p>
        </div>
      </div>
      <nav className="space-y-1 p-3">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                isActive && "bg-accent text-accent-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
