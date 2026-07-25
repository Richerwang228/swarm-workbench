"use client";

import { useEffect } from "react";
import { useSwarmStore } from "@/lib/store";
import { useSwarmStream } from "@/lib/sse";
import { ChatPanel } from "@/components/ChatPanel";
import { PromptInput } from "@/components/PromptInput";
import { BadgeWall } from "@/components/BadgeWall";
import { TodoList } from "@/components/TodoList";
import { ActivityFeed } from "@/components/ActivityFeed";

function StreamConnector() {
  const taskId = useSwarmStore((s) => s.taskId);
  useSwarmStream(taskId);
  return null;
}

function ElapsedTicker() {
  const tick = useSwarmStore((s) => s.tickAgentElapsed);
  const taskStatus = useSwarmStore((s) => s.taskStatus);
  useEffect(() => {
    if (taskStatus !== "running") return;
    const id = setInterval(() => tick(), 1000);
    return () => clearInterval(id);
  }, [taskStatus, tick]);
  return null;
}

function GlobalStatus() {
  const taskStatus = useSwarmStore((s) => s.taskStatus);
  const agentOrder = useSwarmStore((s) => s.agentOrder);
  const agents = useSwarmStore((s) => s.agents);
  const taskId = useSwarmStore((s) => s.taskId);

  const running = agentOrder.filter((id) => agents[id]?.status === "running").length;
  const done    = agentOrder.filter((id) => agents[id]?.status === "done").length;

  if (!taskId) return null;

  return (
    <div className="flex items-center gap-3 font-mono text-xs text-gh-dim">
      {taskStatus === "running" && (
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-gh-green animate-pulse-dot" />
          <span className="text-gh-green">{running} 运行中</span>
        </span>
      )}
      {done > 0 && (
        <span className="text-gh-dim">{done} 完成</span>
      )}
      {taskStatus === "completed" && (
        <span className="text-gh-green">全部完成</span>
      )}
      {taskStatus === "failed" && (
        <span className="text-gh-red">任务失败</span>
      )}
      <span className="text-gh-dim/40">#{taskId.slice(0, 8)}</span>
    </div>
  );
}

export default function Home() {
  const agentOrder = useSwarmStore((s) => s.agentOrder);
  const todos      = useSwarmStore((s) => s.todos);

  return (
    <>
      <StreamConnector />
      <ElapsedTicker />

      <div className="flex h-screen flex-col overflow-hidden bg-gh-bg">
        {/* ── Header ─────────────────────────────────────────────────── */}
        <header className="flex h-11 shrink-0 items-center justify-between border-b border-gh-border bg-gh-surface px-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-gh-purple" />
              <span className="font-semibold text-gh-text tracking-tight">Swarm</span>
            </div>
            <span className="text-gh-dim text-xs">Agent 集群控制台</span>
            <span className="rounded border border-gh-purple/30 bg-gh-purple/10 px-1.5 py-0.5 font-mono text-[9px] text-gh-purple">
              PUBLIC BETA
            </span>
          </div>
          <GlobalStatus />
        </header>

        {/* ── Main ───────────────────────────────────────────────────── */}
        <div className="flex min-h-0 flex-1">

          {/* Left rail — 任务列表 220px */}
          <aside className="flex w-[220px] shrink-0 flex-col border-r border-gh-border bg-gh-surface overflow-hidden">
            <div className="flex items-center gap-2 border-b border-gh-border px-4 py-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-gh-dim">任务</span>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {todos.length > 0 ? (
                <TodoList />
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-2 py-12 opacity-30 select-none">
                  <span className="font-mono text-2xl text-gh-dim">○</span>
                  <p className="text-[11px] text-gh-dim">暂无任务</p>
                </div>
              )}
            </div>
          </aside>

          {/* Center — Agent 卡片 + 对话 */}
          <main className="flex flex-1 flex-col min-w-0 overflow-hidden">
            {/* Agent 集群区域 */}
            {agentOrder.length > 0 && (
              <div className="shrink-0 border-b border-gh-border bg-gh-bg">
                <div className="flex items-center gap-2 px-5 pt-3 pb-0">
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-gh-dim">Agent 集群</span>
                </div>
                <div className="px-5 py-3">
                  <BadgeWall />
                </div>
              </div>
            )}

            {/* 对话区域 */}
            <div className="flex flex-1 flex-col min-h-0 overflow-hidden">
              <div className="flex items-center gap-2 border-b border-gh-border px-5 py-2.5 bg-gh-surface/50">
                <span className="text-[11px] font-semibold uppercase tracking-widest text-gh-dim">对话</span>
              </div>
              <ChatPanel />
              <PromptInput />
            </div>
          </main>

          {/* Right rail — 实时动态 280px */}
          <aside className="flex w-[280px] shrink-0 flex-col border-l border-gh-border bg-gh-surface overflow-hidden">
            <div className="flex items-center gap-2 border-b border-gh-border px-4 py-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-gh-dim">实时动态</span>
              <span className="ml-auto flex items-center gap-1 font-mono text-[10px] text-gh-green">
                <span className="h-1.5 w-1.5 rounded-full bg-gh-green animate-pulse-dot" />
                live
              </span>
            </div>
            <ActivityFeed />
          </aside>

        </div>
      </div>
    </>
  );
}
