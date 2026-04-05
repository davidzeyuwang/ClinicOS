# PRD-005：单次就诊支持多个治疗项目 + 工作流增强

**状态：** 已批准 v1
**日期：** 2026-03-27
**Owner：** 产品
**相关文档：** PRD-001（Daily Sign Sheet）、PRD-004（表单差距分析）

---

## 1. 问题描述

**当前限制：** 每次 visit 只记录一个 `service_type`（例如 `"PT"`）。但真实诊所场景里，一次就诊往往会包含多个并行治疗项目：
- Physical Therapy（30 分钟）+ E-stim（15 分钟）+ Massage（20 分钟）
- 同一个患者可能由多个治疗师参与
- 每个治疗项目都有不同的时长、开始时间和结束时间

**业务影响：**
- 无法按一次 visit 中的多个 CPT code 进行准确 billing
- 无法按治疗项目粒度统计治疗师产能
- 签字表缺少足够细的治疗明细
- 无法生成满足合规要求的明细化患者记录

---

## 2. 用户故事

### US-1：在一次就诊中添加多个治疗项目
**作为** 前台人员
**我希望** 在进行中的 visit 中添加多个治疗 modality
**从而** 记录患者在同一次 session 中接受的全部治疗

**验收标准：**
- Active visit 卡片显示 `+ Add Treatment` 按钮
- 可以添加多个不同 modality 的 treatment
- 每个 treatment 都包含：modality、therapist、duration（可编辑）
- 所有 treatments 以列表形式显示在 visit 卡片下方

### US-2：在 checkout 前复核所有治疗项目
**作为** 前台人员
**我希望** 在 checkout 前看到本次 visit 中完成的全部治疗
**从而** 核对 copay 并生成准确的签字表

**验收标准：**
- Checkout modal 显示只读的 treatment summary table
- 列为：Modality、Therapist、Duration（分钟）、Time
- 提供“为患者签字生成 PDF”选项（checkbox）
- PDF 在 visit history table 中显示所有 treatments

### US-3：按选择的 visits 生成 PDF
**作为** billing staff
**我希望** 只选择特定 visits 进入 sign-sheet PDF
**从而** 生成部分记录（例如只生成本月 visits）

**验收标准：**
- Patient detail modal 中每个 visit 旁都有 checkbox
- `Download Selected Visits PDF` 按钮（仅在选中 ≥1 个 visit 时可用）
- 生成的 PDF 只包含被勾选的 visits

### US-4：治疗记录报表
**作为** 诊所经理
**我希望** 查看跨患者的全部治疗记录并支持筛选
**从而** 分析治疗师产能和 modality 分布

**验收标准：**
- 新增 `Treatment Records` 页面 / 标签页
- 支持筛选：Date range、Patient、Staff（therapist）、Modality
- 表格列为：Patient | Visit Date | Modality | Therapist | Duration | Room
- 支持导出 CSV

---

## 3. 技术需求

### 3.1 数据库 Schema

**新增表：** `visit_treatments`

```sql
CREATE TABLE visit_treatments (
    treatment_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL REFERENCES visits(visit_id),
    modality TEXT NOT NULL,  -- PT, OT, E-stim, Massage, Cupping, etc.
    therapist_id TEXT REFERENCES staff(staff_id),
    duration_minutes INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_visit_treatments_visit ON visit_treatments(visit_id);
CREATE INDEX idx_visit_treatments_therapist ON visit_treatments(therapist_id);
```

**迁移策略：**
- 保留 `visits.service_type` 以兼容旧逻辑（标记为 `Legacy`）
- 新 visits 若使用多个 treatments，则 `service_type` 置空或设为 `"Multiple"`

### 3.2 API Endpoints

| Method | Endpoint | 用途 |
|--------|----------|---------|
| GET | `/prototype/visits/{visit_id}/treatments` | 查询该 visit 的 treatments |
| POST | `/prototype/visits/{visit_id}/treatments/add` | 添加新 treatment |
| PATCH | `/prototype/visits/{visit_id}/treatments/{treatment_id}/update` | 编辑 duration / notes |
| DELETE | `/prototype/visits/{visit_id}/treatments/{treatment_id}/delete` | 删除 treatment |
| GET | `/prototype/treatment-records` | 按筛选条件查询全部 treatments |
| GET | `/prototype/patients/{patient_id}/sign-sheet.pdf?visit_ids=x,y,z` | 为选中的 visits 生成 PDF |

### 3.3 Event Sourcing

**新增事件类型：**
- `TREATMENT_ADDED` —— 在 visit 中创建 treatment
- `TREATMENT_UPDATED` —— 更新 duration / notes
- `TREATMENT_DELETED` —— 删除 treatment（软删除）

所有事件都按 ADR-001 写入 `event_log`。

---

## 4. UI 设计

### 4.1 Active Visits Card（增强版）

```text
┌─────────────────────────────────────────┐
│ John Doe | R201 | Checked In            │
│ Service: Multiple Treatments            │
│                                         │
│ Treatments:                             │
│  • PT (Dr. Chen) - 30min                │
│  • E-stim (Dr. Chen) - 15min [Edit]     │
│  • Massage (Lisa Wu) - 20min [Edit]     │
│                                         │
│ [+ Add Treatment] [Start] [Checkout]    │
└─────────────────────────────────────────┘
```

### 4.2 Add Treatment Modal

```text
┌─────────────────────────────────────────┐
│         Add Treatment                   │
├─────────────────────────────────────────┤
│ Modality:  [Dropdown: PT, E-stim, ...] │
│ Therapist: [Dropdown: Staff list]      │
│ Duration:  [30] minutes                 │
│ Notes:     [___________]                │
│                                         │
│          [Cancel]  [Add Treatment]      │
└─────────────────────────────────────────┘
```

### 4.3 Checkout Modal（增强版）

```text
┌─────────────────────────────────────────┐
│      Checkout: John Doe                 │
├─────────────────────────────────────────┤
│ Treatments Performed:                   │
│ ┌─────────────────────────────────────┐ │
│ │ Modality  Therapist    Duration Time│ │
│ │ PT        Dr. Chen     30min   10:00│ │
│ │ E-stim    Dr. Chen     15min   10:30│ │
│ │ Massage   Lisa Wu      20min   10:45│ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Copay Collected: [$25] ✓                │
│ Walk & Dance:    [✓] Verified           │
│ Patient Signed:  [✓] Completed          │
│                                         │
│ [✓] Generate sign sheet PDF             │
│                                         │
│         [Cancel]  [Complete Checkout]   │
└─────────────────────────────────────────┘
```

### 4.4 Patient Detail Modal（增强版）

```text
┌─────────────────────────────────────────┐
│  John Doe | DOB: 1980-05-15             │
├─────────────────────────────────────────┤
│ Visit History:                          │
│ [✓] 2026-03-27 | PT+E-stim | $25 | ✓    │
│ [✓] 2026-03-20 | Massage   | $25 | ✓    │
│ [ ] 2026-03-13 | PT        | $25 | ✓    │
│                                         │
│ [Download Selected Visits PDF (2)]      │
│ [Download All History PDF]              │
└─────────────────────────────────────────┘
```

### 4.5 Treatment Records Page（新增）

```text
┌─────────────────────────────────────────┐
│        Treatment Records                │
├─────────────────────────────────────────┤
│ Filters:                                │
│ Date: [2026-03-01] to [2026-03-31]      │
│ Patient: [All ▼]  Staff: [All ▼]        │
│ Modality: [All ▼]                       │
│           [Apply Filters] [Export CSV]  │
├─────────────────────────────────────────┤
│ Patient    Date       Modality Therapist│
│ John Doe   03-27 10:00 PT       Dr. Chen│
│ John Doe   03-27 10:30 E-stim   Dr. Chen│
│ Jane Smith 03-27 11:00 Massage  Lisa Wu │
│ ...                                     │
└─────────────────────────────────────────┘
```

---

## 5. 实施阶段

### Phase 1：数据库 + Backend APIs（P0）
- 创建 `visit_treatments` 表（migration）
- 实现 6 个新 API
- 为 treatments 增加 event logging
- **预估：** 8 小时

### Phase 2：核心 UX（P0）
- 在 active visits 中增加 treatment 管理
- 增强 checkout modal，支持复核 treatments
- **预估：** 6 小时

### Phase 3：PDF 增强（P1）
- 增加 checkout 时“生成 PDF” checkbox
- 实现按 visit checkbox 选择性生成 PDF
- 更新 PDF 模板，在每次 visit 下展示所有 treatments
- **预估：** 4 小时

### Phase 4：Treatment Records 页面（P2）
- 新增 treatment records 页面 / tab
- 增加筛选 + CSV 导出
- **预估：** 5 小时

**总预估：** 23 小时（约 3 天）

---

## 6. 成功指标

- **Adoption：** 两周内 ≥80% 的 visits 使用多 treatment 记录
- **Accuracy：** 因缺失 treatment records 导致的 billing dispute 为 0
- **Efficiency：** 因预填 treatments，checkout 时间下降 30%
- **Compliance：** 100% PDF 包含完整 treatment breakdown

---

## 7. 当前阶段不包含（未来）

- 与 billing system 的 CPT code mapping 集成
- 自动化 insurance claim 生成
- 实时 treatment 时长计时器
- treatment templates / favorites

---

## 8. 依赖项

- 依赖：Event sourcing framework（ADR-001）
- 依赖：PDF generation service（fpdf2）
- 依赖：带 therapist 角色的 staff 表

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|--------|------------|
| Legacy `service_type` 引发混淆 | 中 | 保留字段，但在代码注释中标记为 `LEGACY` |
| 100+ visits 时 PDF 生成性能下降 | 中 | 增加分页 / 日期范围限制 |
| 单个 visit 多治疗师导致 billing 更复杂 | 高 | 增加 CSV 导出供人工 billing 复核 |

---

## 10. 合规说明

- 所有治疗记录写入 `event_log`（不可变审计链）
- 非 provider 角色不可看到带 PII 的 treatment notes
- checkout 生成 PDF 前需要患者签字
- 保留期：按 HIPAA 要求保存 7 年（`event_log` 永不删除）

---

**审批：**
- [x] Product Manager：Approved 2026-03-27
- [x] Engineering Lead：可行，预估 3 天
- [x] Compliance：在强制事件记录的前提下满足 HIPAA
