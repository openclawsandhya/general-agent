import { useState } from "react";
import { 
  MessageSquare, Play, ListChecks, Layers, Activity, Settings,
  ChevronLeft, ChevronRight
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activeItem: string;
  onItemClick: (item: string) => void;
  onSettingsClick: () => void;
}

const navItems = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "autonomous", label: "Autonomous Runs", icon: Play },
  { id: "controlled", label: "Controlled Tasks", icon: ListChecks },
  { id: "sessions", label: "Sessions", icon: Layers },
  { id: "agents", label: "Agent Status", icon: Activity },
];

export function AppSidebar({ activeItem, onItemClick, onSettingsClick }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "h-screen flex flex-col border-r border-border bg-card transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold tracking-tight text-foreground">SANDHYA</span>
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="text-sm font-semibold tracking-tight text-foreground">AI</span>
          </div>
        )}
        {collapsed && <span className="w-1.5 h-1.5 rounded-full bg-primary mx-auto" />}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {navItems.map((item) => {
          const isActive = activeItem === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onItemClick(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150",
                "hover:bg-accent",
                isActive
                  ? "text-foreground bg-accent border-l-2 border-primary"
                  : "text-muted-foreground border-l-2 border-transparent"
              )}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="p-2 border-t border-border space-y-0.5">
        <button
          onClick={onSettingsClick}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors duration-150"
        >
          <Settings className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </button>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center py-2 rounded-md text-muted-foreground hover:bg-accent transition-colors duration-150"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
}
