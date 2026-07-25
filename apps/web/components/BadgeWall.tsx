"use client";

import { useSwarmStore, type AgentBadge } from "@/lib/store";

const ROLE_CONFIG: Record<string, { color: string; border: string; label: string }> = {
  pm:       { color: "text-role-pm",       border: "border-l-role-pm",       label: "PM"       },
  designer: { color: "text-role-designer", border: "border-l-role-designer", label: "Design"   },
  frontend: { color: "text-role-frontend", border: "border-l-role-frontend", label: "Frontend" },
  backend:  { color: "text-role-backend",  border: "border-l-role-backend",  label: "Backend"  },
  tester:   { color: "text-role-tester",   border: "border-l-role-tester",   label: "QA"       },
  ops:      { color: "text-role-ops",      border: "border-l-role-ops",      label: "Ops"      },
};

function fmtElapsed(ms: number) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  if (m > 0) return `${m}m${s % 60}s`;
  return `${s}s`;
}

function AgentCard({ badge, index }: { badge: AgentBadge; index: number }) {
  const cfg = ROLE_CONFIG[badge.role] ?? {
    color: "text-gh-dim",
    border: "border-l-gh-border",
    label: badge.role,
  };

  const isRunning = badge.status === "running";
  const isDone    = badge.status === "done";
  const isFailed  = badge.status === "failed";

  return (
    <div
      className={[
        "flex flex-col gap-1.5 rounded border border-gh-border bg-gh-panel",
        "border-l-2 px-3 py-2.5 animate-card-in",
        cfg.border,
        isDone   ? "opacity-60" : "",
        isFailed ? "border-gh-red/60" : "",
      ].join(" ")}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className={`font-mono text-[10px] font-semibold uppercase tracking-widest ${cfg.color}`}>
          {cfg.label}
        </span>
        <div className="flex items-center gap-1.5">
          {isRunning && (
            <span className="h-1.5 w-1.5 rounded-full bg-gh-green animate-pulse-dot" />
          )}
          {isDone && (
            <span className="h-1.5 w-1.5 rounded-full bg-gh-dim" />
          )}
          {isFailed && (
            <span className="h-1.5 w-1.5 rounded-full bg-gh-red" />
          )}
          <span className="font-mono text-[10px] tabular-nums text-gh-dim">
            {fmtElapsed(badge.elapsedMs)}
          </span>
        </div>
      </div>

      {/* Current action */}
      <p className="font-mono text-[10px] text-gh-text/80 truncate leading-snug">
        {badge.lastAction
          ? badge.lastAction
          : badge.status === "spawned"
          ? "初始化中..."
          : badge.task}
      </p>

      {/* Stats row */}
      <div className="flex items-center gap-3 font-mono text-[10px] text-gh-dim">
        <span>
          <span className={cfg.color}>{badge.toolCalls}</span> calls
        </span>
        {badge.tokenCount > 0 && (
          <span>{(badge.tokenCount / 1000).toFixed(1)}k tok</span>
        )}
        <span className="truncate opacity-50 text-[9px]">
          {badge.agentId.slice(0, 8)}
        </span>
      </div>
    </div>
  );
}

export function BadgeWall() {
  const agentOrder = useSwarmStore((s) => s.agentOrder);
  const agents     = useSwarmStore((s) => s.agents);
  if (agentOrder.length === 0) return null;

  return (
    <div className="grid grid-cols-3 gap-2 xl:grid-cols-4">
      {agentOrder.map((id, i) => {
        const badge = agents[id];
        return badge ? <AgentCard key={id} badge={badge} index={i} /> : null;
      })}
    </div>
  );
}
