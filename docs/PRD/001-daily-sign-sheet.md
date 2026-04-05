# PRD-001：电子化每日签到总表

**状态：** 草稿 v2 —— 归属 PRD-003 §11.3（Front Desk Operations Board）
**日期：** 2026-03-02（更新于 2026-03-16）
**上下文：** 完整现状流程请见 `docs/clinic-workflow.md`（18 个步骤）
**父 PRD：** `PRD/003-clinic-os-prd-v2.md` —— 本文档为 PRD v2.0 §11.3 中定义的 **Front Desk Operations Board** 模块提供详细用户故事、验收标准与事件模型。

> **说明：** PRD v2.0 已将本模块的范围从单纯签到表扩大为统一的 **Front Desk Operations Board**。它把 Daily Sign In Sheet、Google Sheets 房间板以及手工汇总整合为一个统一的运营中心，并逐步承载预约状态、支付 / 保险提示、资源分配和下次预约记录等能力。PRD-001 仍然是核心切片的详细规格，聚焦 check-in + room + service tracking + daily report。

## 背景

当前诊所日常运营依赖 **纸质 Daily Sign Sheet**（Step ⑧）+ **Google Sheet 房间状态表**（Step ⑨）+ **手工日终汇总**（Step ⑱）。这是诊所运营的心跳系统，每一次患者就诊都经过这套流程。

根据 PRD v2.0 §7，这些工具将逐步退出主流程：
- **Daily Sign In Sheet** → 迁移期可并存 → 最终停用
- **Google Sheets（room board）** → 迁移期对照使用 → 最终替代

### 当前痛点
- **纸质 PHI 暴露：** 签到表整天放在前台，可见、可拍照、可丢失
- **没有实时可见性：** 治疗师必须走到前台才能知道房间状态
- **Google Sheets 覆盖历史：** 一次房间状态更新会毁掉上一状态，没有审计轨迹，BAA 状态也不明确
- **日报依赖手工：** 日终汇总容易出错，也无法复算
- **无法追溯：** 如果某个数字错了，无法倒推它是怎么来的

### 本模块替代什么

| 当前工具 | 问题 | Clinic OS 替代方案 |
|---|---|---|
| 纸质 Daily Sign Sheet（⑧） | PHI 暴露、无备份、无审计 | 带事件日志的电子签到表 |
| Google Sheet 房间状态（⑨） | 覆盖历史、BAA 不明 | 实时房间板 |
| 手工日终汇总（⑱） | 易错、不可审计 | 自动生成 projection |

## 目标

用一个 **像纸一样快**、支持 **多人实时可见**、并且产生 **不可变审计轨迹** 的数字界面，替代纸质 Daily Sign Sheet + Google Sheet room board + 手工汇总。

根据 PRD v2.0 §11.3，长期目标还包括一个更完整的 **Front Desk Operations Board**，逐步承载：
- 今日预约列表
- 保险 / 资料缺失提醒
- copay / 未完成 intake / 待更新保险提示
- next appointment 快速记录
- 当日统计汇总

Milestone 1 先聚焦 check-in + 房间 + 服务追踪 + 日报，其余能力在 Phase 1 中逐步补齐。

## Milestone 1（首个交付目标）：Room + Staff + Check-In Core

这是 PRD-001 的 **首个可交付切片**，也是后续自动化能力的基础。

### 范围

#### Admin Portal
- 添加房间（name / code / type / active）
- 编辑房间并切换 active 状态
- 添加员工（name / role / license-id 可选 / active）
- 编辑员工并切换 active 状态

#### User Portal（Front Desk + Therapist）
- 患者签到，记录 check-in time
- 选择服务类型
- 开始服务，记录 service start time
- 完成服务，记录 check-out time
- 修改房间状态（available / occupied / cleaning / out-of-service）

#### 实时聚合
- 每位 staff 的实时工作时长（已完成服务总时长）
- 每位 staff 当前进行中 session 的实时计时
- 实时房间占用 / 状态板

#### 报表与持久化
- 在诊所日结时自动生成日报
- 允许手动点击“立即生成”进行对账复跑
- 保存所有事件和日报快照，用于审计和后台引用

### Milestone 1 计划

#### Phase 1 — 事件与数据契约
- 定义以下事件 schema：
  - `ROOM_CREATED`、`ROOM_UPDATED`、`ROOM_STATUS_CHANGED`
  - `STAFF_CREATED`、`STAFF_UPDATED`、`STAFF_STATUS_CHANGED`
  - `PATIENT_CHECKIN`、`SERVICE_STARTED`、`SERVICE_COMPLETED`、`PATIENT_CHECKOUT`
  - `DAILY_REPORT_GENERATED`
- 所有写事件补充 `idempotency key`、`actor metadata` 和 `recorded_at`

#### Phase 2 — 后端 API + Projections
- 管理端 API：rooms / staff 的 CRUD-lite（创建、更新、启用 / 停用）
- 用户端 API：check-in、start / end service、checkout、room status 更新
- Projections：
  - `room_board_current`
  - `staff_hours_daily`
  - `visit_timeline_daily`
  - `daily_report_snapshot`

#### Phase 3 — UI 交付
- 管理端页面：room 列表 / 表单、staff 列表 / 表单
- 用户端页面：patient flow timeline + room board + status actions
- room 与 staff hours 组件通过 WebSocket / SSE 实时同步

#### Phase 4 — 日报引擎
- 在诊所日结 cut-off 自动生成
- 提供带版本化快照的手动重生成接口
- 报告内容包括：
  - 总 check-ins / check-outs
  - 服务次数和总服务分钟数
  - 每位 staff 工时
  - 每个 room 的利用率
  - open / incomplete sessions

#### Phase 5 — 校验与合规门禁
- 管理端与用户端动作的 RBAC 校验
- 审计验证：每个状态变化都映射为不可变事件
- 数据保留测试：日报可以完全由事件历史重建

### Milestone 1 退出标准
- rooms 与 staff 可完全脱离 spreadsheet 管理
- 前台和治疗师可以在系统内完成完整就诊生命周期
- staff 工时聚合近实时更新（projection delay ≤ 5s）
- 日报可生成、可保存、可由 event log 重建

## 本 PRD 当前不包含

- ❌ Patient master file CRUD（PRD v2.0 §11.1，单独规格）
- ❌ Appointment management CRUD（PRD v2.0 §11.2，单独规格）
- ❌ Document / signature archive（PRD v2.0 §11.4，单独规格）
- ❌ 患者 intake 数字化（Step ①，Phase 5+）
- ❌ Eligibility 工作流 / Asana 替代（Steps ②③④，Phase 2）
- ❌ Notability patient ledger 替代（Step ⑤，Phase 2）
- ❌ Claim 生成（Steps ⑪⑫，Phase 2）
- ❌ EOB reconciliation（Steps ⑬–⑰，Phase 2）
- ❌ EHR integration（Step ⑩，Phase 5）
- ❌ Multi-location support（Phase 5）
- ❌ AI 输入 / 抽取（Phase 3）
- ❌ Offline-first（MVP 假设诊所 WiFi 稳定）

## 用户角色

| 角色 | 负责内容 | 访问级别 |
|---|---|---|
| Front Desk | Check-in、付款记录、查看房间状态 | 可读写签到表，可读房间板 |
| Therapist | 开始 / 结束服务、分配房间、查看排程 | 可读写自己的 sessions，可读房间板 |
| Clinic Manager | 查看日报、导出报表 | 全量只读，不直接编辑 |
| Back Office | 在 claim 阶段引用签到数据（Step ⑪） | 只读 |

## 用户故事

### Check-In（替代纸质签到）
- **US-1：** 作为前台，我希望点一下就能给患者签到，这样治疗师能知道患者到了，我也不用在诊所里喊人。
- **US-2：** 作为前台，我希望在一个可滚动列表中看到今天所有患者，并且有颜色状态标记，这样我能一眼看出谁在等候、谁在治疗、谁已完成。

### 服务追踪（替代纸上的时间记录）
- **US-3：** 作为治疗师，我希望把患者带进房间时一键开始计时，这样系统能自动跟踪 session 时长。
- **US-4：** 作为治疗师，我希望在开始服务时选择房间，这样其他员工能实时看到房间占用。
- **US-5：** 作为治疗师，我希望结束服务时确认服务类型（PT、OT、eval 等），这样 billing 数据更准确。
- **US-6：** 作为治疗师，我希望看到当前 session 已经持续了多久，这样我能更好地管理时间。

### Room Board（替代 Google Sheet）
- **US-7：** 作为任何 staff，我希望看到一个实时 room board，显示哪个患者在哪个房间，这样我不用来回走动确认。
- **US-8：** 作为治疗师，我希望通过拖动患者卡片把患者改分配到另一个房间，并且 2 秒内所有人都能看到更新。

### Payment（替代纸质付款栏）
- **US-9：** 作为前台，我希望在 checkout 时记录付款（copay、cash、card、insurance-only、no-charge），这样无需手工汇总就能追踪当天收入。
- **US-10：** 作为前台，我希望看到每位患者的 payment status（paid、pending、insurance-only），这样我知道谁离开前还需要收费。

### Signature（替代纸质签名）
- **US-11：** 作为患者，我希望在 iPad 上签字确认我的 visit，替代纸质签字。

### Daily Summary（替代手工汇总 —— Step ⑱）
- **US-12：** 作为诊所经理，我希望得到自动生成的日报，内容包括：
  - 当日接诊患者总数
  - 当日总收入（按支付方式分组）
  - 每位治疗师的工时和患者数
  - 每个房间的利用率
  - No-shows（签到但未开始服务）
  - Open sessions（已开始但未结束，作为 reconciliation flag）
- **US-13：** 作为诊所经理，我希望可以导出 / 打印日报。
- **US-14：** 作为后台人员，我希望在创建 claims（Step ⑪）时查看 daily sign sheet 数据，以减少手工转录错误。

### Audit（所有合规能力的基础）
- **US-15：** 作为合规负责人，我希望每个动作都以不可变事件记录 actor、timestamp 和 action type，这样能形成完整审计轨迹。
- **US-16：** 作为合规负责人，我希望查询“在日期 Y 谁访问了患者 X 的数据”，用于 incident investigation。

## 验收标准

### Events
- **AC-1：** 患者 check-in 产生 `PATIENT_CHECKIN` 事件：`{patient_id, checked_in_by, timestamp}`
- **AC-2：** 开始服务产生 `SERVICE_STARTED` 事件：`{patient_id, therapist_id, room_id, service_type, timestamp}`
- **AC-3：** 结束服务产生 `SERVICE_COMPLETED` 事件：`{patient_id, therapist_id, service_type, duration_minutes, timestamp}`
- **AC-4：** 房间分配 / 变更产生 `ROOM_ASSIGNED` 事件：`{patient_id, room_id, assigned_by, timestamp}`
- **AC-5：** 付款产生 `PAYMENT_RECORDED` 事件：`{patient_id, amount, method, recorded_by, timestamp}`
- **AC-6：** 签字产生 `SIGNATURE_CAPTURED` 事件：`{patient_id, signature_ref, timestamp}`
- **AC-7：** 任何事件创建后都不能被修改或删除。

### Projections
- **AC-8：** 日报 projection 在任意事件后 5 秒内更新。
- **AC-9：** 房间板 projection 在任意 room event 后 2 秒内反映当前状态。
- **AC-10：** 患者时间线展示指定日期内该患者完整 visit history。

### Security & Compliance
- **AC-11：** 所有 endpoints 都需要 JWT authentication。
- **AC-12：** 强制 RBAC：front desk 不能导出日报；back office 不能编辑。
- **AC-13：** 应用日志、错误信息、URL 中不出现 PHI。
- **AC-14：** 所有数据都在静态（数据库层）和传输中（TLS）加密。
- **AC-15：** Signature images 必须加密存储，只允许授权角色访问。

### UX
- **AC-16：** 从患者列表页到 check-in 动作不超过 2 次点击。
- **AC-17：** 开始服务不超过 3 次点击（选患者 → 选房间 → 点开始）。
- **AC-18：** 所有可交互元素最小触控面积为 44×44px。
- **AC-19：** 所有已连接客户端都能看到实时更新，无需刷新页面。

## 事件模型

| event_type | payload | 触发者 | feeds_projection |
|---|---|---|---|
| `PATIENT_CHECKIN` | patient_id, checked_in_by | Front Desk | daily_sheet, daily_summary |
| `SERVICE_STARTED` | patient_id, therapist_id, room_id, service_type | Therapist | daily_sheet, room_board, daily_summary |
| `SERVICE_COMPLETED` | patient_id, therapist_id, service_type, duration_min | Therapist | daily_sheet, room_board, daily_summary |
| `ROOM_ASSIGNED` | patient_id, room_id, assigned_by | Therapist | room_board |
| `ROOM_RELEASED` | room_id, released_by | Therapist / System | room_board |
| `PAYMENT_RECORDED` | patient_id, amount, method, recorded_by | Front Desk | daily_sheet, daily_summary |
| `SIGNATURE_CAPTURED` | patient_id, signature_storage_ref | System | daily_sheet |
| `NO_SHOW_MARKED` | patient_id, marked_by | Front Desk | daily_sheet, daily_summary |

## 边界情况 / Edge Cases

1. **No-show：** 患者签到但没有开始服务 —— 必须允许显式标记为 no-show
2. **忘记结束服务：** 服务开始后到日终都没结束 —— 系统在日报里标记 open session；经理可通过 `SERVICE_FORCE_COMPLETED` 强制结束（必须带 reason）
3. **多次服务：** 同一患者一天内先 PT 再 OT —— 每个服务都对应独立事件对
4. **拆分付款：** Copay $30 + insurance —— 同一患者允许产生两个 `PAYMENT_RECORDED` 事件
5. **房间冲突：** 两个患者被分配到同一房间 —— 系统给出警告，但允许 override（两次分配都需记录）
6. **角色切换：** 治疗师同时做前台 —— 用户可拥有多个角色，系统按动作逐个检查角色
7. **签字过程中网络中断：** 需支持重试和 deduplication（idempotency key）
8. **补录ย้อนหลัง：** 治疗师第二天才补录前一晚的结束服务 —— 事件同时记录 `actual_time` 和 `recorded_time`
9. **中途换房：** 患者在治疗过程中换房 —— 产生新的 `ROOM_ASSIGNED` + `ROOM_RELEASED` 事件

## PHI / 合规风险

| 风险 | 缓解措施 |
|---|---|
| 候诊区可看到 iPad 患者列表 | 5 分钟自动锁屏，建议加贴防窥膜 |
| Signature images 属于 PHI | 加密存储、按权限访问、绝不写入日志 |
| 含姓名的日报属于 PHI | 仅 manager / back office 可查看完整姓名 |
| 下班后继续访问患者数据 | Session timeout + 全量访问审计 |
| 浏览器缓存留存患者数据 | 正确设置 cache-control headers，不把 PHI 放进 localStorage |
| 对电子签到表截图 | 风险与纸质相同，用访问控制 + 审计来降低风险 |

## 依赖项

- 带静态加密能力的 PostgreSQL 数据库
- 含 JWT auth 的 FastAPI 后端
- 用于实时更新的 WebSocket 或 SSE
- 现代浏览器 iPad（Safari 16+）
- 用于 signature images 的安全存储（带加密的 S3-compatible 或本地加密存储）

## 待确认问题

- [ ] **服务类型：** 完整列表是什么？（PT、OT、Eval、Re-eval、其他？）
- [ ] **房间列表：** 一共有多少个房间？是名字还是编号？
- [ ] **支付方式：** Copay、cash、card、insurance-only、no-charge 之外还有什么？
- [ ] **签字存储：** 使用 S3-compatible 还是本地加密文件系统？
- [ ] **认证模型：** 每位 staff 独立登录，还是共享 iPad + PIN 切换？
- [ ] **PracticeMate 集成：** 是否有 API？还是后台暂时只读引用？
- [ ] **预约列表来源：** 今日患者列表来自手工录入还是 PracticeMate 同步？
- [ ] **Google Workspace BAA：** 是否已经签署？这将影响替代 Google Sheets 的紧迫度。

## Sprint 范围

### Must Have（Sprint 1）
- Event log 表 + 核心事件
- 患者 check-in 流程
- 带 room assignment 的 service start / end
- Room board（实时）
- Payment recording
- Daily summary projection
- JWT auth + 基础 RBAC
- Audit logging

### Nice to Have（Sprint 1）
- Signature capture
- 日报导出 / 打印
- No-show 标记
- Force-close open sessions

### Deferred
- 患者 intake（Step ①）
- Eligibility 工作流（Steps ②③④）
- Patient ledger（Step ⑤）
- Claim generation（Step ⑪）
