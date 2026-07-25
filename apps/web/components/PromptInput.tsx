"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { useSwarmStore, type TaskMode } from "@/lib/store";
import { createTask } from "@/lib/api";

const MODES: { value: TaskMode; label: string; desc: string }[] = [
  { value: "demo",   label: "DEMO",   desc: "无需 API Key 的本地模拟" },
  { value: "auto",   label: "AUTO",   desc: "自动选择" },
  { value: "single", label: "单 Agent", desc: "顺序执行" },
  { value: "swarm",  label: "集群",   desc: "并行执行" },
];

export function PromptInput() {
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const prompt       = useSwarmStore((s) => s.prompt);
  const mode         = useSwarmStore((s) => s.mode);
  const taskStatus   = useSwarmStore((s) => s.taskStatus);
  const taskId       = useSwarmStore((s) => s.taskId);
  const setPrompt    = useSwarmStore((s) => s.setPrompt);
  const setMode      = useSwarmStore((s) => s.setMode);
  const appendUser   = useSwarmStore((s) => s.appendUserMessage);
  const setTaskId    = useSwarmStore((s) => s.setTaskId);
  const setTaskStatus= useSwarmStore((s) => s.setTaskStatus);
  const reset        = useSwarmStore((s) => s.reset);

  const isRunning = taskStatus === "running";
  const canSend   = !!prompt.trim() && !loading && !isRunning;

  function loadDemo() {
    setMode("demo");
    setPrompt("Prepare this project for a portfolio-grade open-source release");
    textareaRef.current?.focus();
  }

  async function submit() {
    if (!canSend) return;
    setLoading(true);
    try {
      const trimmed = prompt.trim();
      appendUser(trimmed);
      setPrompt("");
      const res = await createTask({ prompt: trimmed, mode });
      setTaskId(res.task_id);
      setTaskStatus("running");
    } catch {
      setTaskStatus("failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  }

  return (
    <div className="shrink-0 border-t border-gh-border bg-gh-surface/60 px-4 py-3">
      {/* Mode + abort row */}
      <div className="mb-2 flex items-center gap-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(m.value)}
            disabled={isRunning}
            title={m.desc}
            className={[
              "rounded px-2.5 py-1 text-[11px] font-medium transition-colors",
              "disabled:cursor-not-allowed disabled:opacity-40",
              mode === m.value
                ? "bg-gh-blue/15 text-gh-blue"
                : "text-gh-dim hover:text-gh-text hover:bg-gh-muted/60",
            ].join(" ")}
          >
            {m.label}
          </button>
        ))}

        {!isRunning && !prompt && (
          <button
            onClick={loadDemo}
            className="ml-2 rounded px-2.5 py-1 text-[11px] text-gh-purple transition-colors hover:bg-gh-purple/10"
          >
            加载示例
          </button>
        )}

        {!isRunning && taskId && (
          <button
            onClick={() => reset()}
            className="ml-auto rounded border border-gh-border px-2.5 py-1 text-[11px] font-medium text-gh-dim transition-colors hover:bg-gh-muted hover:text-gh-text"
          >
            清空
          </button>
        )}
      </div>

      {/* Textarea */}
      <div className="flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading || isRunning}
          placeholder={isRunning ? "Agent 集群运行中..." : "描述你的任务... (Enter 发送，Shift+Enter 换行)"}
          rows={2}
          className={[
            "flex-1 resize-none rounded border border-gh-border bg-gh-muted/40",
            "px-3 py-2 font-sans text-[13px] text-gh-text leading-relaxed",
            "placeholder-gh-dim/40 focus:outline-none focus:border-gh-blue/50",
            "transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
          ].join(" ")}
        />
        <button
          onClick={() => void submit()}
          disabled={!canSend}
          className={[
            "shrink-0 rounded border px-4 py-2 text-[12px] font-medium transition-all",
            canSend
              ? "border-gh-blue/40 bg-gh-blue/10 text-gh-blue hover:bg-gh-blue/20 hover:border-gh-blue/60"
              : "border-gh-border text-gh-dim cursor-not-allowed opacity-40",
          ].join(" ")}
        >
          {loading ? "发送中..." : "发送"}
        </button>
      </div>

      {prompt.length > 0 && (
        <p className="mt-1.5 font-mono text-[10px] text-gh-dim/50 text-right">
          {prompt.length} 字符
        </p>
      )}
    </div>
  );
}
