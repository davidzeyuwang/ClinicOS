# PRD-002：里程碑 1 任务拆解 + Prototype 操作步骤

**状态：** 可执行
**日期：** 2026-03-05（更新于 2026-03-16）
**依赖：** `PRD/000-product-roadmap.md`、`PRD/001-daily-sign-sheet.md`、`PRD/003-clinic-os-prd-v2.md`

> **背景说明：** 里程碑 1 是 **PRD v2.0 Phase 1（运营核心打通）** 的首个构建目标。它覆盖 **Front Desk Operations Board**（§11.3）中的核心切片：check-in + 房间 + 服务追踪 + 日报。其余 Phase 1 模块（Patient Master §11.1、Appointment §11.2、Document/Signature §11.4、Task Management §11.9）将在后续里程碑中交付。

## 目标

交付 ClinicOS 的第一个可上线里程碑：
- 管理端基础数据配置（rooms + staff）
- 用户端就诊生命周期（check-in → service start/end → checkout）
- 实时员工工时聚合
- 带持久化快照的日报生成

## 工作拆解结构（WBS）

### Track A — 后端核心（Prototype 优先）
1. 定义 room / staff / visit / report 的事件契约
2. 实现事件追加写入 + 内存 projection 更新
3. 增加管理端 API（room / staff 创建 + 更新）
4. 增加用户端 API（check-in、service start/end、checkout、room status）
5. 增加 projection API（room board、staff hours）
6. 增加 report API（generate + fetch）

### Track B — 前端 Prototype UI
1. 管理端页面：room 列表 / 表单、staff 列表 / 表单
2. 用户端页面：check-in 与服务生命周期动作
3. 实时组件：room board 与 staff hours 表格
4. 日报面板：生成 + 查看

### Track C — 质量与合规关卡
1. API 合约测试（happy path + invalid ids）
2. 事件不可变性校验（append-only）
3. Projection 新鲜度校验（完整实现目标 <5s）
4. RBAC 桩实现与角色矩阵校验

## Prototype 操作步骤（Runbook）

## Step 0 — 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开文档：
- `http://127.0.0.1:8000/docs`

Prototype 接口位于：
- `/prototype/*`

## Step 1 — 管理端初始化：创建房间

POST `/prototype/admin/rooms`

请求体示例：
```json
{
  "name": "Room 1",
  "code": "R1",
  "room_type": "treatment",
  "active": true
}
```

对诊所所有房间重复此步骤。

## Step 2 — 管理端初始化：创建员工

POST `/prototype/admin/staff`

请求体示例：
```json
{
  "name": "Alice Therapist",
  "role": "therapist",
  "license_id": "PT-001",
  "active": true
}
```

前台和治疗师均需创建。

## Step 3 — 用户流程：患者签到

POST `/prototype/portal/checkin`

```json
{
  "patient_name": "John Doe",
  "patient_ref": "MRN-1001",
  "actor_id": "frontdesk-1"
}
```

保存返回的 `visit_id`。

## Step 4 — 用户流程：开始服务

POST `/prototype/portal/service/start`

```json
{
  "visit_id": "<visit_id>",
  "staff_id": "<staff_id>",
  "room_id": "<room_id>",
  "service_type": "PT",
  "actor_id": "therapist-1"
}
```

## Step 5 — 验证实时 projection

GET `/prototype/projections/room-board`
GET `/prototype/projections/staff-hours`

预期结果：
- room status 变为 `occupied`
- 被分配员工的 active minutes 开始累计

## Step 6 — 结束服务并 checkout

POST `/prototype/portal/service/end`
```json
{
  "visit_id": "<visit_id>",
  "actor_id": "therapist-1"
}
```

POST `/prototype/portal/checkout`
```json
{
  "visit_id": "<visit_id>",
  "actor_id": "frontdesk-1"
}
```

预期结果：
- room 恢复为 `available`
- staff 聚合中的完成工时递增

## Step 7 — 生成日报

POST `/prototype/reports/daily/generate`
```json
{
  "actor_id": "manager-1"
}
```

然后获取：
- GET `/prototype/reports/daily`

## Step 8 — 审计验证

GET `/prototype/events`

确认所有动作都以 append-only 事件形式存在，并且能够重建 daily summary。

## 里程碑 1 任务板（可直接分配）

| ID | 任务 | 负责人角色 | 预估 |
|---|---|---|---|
| M1-BE-01 | 用 PostgreSQL `event_log` 替换内存 prototype | Backend Engineer | 2d |
| M1-BE-02 | 增加 DB-backed projections（room / staff / report） | Backend Engineer | 2d |
| M1-BE-03 | 给 prototype endpoints 加上 auth + RBAC 守卫 | Backend Engineer + Compliance | 1.5d |
| M1-FE-01 | 构建 room / staff CRUD-lite 管理端 UI | Frontend Designer | 2d |
| M1-FE-02 | 构建 visit lifecycle 用户端流程 | Frontend Designer | 2d |
| M1-FE-03 | 构建实时 dashboard 组件（room board / staff hours） | Frontend Designer | 1.5d |
| M1-QA-01 | API 与流程测试（happy + failure paths） | Tester | 1.5d |
| M1-COMP-01 | PHI / logging / RBAC 合规门禁 | Compliance | 1d |
| M1-REV-01 | 最终设计 / 代码评审 + go/no-go | Reviewer | 0.5d |

## Prototype 完成定义

- 管理端可通过 API 创建并更新 rooms + staff
- 前台 / 治疗师可通过 API 完成完整 visit lifecycle
- staff hours 与 room board projections 能正确反映状态变化
- 日报可生成并读取
- 事件流覆盖所有状态变化动作

## 与 PRD v2.0 Phase 1 的关系

里程碑 1 交付 **operations board core**（PRD v2.0 §11.3）。后续里程碑继续覆盖其余 Phase 1 模块：

| 里程碑 | PRD v2.0 章节 | 范围 |
|---|---|---|
| M1（本次） | §11.3 部分 | Check-in + Room + Service + Daily Report |
| M2 | §11.1, §11.2 | Patient Master + Appointment Management |
| M3 | §11.3 完整, §11.4 | Full Operations Board + Document/Signature |
| M4 | §11.5, §11.6, §11.9, §11.10, §11.11 | Visit + Note + Task + Dashboard + RBAC |
