"use client";

import { useSwarmStore, type ToolCallEntry } from "@/lib/store";
import { useRef, useEffect } from "react";

const ROLE_COLOR: Record<string, string> = {
  pm:       "text-role-pm",
  designer: "text-role-designer",
  frontend: "text-role-frontend",
  backend:  "text-role-backend",
  tester:   "text-role-tester",
  ops:      "text-role-ops",
};

const TOOL_ICON: Record<string, string> = {
  web_search:  "⌕",
  read_file:   "↗",
  write_file:  "↙",
  bash:        "$",
  todo:        "○",
  str_replace: "~",
};

function FeedItem({ entry }: { entry: ToolCallEntry }) {
  const roleColor = ROLE_COLOR[entry.role] ?? "text-gh-dim";
  const icon = TOOL_ICON[entry.tool] ?? "·";
  const d = new Date(entry.ts);
  const time = `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}:${String(d.getSeconds()).padStart(2,"0")}`;

  return (
    <div className="flex gap-2 py-2 px-4 border-b border-gh-border/50 last:border-0 animate-feed-in">
      {/* Role label */}
      <span className={`shrink-0 font-mono text-[10px] font-semibold w-14 truncate ${roleColor}`}>
        {entry.role.toUpperCase()}
      </span>

      {/* Tool + args */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] text-gh-dim">{icon}</span>
          <span className="font-mono text-[11px] text-gh-text font-medium">{entry.tool}</span>
        </div>
        {entry.args && entry.args !== "{}" && (
          <p className="mt-0.5 font-mono text-[10px] text-gh-dim truncate">
            {entry.args}
          </p>
        )}
      </div>

      {/* Timestamp */}
      <span className="shrink-0 font-mono text-[9px] text-gh-dim/50 self-start pt-px tabular-nums">
        {time}
      </span>
    </div>
  );
}

export function ActivityFeed() {
  const log  = useSwarmStore((s) => s.toolCallLog);
  const ref  = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = 0;
  }, [log.length]);

  if (log.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-2 opacity-25 select-none">
        <span className="font-mono text-3xl text-gh-dim">·</span>
        <p className="text-[11px] text-gh-dim">等待 Agent 工具调用</p>
      </div>
    );
  }

  return (
    <div ref={ref} className="flex-1 overflow-y-auto">
      {log.map((entry) => (
        <FeedItem key={entry.id} entry={entry} />
      ))}
    </div>
  );
}
