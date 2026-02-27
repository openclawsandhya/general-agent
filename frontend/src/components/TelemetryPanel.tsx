import { useState, useEffect } from "react";
import { ChevronRight, ChevronLeft, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { checkHealth, type HealthResponse } from "@/lib/api";

interface TelemetryPanelProps {
  currentMode?: string;
  stepsTaken?: number;
  lastAction?: string;
}

export function TelemetryPanel({ currentMode = "chat", stepsTaken = 0, lastAction = "None" }: TelemetryPanelProps) {
  const [open, setOpen] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealthStatus = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const healthData = await checkHealth();
      setHealth(healthData);
      console.log("[Telemetry] Health status:", healthData);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to connect";
      setError(errorMsg);
      console.error("[Telemetry] Health check failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchHealthStatus();

    // Poll every 5 seconds
    const interval = setInterval(fetchHealthStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (available: boolean) => {
    return available ? "text-green-500" : "text-red-500";
  };

  const getStatusDot = (available: boolean) => {
    return (
      <span className={cn(
        "w-2 h-2 rounded-full inline-block mr-2",
        available ? "bg-green-500 animate-pulse" : "bg-red-500"
      )} />
    );
  };

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
            {/* System Status Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                System Status
              </h3>
              <button
                onClick={fetchHealthStatus}
                disabled={loading}
                className="p-1 rounded hover:bg-muted transition-colors"
                title="Refresh status"
              >
                <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
              </button>
            </div>

            {/* Backend Health */}
            <div>
              <h4 className="text-xs font-medium text-foreground mb-3">Backend</h4>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Status</span>
                  <span className={cn("text-xs font-medium flex items-center", 
                    error ? "text-red-500" : getStatusColor(health?.llm_available ?? false)
                  )}>
                    {getStatusDot(!error && health !== null)}
                    {error ? "Offline" : health?.status || "Checking..."}
                  </span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">LLM Server</span>
                  <span className={cn("text-xs font-medium", getStatusColor(health?.llm_available ?? false))}>
                    {health?.llm_available ? "Connected" : "Disconnected"}
                  </span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Model</span>
                  <span className="text-xs font-medium text-foreground truncate max-w-[140px]" title={health?.llm_model || health?.model}>
                    {health?.llm_model || health?.model || "Unknown"}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">LLM URL</span>
                  <span className="text-xs font-medium text-foreground truncate max-w-[140px]" title={health?.llm_base_url}>
                    {health?.llm_base_url ? health.llm_base_url.replace("http://", "") : "—"}
                  </span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Model Loaded</span>
                  <span className={cn("text-xs font-medium", getStatusColor(health?.model_loaded ?? false))}>
                    {health?.model_loaded ? "Yes" : "No"}
                  </span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Orchestrator</span>
                  <span className={cn("text-xs font-medium", getStatusColor(health?.orchestrator_ready ?? false))}>
                    {health?.orchestrator_ready ? "Ready" : "Not Ready"}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Browser</span>
                  <span className={cn("text-xs font-medium", getStatusColor(health?.browser_ready ?? false))}>
                    {health?.browser_ready ? "Open" : "Idle"}
                  </span>
                </div>
              </div>

              {error && (
                <div className="mt-3 p-2 rounded bg-red-500/10 border border-red-500/20">
                  <p className="text-xs text-red-500">
                    ⚠️ {error}
                  </p>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="border-t border-border" />

            {/* Agent Status */}
            <div>
              <h4 className="text-xs font-medium text-foreground mb-3">Agent Status</h4>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Current Mode</span>
                  <span className="text-xs font-medium text-foreground capitalize">{currentMode}</span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Steps Taken</span>
                  <span className="text-xs font-medium text-foreground">{stepsTaken}</span>
                </div>
                
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-muted-foreground">Last Action</span>
                  <span className="text-xs font-medium text-foreground truncate max-w-[140px]" title={lastAction}>
                    {lastAction}
                  </span>
                </div>
              </div>
            </div>

            {/* Connection Info */}
            {health?.timestamp && (
              <div className="pt-2 border-t border-border">
                <p className="text-[10px] text-muted-foreground">
                  Last updated: {new Date(health.timestamp).toLocaleTimeString()}
                </p>
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
