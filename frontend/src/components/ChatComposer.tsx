import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Mic, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { sendMessage } from "@/lib/api";
import { toast } from "sonner";

interface ComposerProps {
  onSend: (message: string, reply: string, mode: string) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  sessionId?: string;
}

export function ChatComposer({ onSend, isLoading, setIsLoading, sessionId }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [value]);

  const handleSend = async () => {
    if (!value.trim() || isLoading) return;
    
    const message = value.trim();
    setValue("");
    setIsLoading(true);

    try {
      console.log("[ChatComposer] Sending message to backend...");
      const response = await sendMessage(message, sessionId);
      console.log("[ChatComposer] Response received:", response);
      
      onSend(message, response.reply, response.mode);
      
      // Show success toast with mode
      toast.success(`Response received (${response.mode} mode)`);
      
    } catch (error) {
      console.error("[ChatComposer] Error:", error);
      
      // Show error toast
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to send message: ${errorMessage}`);
      
      // Still call onSend with error message so user sees something
      onSend(
        message,
        `❌ Error: ${errorMessage}\n\nPlease ensure:\n1. Backend server is running (http://localhost:8000)\n2. LM Studio is running with Mixtral model loaded\n3. No network issues`,
        "error"
      );
    } finally {
      setIsLoading(false);
    }
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
