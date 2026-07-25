"use client";

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  PROVIDER_KINDS,
  ROLE_NAMES,
  getProviderProfiles,
  putProviderProfiles,
  type ProviderKind,
  type ProviderProfile,
  type RoleName,
  type RuntimeProfiles,
  type RuntimeProfilesInput,
} from "@/lib/provider-api";

interface ModelDraft {
  id: string;
  model: string;
  maxParallelRequests: number;
  supportsTools: boolean;
}

interface ProviderDraft {
  id: string;
  label: string;
  kind: ProviderKind;
  apiBase: string;
  apiKey: string;
  apiKeyEnv: string | null;
  hadInlineKey: boolean;
  allowPrivateNetwork: boolean;
  models: ModelDraft[];
}

interface SettingsDraft {
  providers: ProviderDraft[];
  roleModels: Record<RoleName, string>;
  defaultModel: string;
  globalMaxParallelRequests: number;
  perTaskMaxAgents: number;
}

const EMPTY_ROLES = Object.fromEntries(
  ROLE_NAMES.map((role) => [role, ""]),
) as Record<RoleName, string>;

function newProvider(index = 1): ProviderDraft {
  const id = index === 1 ? "primary" : `provider${index}`;
  return {
    id,
    label: index === 1 ? "Primary provider" : `Provider ${index}`,
    kind: "openai_compatible",
    apiBase: "",
    apiKey: "",
    apiKeyEnv: null,
    hadInlineKey: false,
    allowPrivateNetwork: false,
    models: [
      {
        id: "worker",
        model: "",
        maxParallelRequests: 8,
        supportsTools: true,
      },
    ],
  };
}

const EMPTY_DRAFT: SettingsDraft = {
  providers: [newProvider()],
  roleModels: { ...EMPTY_ROLES },
  defaultModel: "",
  globalMaxParallelRequests: 8,
  perTaskMaxAgents: 8,
};

export function ProviderSettings() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<SettingsDraft>(EMPTY_DRAFT);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;

    void getProviderProfiles()
      .then((response) => {
        if (cancelled) return;
        setConfigured(response.configured);
        setDraft(response.profiles ? draftFromProfiles(response.profiles) : freshDraft());
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Provider settings could not be loaded");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open]);

  function openSettings() {
    setLoading(true);
    setError(null);
    setMessage(null);
    setOpen(true);
  }

  const routes = useMemo(
    () =>
      draft.providers.flatMap((provider) =>
        provider.models
          .filter((model) => provider.id && model.id)
          .map((model) => ({
            value: `${provider.id}:${model.id}`,
            label: `${provider.label || provider.id} / ${model.model || model.id}`,
          })),
      ),
    [draft.providers],
  );

  function close() {
    if (saving) return;
    setOpen(false);
    setDraft(EMPTY_DRAFT);
    setMessage(null);
    setError(null);
  }

  function updateProvider(index: number, patch: Partial<ProviderDraft>) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, providerIndex) =>
        providerIndex === index ? { ...provider, ...patch } : provider,
      ),
    }));
  }

  function updateModel(
    providerIndex: number,
    modelIndex: number,
    patch: Partial<ModelDraft>,
  ) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, currentProviderIndex) =>
        currentProviderIndex === providerIndex
          ? {
              ...provider,
              models: provider.models.map((model, currentModelIndex) =>
                currentModelIndex === modelIndex ? { ...model, ...patch } : model,
              ),
            }
          : provider,
      ),
    }));
  }

  function addProvider() {
    setDraft((current) => ({
      ...current,
      providers: [...current.providers, newProvider(current.providers.length + 1)],
    }));
  }

  function removeProvider(index: number) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.filter((_, providerIndex) => providerIndex !== index),
    }));
  }

  function addModel(providerIndex: number) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, index) =>
        index === providerIndex
          ? {
              ...provider,
              models: [
                ...provider.models,
                {
                  id: `model${provider.models.length + 1}`,
                  model: "",
                  maxParallelRequests: 8,
                  supportsTools: true,
                },
              ],
            }
          : provider,
      ),
    }));
  }

  function removeModel(providerIndex: number, modelIndex: number) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, index) =>
        index === providerIndex
          ? {
              ...provider,
              models: provider.models.filter((_, indexToRemove) => indexToRemove !== modelIndex),
            }
          : provider,
      ),
    }));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const validationError = validateDraft(draft);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    try {
      const response = await putProviderProfiles(toRequest(draft));
      if (!response.profiles) throw new Error("Provider settings response was incomplete");
      setDraft(draftFromProfiles(response.profiles));
      setConfigured(true);
      setMessage("Provider routing is active for this API process.");
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Provider settings could not be saved");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={openSettings}
        className="rounded border border-gh-border bg-gh-muted/40 px-2.5 py-1 font-mono text-[10px] text-gh-dim transition-colors hover:border-gh-blue/40 hover:text-gh-text"
      >
        Providers
        {configured && <span className="ml-1.5 text-gh-green">●</span>}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-5">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="provider-settings-title"
            className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-md border border-gh-border bg-gh-bg shadow-2xl"
          >
            <div className="flex shrink-0 items-start justify-between border-b border-gh-border bg-gh-surface px-5 py-4">
              <div>
                <h2 id="provider-settings-title" className="font-semibold text-gh-text">
                  Live Provider Routing
                </h2>
                <p className="mt-1 text-[11px] text-gh-dim">
                  Configure OpenAI-compatible endpoints and choose a model for every agent role.
                </p>
              </div>
              <button
                type="button"
                onClick={close}
                className="rounded px-2 py-1 text-gh-dim hover:bg-gh-muted hover:text-gh-text"
                aria-label="Close provider settings"
              >
                ×
              </button>
            </div>

            {loading ? (
              <div className="flex min-h-64 items-center justify-center font-mono text-xs text-gh-dim">
                Loading provider configuration…
              </div>
            ) : (
              <form onSubmit={save} className="flex min-h-0 flex-1 flex-col">
                <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
                  <div className="rounded border border-gh-amber/30 bg-gh-amber/5 px-3 py-2.5 text-[11px] leading-relaxed text-gh-dim">
                    <span className="font-semibold text-gh-amber">PROCESS MEMORY ONLY.</span>{" "}
                    API keys are sent once to the local API process. They are never placed in
                    localStorage, returned by GET, or displayed again. Restarting the API clears
                    them. Changing a provider that used an inline key requires re-entering it.
                  </div>

                  {draft.providers.map((provider, providerIndex) => (
                    <ProviderEditor
                      key={providerIndex}
                      provider={provider}
                      providerIndex={providerIndex}
                      canRemove={draft.providers.length > 1}
                      updateProvider={updateProvider}
                      updateModel={updateModel}
                      addModel={addModel}
                      removeModel={removeModel}
                      removeProvider={removeProvider}
                    />
                  ))}

                  <button
                    type="button"
                    onClick={addProvider}
                    className="rounded border border-dashed border-gh-border px-3 py-2 text-[11px] text-gh-blue hover:border-gh-blue/50 hover:bg-gh-blue/5"
                  >
                    + Add provider
                  </button>

                  <section className="rounded border border-gh-border bg-gh-surface/50 p-4">
                    <div className="mb-3">
                      <h3 className="text-xs font-semibold text-gh-text">Runtime limits</h3>
                      <p className="mt-1 text-[10px] text-gh-dim">
                        Agent count and simultaneous model requests are separate limits.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <NumberField
                        label="Global concurrent requests"
                        value={draft.globalMaxParallelRequests}
                        min={1}
                        max={100}
                        onChange={(value) =>
                          setDraft((current) => ({
                            ...current,
                            globalMaxParallelRequests: value,
                          }))
                        }
                      />
                      <NumberField
                        label="Agents per task"
                        value={draft.perTaskMaxAgents}
                        min={1}
                        max={100}
                        onChange={(value) =>
                          setDraft((current) => ({ ...current, perTaskMaxAgents: value }))
                        }
                      />
                    </div>
                  </section>

                  <section className="rounded border border-gh-border bg-gh-surface/50 p-4">
                    <div className="mb-3">
                      <h3 className="text-xs font-semibold text-gh-text">Role routing</h3>
                      <p className="mt-1 text-[10px] text-gh-dim">
                        Each of the nine roles must resolve to one configured model route.
                      </p>
                    </div>
                    <label className="mb-3 block">
                      <FieldLabel>Default model</FieldLabel>
                      <RouteSelect
                        value={draft.defaultModel}
                        routes={routes}
                        onChange={(value) =>
                          setDraft((current) => ({ ...current, defaultModel: value }))
                        }
                      />
                    </label>
                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
                      {ROLE_NAMES.map((role) => (
                        <label key={role} className="block">
                          <FieldLabel>{role}</FieldLabel>
                          <RouteSelect
                            value={draft.roleModels[role]}
                            routes={routes}
                            onChange={(value) =>
                              setDraft((current) => ({
                                ...current,
                                roleModels: { ...current.roleModels, [role]: value },
                              }))
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </section>

                  <div className="rounded border border-gh-border bg-gh-muted/20 px-3 py-2 text-[10px] text-gh-dim">
                    Connection testing is intentionally not enabled here yet. The API test performs
                    a real model request and may incur provider charges.
                  </div>

                  {error && (
                    <div role="alert" className="rounded border border-gh-red/30 bg-gh-red/5 px-3 py-2 text-[11px] text-gh-red">
                      {error}
                    </div>
                  )}
                  {message && (
                    <div className="rounded border border-gh-green/30 bg-gh-green/5 px-3 py-2 text-[11px] text-gh-green">
                      {message}
                    </div>
                  )}
                </div>

                <div className="flex shrink-0 items-center justify-between border-t border-gh-border bg-gh-surface px-5 py-3">
                  <span className="font-mono text-[9px] text-gh-dim">
                    No key persistence · no automatic paid test
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={close}
                      disabled={saving}
                      className="rounded border border-gh-border px-3 py-1.5 text-[11px] text-gh-dim hover:bg-gh-muted disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={saving}
                      className="rounded bg-gh-blue px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-gh-blue/90 disabled:opacity-50"
                    >
                      {saving ? "Applying…" : "Apply to this process"}
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function ProviderEditor({
  provider,
  providerIndex,
  canRemove,
  updateProvider,
  updateModel,
  addModel,
  removeModel,
  removeProvider,
}: {
  provider: ProviderDraft;
  providerIndex: number;
  canRemove: boolean;
  updateProvider: (index: number, patch: Partial<ProviderDraft>) => void;
  updateModel: (providerIndex: number, modelIndex: number, patch: Partial<ModelDraft>) => void;
  addModel: (providerIndex: number) => void;
  removeModel: (providerIndex: number, modelIndex: number) => void;
  removeProvider: (providerIndex: number) => void;
}) {
  return (
    <section className="rounded border border-gh-border bg-gh-surface/50 p-4">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="text-xs font-semibold text-gh-text">Provider {providerIndex + 1}</h3>
          <p className="mt-1 text-[10px] text-gh-dim">
            Use a base URL only; do not append /chat/completions.
          </p>
        </div>
        {canRemove && (
          <button
            type="button"
            onClick={() => removeProvider(providerIndex)}
            className="text-[10px] text-gh-red hover:underline"
          >
            Remove provider
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <TextField
          label="Provider ID"
          value={provider.id}
          placeholder="primary"
          onChange={(value) => updateProvider(providerIndex, { id: value })}
        />
        <TextField
          label="Display name"
          value={provider.label}
          placeholder="Primary provider"
          onChange={(value) => updateProvider(providerIndex, { label: value })}
        />
        <label className="block">
          <FieldLabel>Kind</FieldLabel>
          <select
            value={provider.kind}
            onChange={(event) =>
              updateProvider(providerIndex, { kind: event.target.value as ProviderKind })
            }
            className={inputClassName}
          >
            {PROVIDER_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </label>
        <TextField
          label="Base URL"
          value={provider.apiBase}
          placeholder="https://api.example.com/v1"
          onChange={(value) => updateProvider(providerIndex, { apiBase: value })}
        />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto]">
        <label className="block">
          <FieldLabel>API key · write-only</FieldLabel>
          <input
            type="password"
            value={provider.apiKey}
            autoComplete="new-password"
            spellCheck={false}
            placeholder={
              provider.hadInlineKey
                ? "Re-enter existing key to apply changes"
                : provider.apiKeyEnv
                  ? `Using environment variable ${provider.apiKeyEnv}`
                  : provider.kind === "ollama"
                    ? "Optional for Ollama"
                    : "Required"
            }
            onChange={(event) => updateProvider(providerIndex, { apiKey: event.target.value })}
            className={inputClassName}
          />
        </label>
        <label className="mt-5 flex items-center gap-2 rounded border border-gh-border px-3 text-[10px] text-gh-dim">
          <input
            type="checkbox"
            checked={provider.allowPrivateNetwork}
            onChange={(event) =>
              updateProvider(providerIndex, { allowPrivateNetwork: event.target.checked })
            }
          />
          Allow private / loopback network
        </label>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between">
          <FieldLabel>Models</FieldLabel>
          <button
            type="button"
            onClick={() => addModel(providerIndex)}
            className="text-[10px] text-gh-blue hover:underline"
          >
            + Add model
          </button>
        </div>
        {provider.models.map((model, modelIndex) => (
          <div
            key={modelIndex}
            className="grid grid-cols-[1fr_2fr_120px_auto] gap-2 rounded border border-gh-border/70 bg-gh-bg/50 p-2"
          >
            <TextField
              label="Model ID"
              value={model.id}
              placeholder="worker"
              onChange={(value) => updateModel(providerIndex, modelIndex, { id: value })}
            />
            <TextField
              label="Upstream model"
              value={model.model}
              placeholder="gpt-4o-mini"
              onChange={(value) => updateModel(providerIndex, modelIndex, { model: value })}
            />
            <NumberField
              label="Model concurrency"
              value={model.maxParallelRequests}
              min={1}
              max={100}
              onChange={(value) =>
                updateModel(providerIndex, modelIndex, { maxParallelRequests: value })
              }
            />
            <div className="flex items-end gap-2 pb-1">
              <label className="flex items-center gap-1 text-[9px] text-gh-dim">
                <input
                  type="checkbox"
                  checked={model.supportsTools}
                  onChange={(event) =>
                    updateModel(providerIndex, modelIndex, {
                      supportsTools: event.target.checked,
                    })
                  }
                />
                tools
              </label>
              {provider.models.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeModel(providerIndex, modelIndex)}
                  className="text-gh-red"
                  aria-label={`Remove model ${model.id}`}
                >
                  ×
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

const inputClassName =
  "h-8 w-full rounded border border-gh-border bg-gh-bg px-2 font-mono text-[11px] text-gh-text outline-none placeholder:text-gh-dim/50 focus:border-gh-blue";

function FieldLabel({ children }: { children: ReactNode }) {
  return (
    <span className="mb-1 block text-[9px] font-semibold uppercase tracking-wider text-gh-dim">
      {children}
    </span>
  );
}

function TextField({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <FieldLabel>{label}</FieldLabel>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        spellCheck={false}
        onChange={(event) => onChange(event.target.value)}
        className={inputClassName}
      />
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <FieldLabel>{label}</FieldLabel>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(Number(event.target.value))}
        className={inputClassName}
      />
    </label>
  );
}

function RouteSelect({
  value,
  routes,
  onChange,
}: {
  value: string;
  routes: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={inputClassName}
    >
      <option value="">Select a model…</option>
      {routes.map((route) => (
        <option key={route.value} value={route.value}>
          {route.label}
        </option>
      ))}
    </select>
  );
}

function freshDraft(): SettingsDraft {
  const provider = newProvider();
  const route = `${provider.id}:${provider.models[0].id}`;
  return {
    ...EMPTY_DRAFT,
    providers: [provider],
    roleModels: Object.fromEntries(ROLE_NAMES.map((role) => [role, route])) as Record<
      RoleName,
      string
    >,
    defaultModel: route,
  };
}

function draftFromProfiles(profiles: RuntimeProfiles): SettingsDraft {
  return {
    providers: profiles.providers.map(providerToDraft),
    roleModels: { ...EMPTY_ROLES, ...profiles.role_models },
    defaultModel: profiles.default_model,
    globalMaxParallelRequests: profiles.global_max_parallel_requests,
    perTaskMaxAgents: profiles.per_task_max_agents,
  };
}

function providerToDraft(provider: ProviderProfile): ProviderDraft {
  return {
    id: provider.id,
    label: provider.label,
    kind: provider.kind,
    apiBase: provider.api_base ?? "",
    apiKey: "",
    apiKeyEnv: provider.api_key_env ?? null,
    hadInlineKey: provider.has_api_key === true && !provider.api_key_env,
    allowPrivateNetwork: provider.allow_private_network,
    models: provider.models.map((model) => ({
      id: model.id,
      model: model.model,
      maxParallelRequests: model.max_parallel_requests,
      supportsTools: model.supports_tools,
    })),
  };
}

function toRequest(draft: SettingsDraft): RuntimeProfilesInput {
  return {
    providers: draft.providers.map((provider) => {
      const apiKey = provider.apiKey.trim();
      return {
        id: provider.id.trim(),
        label: provider.label.trim(),
        kind: provider.kind,
        api_base: provider.apiBase.trim() || null,
        api_key: apiKey || undefined,
        api_key_env: apiKey ? null : provider.apiKeyEnv,
        api_version: null,
        allow_private_network: provider.allowPrivateNetwork,
        models: provider.models.map((model) => ({
          id: model.id.trim(),
          model: model.model.trim(),
          max_parallel_requests: model.maxParallelRequests,
          rpm: null,
          tpm: null,
          supports_tools: model.supportsTools,
        })),
      };
    }),
    role_models: draft.roleModels,
    default_model: draft.defaultModel,
    global_max_parallel_requests: draft.globalMaxParallelRequests,
    per_task_max_agents: draft.perTaskMaxAgents,
    request_timeout_seconds: 120,
    max_retries: 2,
  };
}

function validateDraft(draft: SettingsDraft): string | null {
  if (draft.providers.length === 0) return "Add at least one provider.";
  if (
    !Number.isInteger(draft.globalMaxParallelRequests) ||
    draft.globalMaxParallelRequests < 1 ||
    draft.globalMaxParallelRequests > 100
  ) {
    return "Global concurrent requests must be an integer from 1 to 100.";
  }
  if (
    !Number.isInteger(draft.perTaskMaxAgents) ||
    draft.perTaskMaxAgents < 1 ||
    draft.perTaskMaxAgents > 100
  ) {
    return "Agents per task must be an integer from 1 to 100.";
  }

  const providerIds = new Set<string>();
  const availableRoutes = new Set<string>();
  for (const provider of draft.providers) {
    if (!/^[a-z][a-z0-9_-]{0,31}$/.test(provider.id)) {
      return `Provider ID "${provider.id}" must be a lowercase slug.`;
    }
    if (providerIds.has(provider.id)) return `Provider ID "${provider.id}" is duplicated.`;
    providerIds.add(provider.id);
    if (!provider.label.trim()) return `Provider "${provider.id}" needs a display name.`;
    if (provider.models.length === 0) return `Provider "${provider.id}" needs at least one model.`;
    if (
      provider.kind !== "ollama" &&
      !provider.apiKey.trim() &&
      !provider.apiKeyEnv
    ) {
      return `Enter an API key for provider "${provider.id}".`;
    }
    if (provider.hadInlineKey && !provider.apiKey.trim()) {
      return `Re-enter the write-only API key for provider "${provider.id}" before applying changes.`;
    }

    const modelIds = new Set<string>();
    for (const model of provider.models) {
      if (!/^[a-z][a-z0-9_-]{0,31}$/.test(model.id)) {
        return `Model ID "${model.id}" must be a lowercase slug.`;
      }
      if (modelIds.has(model.id)) {
        return `Model ID "${model.id}" is duplicated in provider "${provider.id}".`;
      }
      modelIds.add(model.id);
      if (!model.model.trim()) return `Model "${provider.id}:${model.id}" needs an upstream name.`;
      if (
        !Number.isInteger(model.maxParallelRequests) ||
        model.maxParallelRequests < 1 ||
        model.maxParallelRequests > 100
      ) {
        return `Model concurrency for "${provider.id}:${model.id}" must be 1 to 100.`;
      }
      availableRoutes.add(`${provider.id}:${model.id}`);
    }
  }

  if (!availableRoutes.has(draft.defaultModel)) return "Select a valid default model.";
  for (const role of ROLE_NAMES) {
    if (!availableRoutes.has(draft.roleModels[role])) {
      return `Select a valid model for role "${role}".`;
    }
  }
  return null;
}
