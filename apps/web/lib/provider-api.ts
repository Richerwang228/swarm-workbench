const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const PROVIDER_KINDS = [
  "openai_compatible",
  "openai",
  "anthropic",
  "gemini",
  "openrouter",
  "ollama",
  "azure",
] as const;

export const ROLE_NAMES = [
  "planner",
  "pm",
  "designer",
  "frontend",
  "backend",
  "tester",
  "ops",
  "reducer",
  "summarizer",
] as const;

export type ProviderKind = (typeof PROVIDER_KINDS)[number];
export type RoleName = (typeof ROLE_NAMES)[number];

export interface ModelProfile {
  id: string;
  model: string;
  max_parallel_requests: number;
  rpm?: number | null;
  tpm?: number | null;
  supports_tools: boolean;
}

export interface ProviderProfile {
  id: string;
  label: string;
  kind: ProviderKind;
  api_base?: string | null;
  api_key_env?: string | null;
  api_version?: string | null;
  allow_private_network: boolean;
  models: ModelProfile[];
  has_api_key?: boolean;
}

export interface ProviderProfileInput extends Omit<ProviderProfile, "has_api_key"> {
  api_key?: string;
}

export interface RuntimeProfiles {
  providers: ProviderProfile[];
  role_models: Record<RoleName, string>;
  default_model: string;
  global_max_parallel_requests: number;
  per_task_max_agents: number;
  request_timeout_seconds: number;
  max_retries: number;
}

export interface RuntimeProfilesInput extends Omit<RuntimeProfiles, "providers"> {
  providers: ProviderProfileInput[];
}

interface ProviderProfilesResponse {
  configured: boolean;
  profiles: RuntimeProfiles | null;
  credential_persistence?: "process-memory-only";
}

export async function getProviderProfiles(): Promise<ProviderProfilesResponse> {
  const response = await fetch(`${API_BASE}/api/providers`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Provider settings could not be loaded (${response.status})`);
  }
  return response.json() as Promise<ProviderProfilesResponse>;
}

export async function putProviderProfiles(
  profiles: RuntimeProfilesInput,
): Promise<ProviderProfilesResponse> {
  const response = await fetch(`${API_BASE}/api/providers`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profiles),
  });
  if (!response.ok) {
    throw new Error(`Provider settings were rejected (${response.status})`);
  }
  return response.json() as Promise<ProviderProfilesResponse>;
}
