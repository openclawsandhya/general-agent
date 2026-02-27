import { useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

const tabs = ["General", "Model", "Browser", "Safety"];

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState("General");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 rounded-lg border border-border bg-card shadow-2xl animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">Settings</h2>
          <button onClick={onClose} className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex min-h-[400px]">
          {/* Tab nav */}
          <div className="w-44 border-r border-border p-3 space-y-0.5">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm rounded-md transition-colors duration-150",
                  activeTab === tab
                    ? "bg-accent text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                )}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 p-6 space-y-6">
            {activeTab === "General" && <GeneralSettings />}
            {activeTab === "Model" && <ModelSettings />}
            {activeTab === "Browser" && <BrowserSettings />}
            {activeTab === "Safety" && <SafetySettings />}
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="text-sm font-medium text-foreground">{label}</div>
        {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
      </div>
      {children}
    </div>
  );
}

function Toggle({ defaultChecked = false }: { defaultChecked?: boolean }) {
  const [on, setOn] = useState(defaultChecked);
  return (
    <button
      onClick={() => setOn(!on)}
      className={cn(
        "relative w-9 h-5 rounded-full transition-colors duration-150",
        on ? "bg-primary" : "bg-muted"
      )}
    >
      <span className={cn(
        "absolute top-0.5 w-4 h-4 rounded-full bg-foreground transition-transform duration-150",
        on ? "translate-x-4" : "translate-x-0.5"
      )} />
    </button>
  );
}

function GeneralSettings() {
  return (
    <div className="space-y-5">
      <SettingRow label="Auto-save conversations" description="Automatically save chat history">
        <Toggle defaultChecked />
      </SettingRow>
      <SettingRow label="Streaming responses" description="Show responses as they generate">
        <Toggle defaultChecked />
      </SettingRow>
      <SettingRow label="Sound notifications">
        <Toggle />
      </SettingRow>
      <SettingRow label="Response language">
        <select className="bg-accent border border-border rounded-md px-2 py-1 text-xs text-foreground outline-none">
          <option>English</option>
          <option>Spanish</option>
          <option>French</option>
        </select>
      </SettingRow>
    </div>
  );
}

function ModelSettings() {
  return (
    <div className="space-y-5">
      <SettingRow label="Model">
        <select className="bg-accent border border-border rounded-md px-2 py-1 text-xs text-foreground outline-none">
          <option>Mistral-7B</option>
          <option>Llama-3-70B</option>
          <option>GPT-4</option>
        </select>
      </SettingRow>
      <SettingRow label="Temperature" description="Controls randomness">
        <div className="flex items-center gap-2">
          <input type="range" min="0" max="100" defaultValue="70" className="w-24 accent-primary" />
          <span className="text-xs text-muted-foreground w-8">0.7</span>
        </div>
      </SettingRow>
      <SettingRow label="Max tokens">
        <input
          type="number"
          defaultValue={4096}
          className="w-20 bg-accent border border-border rounded-md px-2 py-1 text-xs text-foreground outline-none text-right"
        />
      </SettingRow>
      <SettingRow label="Top-P">
        <div className="flex items-center gap-2">
          <input type="range" min="0" max="100" defaultValue="90" className="w-24 accent-primary" />
          <span className="text-xs text-muted-foreground w-8">0.9</span>
        </div>
      </SettingRow>
    </div>
  );
}

function BrowserSettings() {
  return (
    <div className="space-y-5">
      <SettingRow label="Headless mode" description="Run browser without UI">
        <Toggle defaultChecked />
      </SettingRow>
      <SettingRow label="Screenshot capture" description="Capture screenshots during automation">
        <Toggle />
      </SettingRow>
      <SettingRow label="Request timeout (ms)">
        <input
          type="number"
          defaultValue={30000}
          className="w-24 bg-accent border border-border rounded-md px-2 py-1 text-xs text-foreground outline-none text-right"
        />
      </SettingRow>
    </div>
  );
}

function SafetySettings() {
  return (
    <div className="space-y-5">
      <SettingRow label="Content filtering" description="Filter unsafe content">
        <Toggle defaultChecked />
      </SettingRow>
      <SettingRow label="Rate limiting" description="Limit request frequency">
        <Toggle defaultChecked />
      </SettingRow>
      <SettingRow label="Max autonomous steps">
        <input
          type="number"
          defaultValue={25}
          className="w-20 bg-accent border border-border rounded-md px-2 py-1 text-xs text-foreground outline-none text-right"
        />
      </SettingRow>
      <SettingRow label="Require confirmation" description="Ask before destructive actions">
        <Toggle defaultChecked />
      </SettingRow>
    </div>
  );
}
