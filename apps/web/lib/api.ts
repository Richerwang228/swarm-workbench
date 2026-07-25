/**
 * API client — 封装后端 REST 调用。
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CreateTaskRequest {
  prompt: string;
  mode?: "demo" | "auto" | "single" | "swarm";
  max_subagents?: number;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
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
