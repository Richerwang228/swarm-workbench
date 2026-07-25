# Live 100: Evidence and Boundaries

## The precise claim

Swarm Workbench supports a fixed plan of up to 100 live logical worker agents.
The user can set the worker count and the maximum in-flight concurrency
independently, up to 100. Global and per-model limits may reduce the effective
concurrency.

The repository does **not** claim that a named commercial provider will accept
100 simultaneous requests on every account.

## What is automated

`tests/integration/test_live_provider_100.py` starts an actual HTTP server that
implements the OpenAI-compatible chat completion contract. The test then:

1. installs the server as a runtime provider through the same profile and
   LiteLLM Router code used by the application;
2. obtains one exact, server-validated 100-item plan from the planner route;
3. creates 100 unique live worker agents;
4. keeps all 100 streaming completion requests simultaneously in flight;
5. verifies every worker receives a provider response;
6. hierarchically reduces the 100 outputs; and
7. verifies that all capacity slots are released.

This is not the simulated benchmark. Requests cross a TCP connection and the
normal LiteLLM, worker streaming, event, graph, and reducer paths.

`tests/integration/test_live_scale.py` independently verifies one-plan
semantics, unique Agent IDs, role-to-model routing, and a process-wide capacity
cap across the live scheduler. `tests/integration/test_benchmark.py` covers
deterministic scheduling, late event replay, failure recovery, and cross-run
capacity without needing a provider.

## What still requires a user's provider

A real-provider canary cannot be run safely in public CI. It requires a
contributor-owned key, quota, and explicit approval for the likely cost. A
publishable canary report should record only redacted data:

- provider and model aliases, not keys or sensitive Base URLs;
- requested and completed Agents;
- peak in-flight requests;
- 429, timeout, retry, cooldown, and failure counts;
- input/output tokens and provider-reported cost when available;
- wall-clock duration and configuration version.

Until such a canary exists, the correct wording is:

> Contract-tested with 100 concurrent OpenAI-compatible provider requests.
> Real-provider scale depends on account quota, rate limits, latency, and
> budget.

## Why 100 is not the default

One live Agent can make multiple model and tool calls. A 100-Agent task may
therefore create hundreds of billable requests. The default remains four
Agents at concurrency four. High-scale runs require an explicit user choice.

The runtime enforces:

- a process-wide Agent capacity;
- a per-deployment LiteLLM parallel-request limit;
- optional RPM and TPM declarations;
- a maximum number of Agents per task;
- per-Agent step limits;
- task-wide model-call and tool-call limits;
- a task wall-clock deadline;
- bounded per-tool concurrency;
- cancellation propagation from the parent task; and
- process-group termination for a cancelled or timed-out shell command.

Unknown custom models may not have trustworthy price metadata, so a USD hard
cap is not presented as complete. Call, tool, time, and concurrency limits
remain effective regardless of model pricing metadata.

## Multi-provider routing

The Providers panel configures up to 16 providers and 32 models per provider.
Each of nine roles maps to a trusted `provider:model` route:

- planner
- project manager
- designer
- frontend
- backend
- tester
- operations
- reducer
- summarizer

The planner outputs roles, task descriptions, and dependencies. It never
outputs credentials or Base URLs. Server-side configuration resolves roles to
provider routes.

## Secret and endpoint boundary

The current product is a localhost, single-user application:

- inline keys are held in API process memory only;
- read APIs omit keys;
- validation responses omit submitted input;
- the starter binds API and web servers to loopback;
- Host and CORS allowlists are local;
- native provider types use LiteLLM's official endpoint;
- custom remote endpoints require HTTPS; and
- private or loopback endpoints require an explicit local-network opt-in.

Domain addresses are checked when configuration is applied. This is still not
a hardened multi-tenant egress proxy and should not be deployed as a shared
public service.
