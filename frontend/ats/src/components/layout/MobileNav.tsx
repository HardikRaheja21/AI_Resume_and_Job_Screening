import { Briefcase, Columns3, LayoutDashboard, UploadCloud, Users } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

const items = [
  { label: "Home", to: "/", icon: LayoutDashboard },
  { label: "Jobs", to: "/jobs", icon: Briefcase },
  { label: "Upload", to: "/uploads", icon: UploadCloud },
  { label: "Talent", to: "/candidates", icon: Users },
  { label: "Pipe", to: "/pipeline", icon: Columns3 },
];

export function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 grid grid-cols-5 border-t bg-card/95 p-1 backdrop-blur lg:hidden">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center gap-1 rounded-md px-2 py-2 text-[11px] text-muted-foreground",
              isActive && "bg-accent text-accent-foreground",
            )
          }
        >
          <item.icon className="h-4 w-4" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
