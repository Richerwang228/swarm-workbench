"use client";

import { useEffect } from "react";
import { ActivityFeed } from "@/components/ActivityFeed";
import { BadgeWall } from "@/components/BadgeWall";
import { ChatPanel } from "@/components/ChatPanel";
import { PromptInput } from "@/components/PromptInput";
import { ProviderSettings } from "@/components/ProviderSettings";
import { TodoList } from "@/components/TodoList";
import { useSwarmStream } from "@/lib/sse";
import { useSwarmStore } from "@/lib/store";

function StreamConnector() {
  const taskId = useSwarmStore((state) => state.taskId);
  useSwarmStream(taskId);
  return null;
}

function ElapsedTicker() {
  const tick = useSwarmStore((state) => state.tickAgentElapsed);
  const taskStatus = useSwarmStore((state) => state.taskStatus);
  useEffect(() => {
    if (taskStatus !== "running") return;
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [taskStatus, tick]);
  return null;
}

function Mark() {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-full border border-gh-text bg-gh-text text-[11px] font-semibold tracking-[-0.08em] text-gh-bg">
      S/
    </span>
  );
}

function StatusLine() {
  const status = useSwarmStore((state) => state.taskStatus);
  const agents = useSwarmStore((state) => state.agents);
  const agentOrder = useSwarmStore((state) => state.agentOrder);
  const running = agentOrder.filter((id) => agents[id]?.status === "running").length;
  const complete = agentOrder.filter((id) => agents[id]?.status === "done").length;

  if (status === "idle") {
    return <span className="text-gh-dim">本地优先 · 默认无 API Key</span>;
  }
  if (status === "running") {
    return <span className="text-gh-green">{running} 个 Agent 正在推进任务</span>;
  }
  if (status === "completed") {
    return <span className="text-gh-green">{complete} 个 Agent 已完成</span>;
  }
  return <span className="text-gh-amber">本次运行已结束：{status}</span>;
}

function MissionMap() {
  return (
    <div className="relative min-h-[340px] overflow-hidden rounded-[2rem] border border-gh-border bg-gh-text p-6 text-gh-bg sm:p-8">
      <div className="absolute inset-0 opacity-30" aria-hidden>
        <div className="absolute -left-20 top-24 h-72 w-72 rounded-full bg-gh-amber blur-3xl" />
        <div className="absolute -right-24 -top-16 h-72 w-72 rounded-full bg-role-backend blur-3xl" />
      </div>
      <div className="relative flex items-start justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-gh-bg/55">Execution topology</p>
          <p className="mt-2 font-serif text-2xl leading-none sm:text-3xl">One task, many accountable steps.</p>
        </div>
        <span className="rounded-full border border-gh-bg/25 px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-gh-bg/70">live path</span>
      </div>

      <svg className="absolute inset-x-0 bottom-0 h-[220px] w-full" viewBox="0 0 620 220" fill="none" aria-hidden>
        <path d="M106 36C170 36 154 110 242 110M106 36C195 36 210 184 395 184M242 110C310 110 324 62 438 62M242 110C320 110 332 184 395 184M438 62C493 62 490 118 532 118M395 184C470 184 485 118 532 118" stroke="currentColor" strokeOpacity=".25" strokeWidth="1.2" strokeDasharray="5 5" className="animate-draw-line" />
      </svg>

      <MapNode className="left-[7%] top-[40%]" eyebrow="BRIEF" title="Intent" />
      <MapNode className="left-[34%] top-[66%]" eyebrow="PLAN" title="DAG" />
      <MapNode className="left-[64%] top-[33%]" eyebrow="ROUTES" title="Models" />
      <MapNode className="left-[58%] top-[76%]" eyebrow="WORK" title="Agents" />
      <MapNode className="right-[5%] top-[57%]" eyebrow="REVIEW" title="Result" emphasis />

      <div className="absolute bottom-6 left-6 right-6 flex items-center justify-between border-t border-gh-bg/20 pt-4 font-mono text-[10px] text-gh-bg/70">
        <span>observable · bounded · replayable</span>
        <span>1 → 100 agents</span>
      </div>
    </div>
  );
}

function MapNode({
  className,
  eyebrow,
  title,
  emphasis = false,
}: {
  className: string;
  eyebrow: string;
  title: string;
  emphasis?: boolean;
}) {
  return (
    <div className={`absolute z-10 rounded-xl border px-3 py-2.5 shadow-2xl ${className} ${emphasis ? "border-gh-amber bg-gh-amber text-gh-text" : "border-gh-bg/20 bg-gh-bg/10 text-gh-bg backdrop-blur-sm"}`}>
      <p className="font-mono text-[8px] tracking-[0.18em] opacity-60">{eyebrow}</p>
      <p className="mt-1 text-xs font-semibold">{title}</p>
    </div>
  );
}

function CapabilityStrip() {
  const items = [
    ["100", "并发协议路径已验证"],
    ["9", "可分配的角色模型"],
    ["0", "默认网络与密钥依赖"],
  ];
  return (
    <div className="grid grid-cols-3 divide-x divide-gh-border border-y border-gh-border">
      {items.map(([value, label]) => (
        <div key={value} className="px-3 py-4 sm:px-5">
          <p className="font-serif text-3xl leading-none text-gh-text sm:text-4xl">{value}</p>
          <p className="mt-1.5 text-[10px] leading-relaxed text-gh-dim sm:text-xs">{label}</p>
        </div>
      ))}
    </div>
  );
}

function EmptyBrief() {
  return (
    <section className="grid items-stretch gap-8 lg:grid-cols-[minmax(0,0.88fr)_minmax(420px,1.12fr)] lg:gap-12">
      <div className="flex flex-col justify-between py-3 sm:py-8">
        <div className="animate-rise">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-gh-amber">Swarm Workbench / Public beta</p>
          <h1 className="mt-5 max-w-2xl font-serif text-[clamp(3rem,7vw,6.5rem)] leading-[0.88] tracking-[-0.055em] text-gh-text">
            Make the work
            <span className="block italic text-gh-amber">visible.</span>
          </h1>
          <p className="mt-7 max-w-xl text-base leading-7 text-gh-dim sm:text-lg">
            把一个复杂任务拆成可观察、可控、可复盘的协作过程。不是堆叠 Agent，而是让每一次模型选择、工具调用和最终结论都能解释。
          </p>
        </div>
        <div className="mt-10 animate-rise" style={{ animationDelay: "100ms" }}>
          <CapabilityStrip />
          <p className="mt-4 text-xs leading-5 text-gh-dim">
            100 的含义是：运行时已通过 100 条同时在途的 OpenAI-compatible 流式请求契约测试；商业 Provider 的额度和费用仍由你的账户决定。
          </p>
        </div>
      </div>
      <div className="animate-rise" style={{ animationDelay: "150ms" }}><MissionMap /></div>
    </section>
  );
}

function ActiveWorkspace() {
  const todos = useSwarmStore((state) => state.todos);
  const agentOrder = useSwarmStore((state) => state.agentOrder);
  const taskStatus = useSwarmStore((state) => state.taskStatus);

  return (
    <section className="mt-12 grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="overflow-hidden rounded-[1.5rem] border border-gh-border bg-gh-surface shadow-[0_18px_40px_rgba(30,41,37,0.07)]">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-gh-border px-5 py-5 sm:px-7">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-gh-amber">Current execution</p>
            <h2 className="mt-2 font-serif text-3xl tracking-[-0.03em] text-gh-text">过程，而不是黑箱。</h2>
          </div>
          <span className="rounded-full border border-gh-border bg-gh-bg px-3 py-1.5 font-mono text-[9px] uppercase tracking-widest text-gh-dim">{taskStatus}</span>
        </div>
        <div className="space-y-6 p-5 sm:p-7">
          {agentOrder.length > 0 && <BadgeWall />}
          <div className="min-h-[250px] rounded-2xl bg-gh-bg/60 px-1 py-2"><ChatPanel /></div>
        </div>
      </div>
      <aside className="overflow-hidden rounded-[1.5rem] border border-gh-border bg-gh-surface">
        <div className="border-b border-gh-border px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-gh-amber">Trace</p>
          <h2 className="mt-2 font-serif text-2xl text-gh-text">任务脉络</h2>
        </div>
        <div className="max-h-[300px] overflow-y-auto py-3">{todos.length ? <TodoList /> : <p className="px-5 py-8 text-sm text-gh-dim">正在生成计划…</p>}</div>
        <div className="border-t border-gh-border px-5 py-4"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-gh-dim">Activity</p></div>
        <div className="h-[220px]"><ActivityFeed /></div>
      </aside>
    </section>
  );
}

export default function Home() {
  const taskId = useSwarmStore((state) => state.taskId);
  const agentOrder = useSwarmStore((state) => state.agentOrder);
  const isActive = taskId !== null || agentOrder.length > 0;

  return (
    <>
      <StreamConnector />
      <ElapsedTicker />
      <div className="paper-grain min-h-screen bg-gh-bg text-gh-text">
        <header className="hairline sticky top-0 z-30 border-b border-gh-border/70 bg-gh-bg/85 px-5 py-4 backdrop-blur-xl sm:px-8">
          <div className="mx-auto flex max-w-[1480px] items-center justify-between gap-5">
            <div className="flex items-center gap-3">
              <Mark />
              <div>
                <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-gh-dim">Swarm Workbench</p>
                <p className="mt-0.5 font-serif text-lg leading-none tracking-[-0.025em]">Observable agent work</p>
              </div>
            </div>
            <div className="hidden items-center gap-5 font-mono text-[10px] sm:flex"><StatusLine /><span className="h-3 w-px bg-gh-border" /><a className="text-gh-dim transition-colors hover:text-gh-text" href="https://github.com/Richerwang228/swarm-workbench" target="_blank" rel="noreferrer">GitHub ↗</a><ProviderSettings /></div>
            <div className="sm:hidden"><ProviderSettings /></div>
          </div>
        </header>

        <main className="mx-auto max-w-[1480px] px-5 py-10 sm:px-8 sm:py-14">
          {!isActive && <EmptyBrief />}
          <section className={`${isActive ? "" : "mt-14"} rounded-[1.5rem] border border-gh-border bg-gh-surface p-4 shadow-[0_18px_40px_rgba(30,41,37,0.06)] sm:p-6`}>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gh-border pb-4">
              <div><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-gh-amber">New task</p><p className="mt-1 text-sm text-gh-dim">从一个问题开始，选择协作方式，观察整个过程。</p></div>
              <span className="rounded-full bg-gh-muted px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-gh-dim">local-first</span>
            </div>
            <PromptInput />
          </section>
          {isActive && <ActiveWorkspace />}
        </main>
        <footer className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-3 border-t border-gh-border/70 px-5 py-6 font-mono text-[9px] uppercase tracking-[0.18em] text-gh-dim sm:px-8"><span>Built for legible AI collaboration</span><span>Local process · explicit boundaries · public beta</span></footer>
      </div>
    </>
  );
}
