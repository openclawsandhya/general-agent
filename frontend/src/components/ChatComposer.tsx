import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Mic, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ComposerProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export function ChatComposer({ onSend, isLoading }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [value]);

  const handleSend = () => {
    if (!value.trim() || isLoading) return;
    onSend(value.trim());
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-border bg-card/50 backdrop-blur-sm p-4">
      <div className="max-w-[720px] mx-auto">
        <div className="flex items-end gap-2 rounded-lg border border-border bg-card p-2">
          <button className="p-2 text-muted-foreground hover:text-foreground transition-colors shrink-0">
            <Paperclip className="w-4 h-4" />
          </button>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask SANDHYA.AI anything or give an autonomous goal…"
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none min-h-[36px] py-2 leading-relaxed"
          />

          <button className="p-2 text-muted-foreground hover:text-foreground transition-colors shrink-0">
            <Mic className="w-4 h-4" />
          </button>

          <button
            onClick={handleSend}
            disabled={!value.trim() || isLoading}
            className={cn(
              "p-2 rounded-md transition-all duration-150 shrink-0",
              value.trim() && !isLoading
                ? "bg-primary text-primary-foreground hover:bg-destructive hover:shadow-lg hover:-translate-y-0.5"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
