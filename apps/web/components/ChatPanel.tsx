"use client";

import { useRef, useEffect, useState } from "react";
import { useSwarmStore, type ChatMessage } from "@/lib/store";

function Timestamp({ ts }: { ts: number }) {
  const d = new Date(ts);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return (
    <span className="font-mono text-[10px] text-gh-dim/60 tabular-nums">
      {hh}:{mm}:{ss}
    </span>
  );
}

function ReasoningBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 font-mono text-[10px] text-gh-dim hover:text-gh-text transition-colors"
      >
        <span className="text-gh-dim/50">{open ? "▼" : "▶"}</span>
        <span>思维链 · {text.length} 字符</span>
      </button>
      {open && (
        <div className="mt-1.5 border-l-2 border-gh-border pl-3 animate-slide-in">
          <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-gh-dim/70 italic">
            {text}
          </pre>
        </div>
      )}
    </div>
  );
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex flex-col items-end gap-1 animate-slide-in">
      <div className="flex items-center gap-2">
        <Timestamp ts={msg.ts} />
        <span className="text-[10px] font-semibold text-gh-blue">你</span>
      </div>
      <div className="max-w-[85%] rounded-lg rounded-tr-sm bg-gh-blue/10 border border-gh-blue/20 px-3 py-2">
        <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-gh-text">
          {msg.content}
        </pre>
      </div>
    </div>
  );
}

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex flex-col items-start gap-1 animate-slide-in">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-gh-purple" />
          <span className="text-[10px] font-semibold text-gh-purple">Swarm</span>
        </div>
        <Timestamp ts={msg.ts} />
      </div>
      <div className="max-w-[90%] rounded-lg rounded-tl-sm border border-gh-border bg-gh-surface px-3 py-2">
        <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-gh-text">
          {msg.content}
        </pre>
        {msg.reasoning && <ReasoningBlock text={msg.reasoning} />}
      </div>
    </div>
  );
}

function StreamingBubble() {
  const content   = useSwarmStore((s) => s.streamingContent);
  const reasoning = useSwarmStore((s) => s.streamingReasoning);
  if (!content && !reasoning) return null;

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-gh-purple animate-pulse-dot" />
        <span className="text-[10px] font-semibold text-gh-purple">Swarm</span>
        <span className="font-mono text-[10px] text-gh-dim">streaming...</span>
      </div>
      {reasoning && (
        <div className="max-w-[90%] border-l-2 border-gh-border/50 pl-3">
          <p className="font-mono text-[10px] italic text-gh-dim">
            {reasoning.slice(-200)}
          </p>
        </div>
      )}
      {content && (
        <div className="max-w-[90%] rounded-lg rounded-tl-sm border border-gh-purple/20 bg-gh-purple/5 px-3 py-2">
          <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-gh-text">
            {content}
          </pre>
          <span className="ml-0.5 inline-block font-mono text-gh-purple animate-blink">▌</span>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 select-none opacity-30">
      <span className="h-2 w-2 rounded-full bg-gh-purple" />
      <p className="text-[12px] text-gh-dim">在下方输入任务，开始运行 Agent 集群</p>
    </div>
  );
}

export function ChatPanel() {
  const messages  = useSwarmStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="flex flex-1 min-h-0 flex-col overflow-y-auto px-5 py-4 gap-5">
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        messages.map((msg) =>
          msg.role === "user"
            ? <UserMessage key={msg.id} msg={msg} />
            : <AssistantMessage key={msg.id} msg={msg} />
        )
      )}
      <StreamingBubble />
      <div ref={bottomRef} />
    </div>
  );
}
