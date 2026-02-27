import { cn } from "@/lib/utils";

type Mode = "chat" | "controlled" | "autonomous";

interface ModeSwitcherProps {
  mode: Mode;
  onChange: (mode: Mode) => void;
}

const modes: { id: Mode; label: string }[] = [
  { id: "chat", label: "Chat" },
  { id: "controlled", label: "Controlled" },
  { id: "autonomous", label: "Autonomous" },
];

export function ModeSwitcher({ mode, onChange }: ModeSwitcherProps) {
  return (
    <div className="inline-flex items-center rounded-md border border-border bg-card p-0.5">
      {modes.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded transition-colors duration-150",
            mode === m.id
              ? "bg-accent text-foreground border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
