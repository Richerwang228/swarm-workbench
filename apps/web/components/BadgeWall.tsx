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
            <span
              className={[
                "h-1.5 w-1.5 rounded-full",
                badge.recovered ? "bg-gh-purple" : "bg-gh-dim",
              ].join(" ")}
            />
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
  const mode = useSwarmStore((s) => s.mode);
  const progress = useSwarmStore((s) => s.benchmarkProgress);
  const report = useSwarmStore((s) => s.benchmarkReport);
  if (agentOrder.length === 0) return null;

  const dense = mode === "benchmark" || agentOrder.length > 24;
  if (dense) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded border border-gh-purple/30 bg-gh-purple/10 px-2 py-1 font-mono text-[9px] font-semibold tracking-widest text-gh-purple">
            SIMULATED BENCHMARK
          </span>
          <span className="font-mono text-[10px] text-gh-dim">
            100 logical agents · no live model calls
          </span>
          {report && (
            <span className="ml-auto font-mono text-[9px] text-gh-dim/60">
              trace {report.semantic_sha256.slice(0, 12)}
            </span>
          )}
        </div>

        <BenchmarkMetrics
          completed={progress?.completed ?? countStatus(agentOrder, agents, "done")}
          total={progress?.agentCount ?? agentOrder.length}
          active={progress?.active ?? countStatus(agentOrder, agents, "running")}
          queued={progress?.queued ?? countStatus(agentOrder, agents, "spawned")}
          recovered={progress?.recovered ?? countRecovered(agentOrder, agents)}
          peak={report?.peak_active ?? progress?.peakActive ?? 0}
        />

        <div
          className="grid grid-cols-10 gap-1.5 rounded border border-gh-border bg-gh-panel/70 p-3"
          aria-label="100 logical agent status matrix"
        >
          {agentOrder.map((id) => {
            const badge = agents[id];
            return badge ? <AgentDot key={id} badge={badge} /> : null;
          })}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[9px] text-gh-dim">
          <LegendDot color="bg-gh-dim/50" label="queued" />
          <LegendDot color="bg-gh-blue" label="running" />
          <LegendDot color="bg-gh-green" label="completed" />
          <LegendDot color="bg-gh-purple" label="recovered" />
          <LegendDot color="bg-gh-red" label="failed" />
          {report && (
            <span className="ml-auto">
              {report.elapsed_ms.toFixed(0)} ms · {report.throughput_agents_s.toFixed(1)} agents/s
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2 xl:grid-cols-4">
      {agentOrder.map((id, i) => {
        const badge = agents[id];
        return badge ? <AgentCard key={id} badge={badge} index={i} /> : null;
      })}
    </div>
  );
}

function AgentDot({ badge }: { badge: AgentBadge }) {
  const color =
    badge.status === "failed"
      ? "bg-gh-red"
      : badge.recovered
        ? "bg-gh-purple"
        : badge.status === "done"
          ? "bg-gh-green"
          : badge.status === "running"
            ? "bg-gh-blue animate-pulse-dot"
            : "bg-gh-dim/40";

  return (
    <span
      className={`aspect-square min-h-2 rounded-[2px] transition-colors duration-300 ${color}`}
      title={`${badge.agentId} · ${badge.role} · ${badge.recovered ? "recovered" : badge.status}`}
      aria-label={`${badge.agentId}: ${badge.recovered ? "recovered" : badge.status}`}
    />
  );
}

function BenchmarkMetrics({
  completed,
  total,
  active,
  queued,
  recovered,
  peak,
}: {
  completed: number;
  total: number;
  active: number;
  queued: number;
  recovered: number;
  peak: number;
}) {
  const metrics = [
    { label: "progress", value: `${completed}/${total}`, color: "text-gh-green" },
    { label: "active", value: active, color: "text-gh-blue" },
    { label: "queued", value: queued, color: "text-gh-dim" },
    { label: "recovered", value: recovered, color: "text-gh-purple" },
    { label: "peak", value: peak, color: "text-gh-text" },
  ];

  return (
    <div className="grid grid-cols-5 gap-2">
      {metrics.map((metric) => (
        <div key={metric.label} className="rounded border border-gh-border bg-gh-panel px-2.5 py-2">
          <div className={`font-mono text-sm font-semibold tabular-nums ${metric.color}`}>
            {metric.value}
          </div>
          <div className="mt-0.5 font-mono text-[8px] uppercase tracking-widest text-gh-dim">
            {metric.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-[1px] ${color}`} />
      {label}
    </span>
  );
}

function countStatus(
  order: string[],
  agents: Record<string, AgentBadge>,
  status: AgentBadge["status"],
) {
  return order.reduce((count, id) => count + Number(agents[id]?.status === status), 0);
}

function countRecovered(order: string[], agents: Record<string, AgentBadge>) {
  return order.reduce((count, id) => count + Number(agents[id]?.recovered), 0);
}
