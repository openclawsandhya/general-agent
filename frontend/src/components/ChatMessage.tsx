import { cn } from "@/lib/utils";
import { Copy, Check } from "lucide-react";
import { useState } from "react";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 rounded-md border border-border bg-background overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-accent/50">
        <span className="text-xs text-muted-foreground font-mono">{language || "code"}</span>
        <button onClick={handleCopy} className="text-muted-foreground hover:text-foreground transition-colors">
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono text-foreground leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderMarkdown(content: string) {
  const parts: React.ReactNode[] = [];
  const lines = content.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      const language = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      parts.push(<CodeBlock key={parts.length} code={codeLines.join("\n")} language={language} />);
      continue;
    }

    // Headers
    if (line.startsWith("### ")) {
      parts.push(<h3 key={parts.length} className="text-sm font-semibold text-foreground mt-4 mb-2">{line.slice(4)}</h3>);
    } else if (line.startsWith("## ")) {
      parts.push(<h2 key={parts.length} className="text-base font-semibold text-foreground mt-4 mb-2">{line.slice(3)}</h2>);
    } else if (line.startsWith("# ")) {
      parts.push(<h1 key={parts.length} className="text-lg font-semibold text-foreground mt-4 mb-2">{line.slice(2)}</h1>);
    }
    // Bullet lists
    else if (line.startsWith("- ") || line.startsWith("* ")) {
      parts.push(
        <li key={parts.length} className="ml-4 text-sm text-foreground leading-relaxed list-disc">
          {renderInline(line.slice(2))}
        </li>
      );
    }
    // Numbered lists
    else if (/^\d+\.\s/.test(line)) {
      const text = line.replace(/^\d+\.\s/, "");
      parts.push(
        <li key={parts.length} className="ml-4 text-sm text-foreground leading-relaxed list-decimal">
          {renderInline(text)}
        </li>
      );
    }
    // Empty line
    else if (line.trim() === "") {
      parts.push(<div key={parts.length} className="h-2" />);
    }
    // Normal paragraph
    else {
      parts.push(
        <p key={parts.length} className="text-sm text-foreground leading-relaxed">
          {renderInline(line)}
        </p>
      );
    }

    i++;
  }

  return parts;
}

function renderInline(text: string): React.ReactNode {
  // Handle inline code, bold, links
  const parts: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("`")) {
      parts.push(
        <code key={parts.length} className="px-1.5 py-0.5 rounded bg-accent text-primary text-xs font-mono">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**")) {
      parts.push(<strong key={parts.length} className="font-semibold">{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("[")) {
      const labelMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (labelMatch) {
        parts.push(
          <a key={parts.length} href={labelMatch[2]} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
            {labelMatch[1]}
          </a>
        );
      }
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length === 1 ? parts[0] : parts;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex w-full animate-fade-in", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[720px] rounded-lg px-4 py-3",
          isUser
            ? "bg-accent text-foreground"
            : "text-foreground"
        )}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div>{renderMarkdown(message.content)}</div>
        )}
        <span className="block mt-2 text-xs text-muted-foreground">{message.timestamp}</span>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="flex items-center gap-1.5 px-4 py-3">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}
