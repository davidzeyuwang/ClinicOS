# Clinic OS — 产品路线图

**最后更新：** 2026-03-27

> **规范 PRD：** `PRD/003-clinic-os-prd-v2.md`（v2.0）—— 所有模块范围、分期与工具迁移策略以该文档为准。
> **表单字段差距分析：** `PRD/004-form-field-gap-analysis.md` —— 真实纸质表单与当前 ClinicOS 实现的逐字段差异分析（更新于 2026-03-26）。

## 愿景

Clinic OS 是一个面向诊所场景的 **垂直 AI Operating System**，目标是用一个事件溯源、HIPAA 对齐、统一的数据与工作流平台，替换当前分散的纸质表单与 SaaS 工具组合（Daily Sign In Sheet、Google Sheets、Notability、Asana）。

长期目标包括：
- 面向诊所运营的 SaaS 平台（统一患者主档 + 就诊 + note + billing）
- 自动化 RCM（Revenue Cycle Management）
- AI 驱动的收费与对账
- AI Agent 驱动的后台自动化（copilot → operator）
- Compliance-as-a-service
- 多诊所 / 多院点平台

## 分阶段路线图（与 PRD v2.0 §14 对齐）

### Phase 1 — 运营核心打通（Operations Core）

| 模块 | 替代对象 | PRD 章节 | 状态 |
|---|---|---|---|
| Event Log System + Compliance Audit Log | 全系统基础设施 | §9, §11.11 | 🔲 未开始 |
| Auth + RBAC | 无（新增能力） | §11.11 | 🔲 未开始 |
| Patient Master File | 纸质 / Notability 中分散的患者记录 | §11.1 | ⚠️ M1 核心进行中 |
| Appointment Management | 仅有 PracticeMate，缺少统一视图 | §11.2 | 🔲 M1 后继续 |
| Front Desk Operations Board（签到 + 房间 / 资源板） | 纸质签到表（⑧）+ Google Sheets（⑨）+ 手工汇总（⑱） | §11.3 | ⚠️ M1 核心进行中 |
| Visit Management | 人工追踪 | §11.5 | ⚠️ M1 核心进行中 |
| **Insurance Policy Fields（P0）** | 个人签字表表头中的 Member ID、Deductible、OOP、Copay、Visits | §11.7 + PRD-004 §2.1 | 🔲 未开始 |
| **Copay Collection + WD Verified per Visit（P0）** | 每次就诊实收共付额（CC）+ WD 核实 | PRD-004 §2.2 | 🔲 未开始 |
| Clinical Note（基础状态） | EHR notes、Notability | §11.6 | 🔲 M1 后继续 |
| **Multi-modality Treatment Record（P1）** | 个人诊疗记录表中的单次多治疗项目 | PRD-004 §2.4 | 🔲 未开始 |
| Document / Signature Archive（基础版） | Notability 手工归档 | §11.4 | ⚠️ M1 PDF / 签字流程进行中 |
| Task Management（基础版） | Asana（②③） | §11.9 | 🔲 M1 后继续 |
| Dashboard（基础版） | 手工汇总（⑱） | §11.10 | ⚠️ M1 日报进行中 |

#### 里程碑 1 — Operations Board（首个交付目标）

范围：
- 患者管理：创建 / 搜索 / 查看前台流程所需的患者记录
- 管理端：房间管理（创建 / 编辑 / 启用状态）、员工管理（创建 / 编辑 / 角色 / 启用状态）
- 用户端：患者签到流程，包括签到时间、服务类型、开始服务时间、结束服务 / checkout 时间、房间状态更新
- Checkout 流程：copay 记录、WD 核实、患者签字确认
- 签字表 PDF：基于结构化就诊历史生成可打印的单患者签字表
- 日报：自动生成每日汇总，并持久化所有事件与 projection 数据

交付物：
- patient、room、staff、check-in/out、服务计时、支付 / 签字确认、房间状态变化等事件契约
- room board、visit history、staff hours 聚合、sign-sheet PDF 源数据、daily summary report 等读模型
- 患者管理、管理端配置、check-in / check-out 与日常运营工作流对应的 API + UI 切片
- M1 黄金路径的后端测试与浏览器 E2E 覆盖
- 日报持久化任务（定时 + 手动重跑）

完成定义：
- 前台无需纸质追踪表即可管理患者、员工和房间
- 前台与治疗师无需纸质表即可完成签到、分房、服务和 checkout
- 可从 ClinicOS 就诊数据生成用于院内签字流程的可打印 sign-sheet PDF
- 诊所经理可实时查看 staff hours、房间占用与当日汇总
- 日终报告可以生成、保存，并且可由 event log 重建

M1 不包含：
- Eligibility 工作流 / Asana 替代
- 超出基础保险字段之外的保险门户操作
- 以 appointment 为主入口的完整工作流
- Claim 提交、EOB 对账、拒付处理与 posting correction
- 超出基础状态支持之外的完整 clinical note 工作流

### Phase 2 — 后台保险与 Claim 流程打通（Insurance + Billing）

| 模块 | 替代对象 | PRD 章节 | 状态 |
|---|---|---|---|
| Insurance / Eligibility | 门户查询（④）、Notability ledger（⑤） | §11.7 + PRD-004 §2.7 | 🔲 未开始 |
| **Eligibility Verification Workflow（替代 Asana）** | Asana insurance inquiry list —— 按年份、按患者管理的 5 问 SOP | PRD-004 §2.7 | 🔲 未开始 |
| **Digital Signature Archive（替代 Notability）** | 签字总表 —— 317+ 患者笔记本 | PRD-004 §2.6 | 🔲 未开始 |
| Claim / Billing State Machine | 手工 claim 录入（⑪⑫） | §11.8 | 🔲 未开始 |
| Denial / AR Queue | 人工比对（⑬–⑰） | §11.8 | 🔲 未开始 |
| Billing Dashboard | 人工对账 | §11.10 | 🔲 未开始 |
| Task Migration（Asana → Clinic OS） | Asana（②③） | §11.9 | 🔲 未开始 |

### Phase 3 — AI 输入与自动化（AI Input + Automation）

| 模块 | 替代对象 | PRD 章节 | 状态 |
|---|---|---|---|
| Voice / Handwriting / Free-text Input | 手工结构化录入 | §11.6 | 🔲 未开始 |
| OCR / Speech-to-Text / LLM Extraction | 人工转录 | §8.2 | 🔲 未开始 |
| AI Note Completeness Check | 仅靠人工复核 | §11.6 | 🔲 未开始 |
| AI Tasking / AI QA | 手工建任务 | §11.9 | 🔲 未开始 |

### Phase 4 — AI Agent 后台协作（AI Agent Back-Office）

| 模块 | 说明 | PRD 章节 | 状态 |
|---|---|---|---|
| AI Agent Standardized Case Processing | 自动处理 eligibility、拒付分类、claim 准备 | §11.9 | 🔲 未开始 |
| Human Review + Exception Handling | 高风险动作的人在回路 | §11.9 | 🔲 未开始 |
| Operation Log / Rollback / Approval Flow | AI 动作的完整审计 | §11.9, §11.11 | 🔲 未开始 |

### Phase 5 — 合规强化与深度集成（Compliance + Integration）

| 模块 | 说明 | PRD 章节 | 状态 |
|---|---|---|---|
| Audit Log Enhancement | 字段级跟踪、保留策略 | §12.1 | 🔲 未开始 |
| Permission Fine-tuning | 更细粒度 RBAC、最小权限执行 | §11.11 | 🔲 未开始 |
| External Integrations | EHR（⑩）、PracticeMate（⑦）、Clearinghouse、Calendar、Payment | §8.2 | 🔲 未开始 |
| Multi-clinic / Multi-location | 多品牌、多院点支持 | §12.2 | 🔲 未开始 |

## 工具迁移策略（PRD v2.0 §7）

| 工具 | MVP 阶段 | 长期状态 | 对应 Clinic OS 模块 |
|---|---|---|---|
| Daily Sign In Sheet | 迁移期可并存 | 停用主流程 | Front Desk Operations Board |
| Google Sheets（room board） | 迁移期对照使用 | 被替代 | Front Desk Operations Board + Resource Model |
| Notability | 可部分保留 | 保留为文档层 | Document / Consent / Clinical Note |
| Asana | 迁移期并存 | 患者任务迁回 Clinic OS | Task / Case Management |

## 关键决策：合规优先

> **第一优先级不是 AI，而是合规架构。**
> 如果没有 HIPAA 对齐的基础设施，产品就无法商业化。

每个模块在上线前都必须通过合规评审。Compliance 角色拥有否决权。

## 核心领域模型（PRD v2.0 §9）

Patient · Appointment · Visit · Room / Resource Allocation · Clinical Note · Document · Consent / Intake Package · Insurance Policy · Eligibility Check · Claim · Task / Case · User · Role / Permission · Audit Log

## 技术决策

| 决策项 | 选择 | ADR |
|---|---|---|
| 核心架构 | Event Sourcing + CQRS | ADR-001 |
| 后端 | Python + FastAPI + PostgreSQL | — |
| 前端 | TBD（React/Next.js，iPad 优先） | — |
| 认证 | JWT + RBAC | — |

## PRD 文档列表

| 文档 | 标题 | 状态 |
|---|---|---|
| PRD-000 | 产品路线图（本文件） | Active |
| PRD-001 | 电子化每日签到总表 | Draft v2 —— 归属 PRD-003 §11.3 |
| PRD-002 | M1 任务拆解 + Prototype 运行步骤 | Ready to execute |
| PRD-003 | Clinic OS PRD v2.0（完整整合版） | **Canonical** |
