# Swarm Workbench

[English](README.md)

**一个本地优先的多 Agent 编排工作台：把任务拆解、并行协作、Todo
状态、工具活动与最终汇总完整地呈现出来。**

![Swarm Workbench 演示](docs/assets/swarm-workbench-demo.png)

> [!IMPORTANT]
> 这是一个作品集级参考实现和公开 Beta，不是生产级 Agent 框架。内置
> Demo 是确定性的模拟执行；真实 LLM 路径为可选实验功能。

## 为什么做这个项目

很多多 Agent 项目只展示最终答案，看不出多个 Agent 为什么存在、如何协作、
哪里失败。Swarm Workbench 用统一事件契约把任务拆解、角色分配、受限并发、
Todo 状态、工具调用、流式输出和结果聚合呈现在同一个控制台中。

本项目刻意控制范围：先做到容易运行、容易审查、容易解释；尚未完成的生产
能力会清楚写入限制和路线图，而不是包装成已经可用。

## 当前真正可用的能力

- 无需 API Key、无需联网的四角色可观测 Demo。
- 可选真实 Provider 的 `single`、`swarm`、`auto` 编排路径。
- 有并发上限的任务派发和确定性的 Todo 结果合并。
- FastAPI 任务 API，以及支持 wildcard 和有限 replay 的 SSE。
- Next.js 控制台：Todo、Agent 工牌、对话结果、实时活动。
- 用户自行配置环境变量后，通过 LiteLLM 路由真实模型。
- 文件工具限制在 workspace 内；本机 shell 默认关闭。
- Python 单元/集成测试和前端 lint、类型检查、生产构建。

每一项状态请以 [能力矩阵](docs/STATUS.md) 为准。

## 五分钟启动：无需 API Key

需要 Python 3.12、Node.js 22、[uv](https://docs.astral.sh/uv/) 和
[pnpm](https://pnpm.io/)。

```bash
git clone https://github.com/Richerwang228/swarm-workbench.git
cd swarm-workbench

uv sync --locked
pnpm --dir apps/web install --frozen-lockfile
./start.sh --demo
```

打开 [http://127.0.0.1:3000](http://127.0.0.1:3000)，点击“加载示例”，
再点击“发送”。这个 Demo 不请求模型，也不执行本机工具。

## 架构

```mermaid
flowchart LR
    U["用户 / 浏览器"] --> W["Next.js 控制台"]
    W -->|创建任务| A["FastAPI Task API"]
    A --> O{"运行模式"}
    O -->|demo| D["确定性 Demo Runner"]
    O -->|single / swarm| G["LangGraph 编排器"]
    G --> L["LiteLLM Provider Router"]
    G --> T["显式启用的工具"]
    D --> E["进程内事件总线"]
    G --> E
    E -->|wildcard + replay SSE| W
```

Demo 和真实执行都使用相同的 task、todo、agent、tool、content 事件契约。
完整组件职责和时序见 [架构文档](docs/ARCHITECTURE.md)。

## 使用真实模型

```bash
cp .env.example .env
# 将 SWARM_DEMO_MODE 改为 false，并配置 SWARM_MODEL、
# SWARM_API_BASE 和 SWARM_API_KEY。
./start.sh
```

不要提交 `.env`。真实 Provider 可能产生费用；搜索工具可能联网。启用工具前
请阅读 [安全模型](docs/SECURITY_MODEL.md)。

## 验证

```bash
./scripts/verify.sh
```

它会运行 Python 测试、Ruff、mypy、ESLint、TypeScript 和 Next.js 生产构建。

## 安全边界

- 本机 shell 默认关闭。
- 文件路径会做 canonical resolve，并拒绝 symlink 逃逸。
- Demo 不使用模型、网络或本机工具。
- 仓库只跟踪 `.env.example`，不跟踪真实环境文件。
- CI 持续执行 CodeQL、依赖更新和密钥扫描。

本 Beta 没有生产级沙箱。不要在 `ALLOW_LOCAL_EXECUTION=true` 时运行不可信
任务。详见 [SECURITY.md](SECURITY.md)。

## 已知限制

- Checkpoint 和事件 replay 只存在于当前进程，重启后丢失。
- 真实 Provider 在 CI 中使用 mock 验证，不代表第三方 API 永远稳定。
- 中断、公开分享、浏览器自动化、E2B、MCP、git worktree 自动合并尚未实现。
- Demo 证明的是产品和事件闭环，不证明模型效果优于单 Agent。
- 没有鉴权和多租户隔离，只应绑定 localhost。

后续计划见 [Roadmap](docs/ROADMAP.md)。

## 参与项目

- [贡献指南](CONTRIBUTING.md)
- [问题与支持](SUPPORT.md)
- [安全漏洞报告](SECURITY.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [第三方说明](THIRD_PARTY_NOTICES.md)

## License

Apache-2.0，见 [LICENSE](LICENSE)。
