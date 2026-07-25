/**
 * Zustand store — 全局 swarm 状态
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

// ── Types ──────────────────────────────────────────────────────────────────

export type TodoStatus = "pending" | "running" | "done" | "failed";
export type AgentStatus = "spawned" | "running" | "done" | "failed";
export type TaskMode = "demo" | "auto" | "single" | "swarm";

export interface TodoItem {
  id: string;
  description: string;
  status: TodoStatus;
  role: string;
  dependsOn: string[];
}

export interface AgentBadge {
  agentId: string;
  role: string;
  task: string;
  status: AgentStatus;
  toolCalls: number;
  tokenCount: number;
  lastAction: string;
  spawnedAt: number;
  elapsedMs: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  reasoning?: string;
  ts: number;
}

export interface ToolCallEntry {
  id: string;
  agentId: string;
  role: string;
  tool: string;
  args: string;
  ts: number;
}

export interface SwarmState {
  // Task
  taskId: string | null;
  taskStatus: "idle" | "running" | "completed" | "failed";
  mode: TaskMode;
  prompt: string;

  // Chat
  messages: ChatMessage[];
  streamingReasoning: string;
  streamingContent: string;

  // Todo list
  todos: TodoItem[];

  // Agent swarm
  agents: Record<string, AgentBadge>;
  agentOrder: string[];

  // Tool call log for activity feed (capped at 50)
  toolCallLog: ToolCallEntry[];

  // Last tool call for terminal tab
  lastToolCall: { tool: string; args: unknown; result?: string } | null;

  // Actions
  setPrompt: (prompt: string) => void;
  setMode: (mode: TaskMode) => void;
  setTaskId: (id: string | null) => void;
  setTaskStatus: (status: SwarmState["taskStatus"]) => void;

  appendUserMessage: (content: string) => void;
  appendStreamingContent: (delta: string) => void;
  appendStreamingReasoning: (delta: string) => void;
  flushStreaming: () => void;

  upsertTodo: (todo: TodoItem) => void;
  updateTodoStatus: (id: string, status: TodoStatus) => void;

  spawnAgent: (badge: AgentBadge) => void;
  updateAgentStatus: (agentId: string, status: AgentStatus, lastAction?: string) => void;
  incrementAgentToolCalls: (agentId: string, tool: string, args: unknown) => void;
  updateAgentTokens: (agentId: string, delta: number) => void;
  tickAgentElapsed: () => void;

  setLastToolCall: (tc: SwarmState["lastToolCall"]) => void;
  reset: () => void;
}

// ── Initial state ──────────────────────────────────────────────────────────

const initialState = {
  taskId: null as string | null,
  taskStatus: "idle" as SwarmState["taskStatus"],
  mode: "demo" as TaskMode,
  prompt: "",
  messages: [] as ChatMessage[],
  streamingReasoning: "",
  streamingContent: "",
  todos: [] as TodoItem[],
  agents: {} as Record<string, AgentBadge>,
  agentOrder: [] as string[],
  toolCallLog: [] as ToolCallEntry[],
  lastToolCall: null as SwarmState["lastToolCall"],
};

// ── Store ──────────────────────────────────────────────────────────────────

export const useSwarmStore = create<SwarmState>()(
  immer((set) => ({
    ...initialState,

    setPrompt: (prompt) => set((s) => { s.prompt = prompt; }),
    setMode: (mode) => set((s) => { s.mode = mode; }),
    setTaskId: (id) => set((s) => { s.taskId = id; }),
    setTaskStatus: (status) => set((s) => { s.taskStatus = status; }),

    appendUserMessage: (content) =>
      set((s) => {
        s.messages.push({
          id: crypto.randomUUID(),
          role: "user",
          content,
          ts: Date.now(),
        });
      }),

    appendStreamingContent: (delta) =>
      set((s) => { s.streamingContent += delta; }),

    appendStreamingReasoning: (delta) =>
      set((s) => { s.streamingReasoning += delta; }),

    flushStreaming: () =>
      set((s) => {
        if (s.streamingContent) {
          s.messages.push({
            id: crypto.randomUUID(),
            role: "assistant",
            content: s.streamingContent,
            reasoning: s.streamingReasoning || undefined,
            ts: Date.now(),
          });
          s.streamingContent = "";
          s.streamingReasoning = "";
        }
      }),

    upsertTodo: (todo) =>
      set((s) => {
        const idx = s.todos.findIndex((t) => t.id === todo.id);
        if (idx >= 0) {
          s.todos[idx] = todo;
        } else {
          s.todos.push(todo);
        }
      }),

    updateTodoStatus: (id, status) =>
      set((s) => {
        const todo = s.todos.find((t) => t.id === id);
        if (todo) todo.status = status;
      }),

    spawnAgent: (badge) =>
      set((s) => {
        s.agents[badge.agentId] = { ...badge, tokenCount: 0, elapsedMs: 0 };
        if (!s.agentOrder.includes(badge.agentId)) {
          s.agentOrder.push(badge.agentId);
        }
      }),

    updateAgentStatus: (agentId, status, lastAction) =>
      set((s) => {
        if (s.agents[agentId]) {
          s.agents[agentId].status = status;
          if (lastAction !== undefined) {
            s.agents[agentId].lastAction = lastAction;
          }
        }
      }),

    incrementAgentToolCalls: (agentId, tool, args) =>
      set((s) => {
        if (s.agents[agentId]) {
          s.agents[agentId].toolCalls += 1;
          s.agents[agentId].lastAction = tool;
        }
        const entry: ToolCallEntry = {
          id: crypto.randomUUID(),
          agentId,
          role: s.agents[agentId]?.role ?? "pm",
          tool,
          args: typeof args === "string" ? args : JSON.stringify(args).slice(0, 80),
          ts: Date.now(),
        };
        s.toolCallLog.unshift(entry);
        if (s.toolCallLog.length > 50) {
          s.toolCallLog.splice(50);
        }
      }),

    updateAgentTokens: (agentId, delta) =>
      set((s) => {
        if (s.agents[agentId]) {
          s.agents[agentId].tokenCount += delta;
        }
      }),

    tickAgentElapsed: () =>
      set((s) => {
        for (const id of s.agentOrder) {
          if (s.agents[id]?.status === "running") {
            s.agents[id].elapsedMs += 1000;
          }
        }
      }),

    setLastToolCall: (tc) => set((s) => { s.lastToolCall = tc; }),

    reset: () => set(() => ({ ...initialState })),
  }))
);
