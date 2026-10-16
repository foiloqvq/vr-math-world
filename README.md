# VR Math World

> **Taking over this project? Read [`docs/NEXT.md`](docs/NEXT.md) first** — current state, next step, paths, verification commands, and pitfalls are all there.
> An Open-ended Immersive Virtual Space for Mathematical Visualization, Social Interaction and Recreational Exploration

## Project Overview
VR Math World is an open-world immersive virtual environment built for PC and VR platforms. It integrates mathematical visualization, interactive reading space, agent-based AI companions, user-generated content (UGC) system and in-game token economy.

The project aims to construct a gentle virtual habitat for users seeking spiritual relaxation. It combines recreational gameplay and lightweight academic exploration, breaking the boundary between entertainment and mathematical learning. Users are permitted to roam freely, interact with AI agents, explore visualized mathematical structures, upload custom avatar models, and participate in social activities within this persistent virtual world.

## Core Design Objectives
1. **Dual-platform support**: Native runtime for desktop PC and VR headsets, with a unified world scene.
2. **Mathematical visualization module**: A dedicated reading space for formal mathematical notation, symbolic demonstration and interactive geometry exploration.
3. **AI social subsystem**: LLM-powered non-player agents serving as companions, dialogue partners and interactive entities inside the world.
4. **UGC content pipeline**: Decentralized user asset uploading, model preview and permission management for custom avatars and scene props.
5. **Closed-loop in-world token economy**: Non-crypto in-game token system, adopting a “grind-first, pay-to-accelerate” resource acquisition model.

## Development Roadmap
- **Phase 1 — Documentation & Knowledge Base (Current)**:
  Project specification, requirement analysis, mathematical terminology corpus, architecture design, risk assessment.
- **Phase 2 — Prototype Implementation**:
  Core scene framework, basic player movement, math visualization sandbox, prototype AI agent.
- **Phase 3 — Feature Iteration**:
  UGC asset upload system, token economy, multiplayer social module, cross-platform compatibility optimization.
- **Phase 4 — Hardware & Ecosystem Exploration**:
  Custom VR hardware research, ecosystem expansion, community moderation and content grading system.

## 代码结构

| 目录 | 内容 |
| --- | --- |
| `prototype/` | **网页原型**（Three.js）：星空场景 + 第一人称走动 + 三件数学展品 —— 改数学内容最快的试验田 |
| `unity/` | **Unity 侧**（正式引擎）：网格数学、展品组件、场景搭建脚本、Editor 搭建清单 |
| `tools/meshmath-test/` | **引擎外**验证网格数学的测试（`dotnet run`）：顶点/索引/包围盒/单面性不变量 |

网格数学刻意做成不依赖 UnityEngine 的纯 C#，因此**装引擎之前就能编译并测试**。

## Architecture Highlights
The system adopts a modular architecture to separate rendering engine, world logic, AI service, asset management and economic subsystem, which facilitates independent iteration of each component. Content moderation and age-based access control are embedded as a fundamental cross-cutting module.

