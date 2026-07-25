/**
 * SSE event stream hook — 连接 /api/stream/{taskId}，派发事件到 store。
 */
"use client";

import { useEffect, useRef } from "react";
import { useSwarmStore } from "./store";
import type { BenchmarkReport } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useSwarmStream(taskId: string | null) {
  const esRef = useRef<EventSource | null>(null);
  const store = useSwarmStore();

  useEffect(() => {
    if (!taskId) return;

    const url = `${API_BASE}/api/stream/${taskId}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      store.setTaskStatus("running");
    };

    es.onerror = () => {
      store.setTaskStatus("failed");
      es.close();
    };

    // Generic message handler — dispatches based on event type
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string) as Record<string, unknown>;
        dispatchEvent(data, store);
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);
}

type Store = ReturnType<typeof useSwarmStore.getState>;

function dispatchEvent(data: Record<string, unknown>, store: Store) {
  const type = data.type as string;

  switch (type) {
    case "task.started":
      store.setTaskStatus("running");
      if (data.mode === "benchmark") {
        store.setMode("benchmark");
      }
      break;

    case "task.completed":
      store.setTaskStatus("completed");
      store.flushStreaming();
      break;

    case "task.error":
      store.setTaskStatus("failed");
      break;

    case "task.cancelled":
      store.setTaskStatus("cancelled");
      store.flushStreaming();
      break;

    case "agent.spawned":
      store.spawnAgent({
        agentId: (data.agent_id as string) ?? "",
        role: (data.role as string) ?? "pm",
        task: (data.task as string) ?? "",
        status: "spawned",
        toolCalls: 0,
        tokenCount: 0,
        elapsedMs: 0,
        recovered: false,
        lastAction: "",
        spawnedAt: Date.now(),
      });
      break;

    case "agent.update":
      store.updateAgentStatus(
        data.agent_id as string,
        (data.status as "running" | "done" | "failed") ?? "running",
        data.last_action as string | undefined
      );
      break;

    case "agent.done":
      store.updateAgentStatus((data.agent_id as string) ?? "", "done");
      store.markAgentRecovered(
        (data.agent_id as string) ?? "",
        data.recovered === true,
      );
      store.flushStreaming();
      break;

    case "agent.failed":
      store.updateAgentStatus((data.agent_id as string) ?? "", "failed");
      break;

    case "agent.reasoning.delta":
      store.appendStreamingReasoning(data.content as string ?? "");
      break;

    case "agent.content.delta":
      store.appendStreamingContent(data.content as string ?? "");
      break;

    case "agent.tool.call.start":
      store.setLastToolCall({
        tool: data.tool as string,
        args: data.args,
      });
      store.incrementAgentToolCalls(
        (data.agent_id as string) ?? "",
        data.tool as string,
        data.args,
      );
      break;

    case "agent.tool.result":
      store.setLastToolCall({
        tool: data.tool as string,
        args: null,
        result: data.result as string,
      });
      break;

    case "todo.update": {
      const t = data as Record<string, unknown>;
      store.upsertTodo({
        id: t.id as string,
        description: t.description as string,
        status: t.status as "pending" | "running" | "done" | "failed",
        role: t.role as string ?? "pm",
        dependsOn: (t.depends_on as string[]) ?? [],
      });
      break;
    }

    case "agent.retry.scheduled":
      store.updateAgentStatus(
        (data.agent_id as string) ?? "",
        "running",
        `retry ${String(data.next_attempt ?? "")}`.trim(),
      );
      break;

    case "benchmark.started":
      store.startBenchmark({
        simulated: true,
        agentCount: numberValue(data.agent_count),
        completed: 0,
        active: 0,
        queued: numberValue(data.agent_count),
        recovered: 0,
        peakActive: 0,
        processActive: 0,
        maxConcurrency: numberValue(data.max_concurrency),
        processCapacity: numberValue(data.process_capacity),
        seed: numberValue(data.seed),
      });
      break;

    case "benchmark.progress":
      store.updateBenchmarkProgress({
        completed: numberValue(data.completed),
        active: numberValue(data.active),
        queued: numberValue(data.queued),
        recovered: numberValue(data.recovered),
        peakActive: numberValue(data.peak_active),
        processActive: numberValue(data.process_active),
      });
      break;

    case "benchmark.completed":
      store.setBenchmarkReport(data as unknown as BenchmarkReport);
      break;

    default:
      break;
  }
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
