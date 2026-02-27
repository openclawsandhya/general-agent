import { Settings, User } from "lucide-react";

interface HeaderProps {
  onSettingsClick: () => void;
}

export function AppHeader({ onSettingsClick }: HeaderProps) {
  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-card/50 backdrop-blur-sm shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">Workspace</span>
        <span className="text-muted-foreground">/</span>
        <span className="text-sm text-muted-foreground">Chat</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-muted-foreground">Connected</span>
        </div>

        {/* Model badge */}
        <div className="px-2.5 py-1 rounded-md bg-accent text-xs font-medium text-muted-foreground border border-border">
          Mistral-7B
        </div>

        <button
          onClick={onSettingsClick}
          className="p-1.5 rounded-md text-muted-foreground hover:bg-accent transition-colors duration-150"
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center">
          <User className="w-3.5 h-3.5 text-muted-foreground" />
        </div>
      </div>
    </header>
  );
}
