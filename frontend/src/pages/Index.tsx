import { useState, useRef, useEffect } from "react";
import { AppSidebar } from "@/components/AppSidebar";
import { AppHeader } from "@/components/AppHeader";
import { ChatMessage, ChatMessageData, TypingIndicator } from "@/components/ChatMessage";
import { ChatComposer } from "@/components/ChatComposer";
import { ModeSwitcher } from "@/components/ModeSwitcher";
import { TelemetryPanel } from "@/components/TelemetryPanel";
import { SettingsModal } from "@/components/SettingsModal";

const initialMessages: ChatMessageData[] = [
  {
    id: "1",
    role: "assistant",
    content: `Welcome to **SANDHYA.AI**. I'm your autonomous AI assistant, ready to help you with complex tasks.

Here's what I can do:

- **Chat Mode** — Natural conversation and Q&A
- **Controlled Mode** — Step-by-step task execution with your approval
- **Autonomous Mode** — Full autonomous goal completion

### Getting Started

You can ask me to perform web research, analyze data, write code, or automate browser tasks. Try something like:

1. "Research the latest trends in AI safety"
2. "Help me debug this Python function"
3. "Autonomously find and summarize the top 5 competitors"

\`\`\`python
# Example: I can generate and explain code
def fibonacci(n: int) -> list[int]:
    if n <= 0:
        return []
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib[:n]
\`\`\`

What would you like to work on today?`,
    timestamp: "Just now",
  },
];

const Index = () => {
  const [messages, setMessages] = useState<ChatMessageData[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [activeNav, setActiveNav] = useState("chat");
  const [mode, setMode] = useState<"chat" | "controlled" | "autonomous">("chat");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [stepsTaken, setStepsTaken] = useState(0);
  const [lastAction, setLastAction] = useState("None");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = (content: string, reply: string, currentMode: string) => {
    // Add user message
    const userMsg: ChatMessageData = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    
    // Add assistant message
    const assistantMsg: ChatMessageData = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: reply,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, assistantMsg]);
    
    // Update telemetry
    setStepsTaken((prev) => prev + 1);
    setLastAction(`Responded in ${currentMode} mode`);
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      <AppSidebar
        activeItem={activeNav}
        onItemClick={setActiveNav}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <div className="flex flex-1 flex-col min-w-0">
        <AppHeader onSettingsClick={() => setSettingsOpen(true)} />

        <div className="flex flex-1 min-h-0 relative">
          {/* Main chat area */}
          <div className="flex flex-1 flex-col min-w-0">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              <div className="max-w-[720px] mx-auto space-y-4">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                {isLoading && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Mode switcher + Composer */}
            <div className="px-6 pb-2 pt-1">
              <div className="max-w-[720px] mx-auto flex justify-center mb-2">
                <ModeSwitcher mode={mode} onChange={setMode} />
              </div>
            </div>
            <ChatComposer 
              onSend={handleSend} 
              setIsLoading={setIsLoading}
              isLoading={isLoading}
              sessionId={sessionId}
            />
          </div>

          {/* Telemetry */}
          <TelemetryPanel 
            currentMode={mode}
            stepsTaken={stepsTaken}
            lastAction={lastAction}
          />
        </div>
      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
};

export default Index;
