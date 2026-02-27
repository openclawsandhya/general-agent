import { useState } from "react";
import { ChevronRight, ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";

const timelineSteps = [
  { step: 1, action: "Initialize session", status: "success" as const, time: "00:00.12" },
  { step: 2, action: "Parse user intent", status: "success" as const, time: "00:01.34" },
  { step: 3, action: "Query knowledge base", status: "success" as const, time: "00:02.89" },
  { step: 4, action: "Generate response", status: "running" as const, time: "00:04.12" },
];

const statusColors: Record<string, string> = {
  success: "status-success",
  failed: "status-failed",
  running: "status-running",
};

export function TelemetryPanel() {
  const [open, setOpen] = useState(true);

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 p-1.5 rounded-l-md bg-card border border-r-0 border-border text-muted-foreground hover:text-foreground transition-colors"
        style={{ right: open ? "320px" : 0 }}
      >
        {open ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>

      {/* Panel */}
      <aside
        className={cn(
          "h-full border-l border-border bg-card overflow-y-auto transition-all duration-200",
          open ? "w-80" : "w-0 border-l-0"
        )}
      >
        {open && (
          <div className="p-4 space-y-6">
            {/* Agent Status */}
            <div>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Agent Status</h3>
              <div className="space-y-2.5">
                {[
                  { label: "Current Mode", value: "Chat" },
                  { label: "Steps Taken", value: "4" },
                  { label: "Last Action", value: "Generate response" },
                  { label: "Confidence", value: "0.94" },
                  { label: "Loop Detection", value: "None" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between py-1.5">
                    <span className="text-xs text-muted-foreground">{item.label}</span>
                    <span className="text-xs font-medium text-foreground">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-border" />

            {/* Timeline */}
            <div>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Execution Timeline</h3>
              <div className="space-y-0">
                {timelineSteps.map((step, idx) => (
                  <div key={step.step} className="flex items-start gap-3 py-2">
                    {/* Vertical line */}
                    <div className="flex flex-col items-center">
                      <div className={cn("w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-medium", statusColors[step.status])}>
                        {step.step}
                      </div>
                      {idx < timelineSteps.length - 1 && (
                        <div className="w-px h-6 bg-border mt-1" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-foreground truncate">{step.action}</span>
                        <span className="text-[10px] text-muted-foreground ml-2 shrink-0">{step.time}</span>
                      </div>
                      <span className={cn("inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded", statusColors[step.status])}>
                        {step.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
