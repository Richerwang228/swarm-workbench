/**
 * API client — 封装后端 REST 调用。
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CreateTaskRequest {
  prompt: string;
  mode?: "demo" | "auto" | "single" | "swarm" | "benchmark";
  max_subagents?: number;
  agent_count?: number;
  exact_agent_count?: boolean;
  seed?: number;
  work_ms?: number;
  failure_rate?: number;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
}

export interface BenchmarkReport {
  task_id: string;
  simulated: true;
  agent_count: number;
  completed: number;
  failed: number;
  recovered: number;
  max_concurrency: number;
  process_capacity: number;
  peak_active: number;
  process_peak_active: number;
  elapsed_ms: number;
  throughput_agents_s: number;
  queue_wait_p50_ms: number;
  queue_wait_p95_ms: number;
  duration_p50_ms: number;
  duration_p95_ms: number;
  event_agents: number;
  seed: number;
  work_ms: number;
  failure_rate: number;
  semantic_sha256: string;
}

export async function createTask(req: CreateTaskRequest): Promise<CreateTaskResponse> {
  const res = await fetch(`${API_BASE}/api/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Failed to create task: ${res.statusText}`);
  }
  return res.json() as Promise<CreateTaskResponse>;
}

export async function getBenchmarkReport(taskId: string): Promise<BenchmarkReport> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/benchmark-report`);
  if (!res.ok) {
    throw new Error(`Failed to load benchmark report: ${res.statusText}`);
  }
  return res.json() as Promise<BenchmarkReport>;
}

export async function cancelTask(taskId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to cancel task: ${res.statusText}`);
  }
}
