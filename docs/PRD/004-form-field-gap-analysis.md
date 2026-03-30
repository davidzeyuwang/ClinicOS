# PRD-004: 基于现有纸质表单的字段差距分析与功能补全需求

**Status:** Draft v1
**Date:** 2026-03-26
**来源:** 分析现有 7 张实际使用的表单图片（Files/ 目录）
**关联:** PRD-001（日常运营板）、PRD-003 §11（所有模块）

---

## 1. 分析的现有表单

| 文件 | 表单名称 | 用途 |
|------|----------|------|
| `daily sign in sheet.png` | 每日签到总表 | 每日患者+员工出勤与服务记录 |
| `个人签字表.png` | 个人签字表（完整版） | 单患者保险信息+每次就诊签字 |
| `个人签字表表头.png` | 个人签字表（表头特写） | 保险验证字段详情（可读版） |
| `个人诊疗记录表.png` | 个人诊疗记录表 | 每次治疗项目详细记录 |
| `房间排班表.png` | 房间排班表（Google Sheets） | 实时房间占用与患者分配 |
| `签字总表list.png` | 签字总表（Notability） | 全患者签字表数字归档索引 |
| `asana insurance inquiry list.png` | 保险资格查询列表（Asana） | 保险资格验证任务管理 |

---

## 2. 表单字段详解与当前系统差距

### 2.1 个人签字表（保险信息表头）— 最高优先级

这是当前系统差距最大的部分。个人签字表表头承载完整的保险验证字段，**当前 ClinicOS 完全缺失**。

#### 2.1.1 患者基础信息（表头）

| 字段 | 英文标签 | 当前状态 | 优先级 |
|------|----------|----------|--------|
| 姓（Last Name） | Last Name | ✅ 已有 | - |
| 名（First Name） | First Name | ✅ 已有 | - |
| 保险计划类型 | Plan Type（PPO/HMO/EPO等） | ❌ 缺失 | P0 |
| 保险公司名称 | Carrier | ❌ 缺失 | P0 |
| 保险 Member ID | Member ID | ❌ 缺失 | P0 |
| Group 号码 | Group No | ❌ 缺失 | P0 |
| Plan Code | Plan Code | ❌ 缺失 | P1 |
| 诊所就诊共付额 | Office Visit Copay | ❌ 缺失 | P0 |
| 生效日期 | Effective Date（起止） | ❌ 缺失 | P0 |
| 是否需要转诊单 | Referral From MD（Y/N） | ❌ 缺失 | P0 |
| 是否需要预授权 | Pre-Authorization Required（Y/N） | ❌ 缺失 | P0 |
| 允许就诊次数 | Allow Visits（年度限额） | ❌ 缺失 | P0 |
| 已使用就诊次数 | Used Visits | ❌ 缺失 | P0 |

#### 2.1.2 保险 Deductible / OOP 字段（双份保险支持）

> 注：表单支持**主保险（Primary）+ 次保险（Secondary）**两列

| 字段 | 英文标签 | 支持双份保险 | 当前状态 | 优先级 |
|------|----------|-------------|----------|--------|
| 个人免赔额 | Deductible (Individual) | ✅ | ❌ 缺失 | P0 |
| 已满足免赔额 | Deductible Met (IND) | ✅ | ❌ 缺失 | P0 |
| 家庭免赔额 | Deductible (Family) | ✅ | ❌ 缺失 | P1 |
| 已满足家庭免赔额 | Family Deductible Met | ✅ | ❌ 缺失 | P1 |
| 个人自付最高额 | Out of Pocket Max (Individual) | ✅ | ❌ 缺失 | P0 |
| 已满足自付最高额 | OOP Met | ✅ | ❌ 缺失 | P0 |
| 保险覆盖比例 | Coverage % | ✅ | ❌ 缺失 | P0 |
| 每次就诊共付额 | Copay (per visit) | ✅ | ❌ 缺失 | P0 |
| 患者实际支付额 | Patient Pay | ✅ | ❌ 缺失 | P0 |

#### 2.1.3 药房保险字段（可选）

| 字段 | 英文标签 | 当前状态 | 优先级 |
|------|----------|----------|--------|
| 药房 BIN | RxBIN | ❌ 缺失 | P2 |
| 药房 PCN | RxPCN | ❌ 缺失 | P2 |
| 药房 Group | RxGRP | ❌ 缺失 | P2 |

#### 2.1.4 验证元数据

| 字段 | 英文标签 | 当前状态 | 优先级 |
|------|----------|----------|--------|
| 查证人员 | Checked By（工作人员初签） | ❌ 缺失 | P1 |
| 医疗审核入口/参考 ID | Medical Review Portal Reference | ❌ 缺失 | P2 |
| 覆盖项目 | Coverages（Medical / Pharmacy） | ❌ 缺失 | P1 |

---

### 2.2 个人签字表（每次就诊签到列表）— 高优先级

每次就诊在表单底部记录一行。当前系统**有部分字段但缺少关键字段**。

| 字段 | 英文标签 | 当前状态 | 说明 |
|------|----------|----------|------|
| 就诊日期 | Date of Service | ✅ 已有（check_in_time） | - |
| W / D 字段 | W、D（纸质表单中为两个独立列，业务含义待确认） | ❌ 缺失 | 当前系统曾将其合并理解为一个 `WD` 字段，此含义尚未得到业务确认 |
| 患者手写签字 | Patient Signature | ❌ 缺失 | 数字签名或确认点击 |
| 共付额已收款 | CC（Copay Collected，金额） | ❌ 缺失 | 当次实际收取金额 |
| 备注 | Note | ⚠️ 部分（visit notes） | 需在签到行级别支持 |

---

### 2.3 每日签到总表（Daily Sign In Sheet）

这是当前 ClinicOS 部分实现的功能。对比实际表单，差距如下：

| 字段 | 当前状态 | 差距说明 |
|------|----------|----------|
| 日期表头 | ✅ 已有 | - |
| 员工/医生姓名列 | ✅ 已有（staff） | - |
| 每位员工每个患者对应一列/行 | ⚠️ 部分 | 当前按时间轴显示，原表为格状交叉表 |
| 患者每次就诊签到记录 | ✅ 已有（visit） | - |
| 当日合计统计 | ⚠️ 部分 | 有 staff hours 但缺少独立的"当日汇总行" |
| 跨员工横向对比 | ❌ 缺失 | 当前无横向多员工对比视图 |

---

### 2.4 个人诊疗记录表（Treatment Record）— 中优先级

每次就诊的治疗项目记录。当前系统**只有 `service_type` 单字段，缺少治疗项目明细**。

#### 2.4.1 患者+主诊信息

| 字段 | 当前状态 | 优先级 |
|------|----------|--------|
| 患者姓名 | ✅ 已有 | - |
| 主诊医生/治疗师 | ⚠️ 有 staff_id，但显示不完整 | P1 |

#### 2.4.2 每次就诊治疗项目（模态记录）

当前 `service_type` 只能记录一个服务类型。实际表单记录**多个治疗模态同时进行**。

| 字段/治疗项目 | 缩写 | 当前状态 | 优先级 |
|--------------|------|----------|--------|
| 多个并发治疗项 checkbox | - | ❌ 缺失 | P1 |
| 治疗备注 | Note | ⚠️ 有 clinical note，但未嵌入治疗行 | P2 |

> 更正：此前文档中的 `OUT`、`WW`、`CAST/GAS`、`Sig` 为 AI/OCR 误读，不是已确认的纸质表单字段，已移除。

**→ 需要新增 `visit_treatments`（多对一）表，记录每次就诊使用的多个治疗项目。**

---

### 2.5 房间排班表（Room Scheduling）— 当前实现接近但有差距

| 字段 | 当前状态 | 差距 |
|------|----------|------|
| 房间名称/代码 | ✅ 已有 | - |
| 房间状态（available/occupied/cleaning/OOS） | ✅ 已有 | - |
| 当前患者姓名 | ✅ 已有 | - |
| 当前服务类型 | ✅ 已有 | - |
| 楼层标记（16楼/18楼） | ❌ 缺失 | 当前有 `floor` 字段但未在 UI 中按楼层分组显示 |
| 状态更新时间 | ⚠️ 有 updated_at，但未显示 | P2 |
| 多楼层分组视图 | ❌ 缺失 | UI 不按楼层分组 |

> 更正：此前文档中提到的 `BA`、`RA`、`MA`、`NA` 并非已确认的原始房间表状态码，属于 AI/OCR 误读，已移除。

---

### 2.6 签字总表（Patient Archive Index）— 低优先级（Phase 2）

当前用 Notability 管理 317+ 个患者的签字表档案。ClinicOS 需要：

| 需求 | 优先级 |
|------|--------|
| 患者档案列表：按 Last, First 格式排序 | P1（已有 patients 列表） |
| 每患者签字记录归档（数字签名或 PDF） | P2 |
| 按更新日期快速查找患者 | P1（已有） |
| In-Network（INN）标记 | ❌ P1（标记患者为 in-network/out-of-network） |
| 患者可按保险公司分组 | P2 |
| 历史年份归档分区显示 | P2 |

---

### 2.7 保险资格查询（Asana Insurance Eligibility Workflow）— Phase 2

当前 ClinicOS **完全没有**保险资格验证（Eligibility）工作流。需要新建功能模块。

#### 每个保险验证任务的字段

| 字段 | Asana 中的等价 | 优先级 |
|------|----------------|--------|
| 患者姓名 | Task Name | P0 |
| 保险公司 | Task Name / Description | P0 |
| Plan Type | Description | P0 |
| 验证状态 | Task completion | P0 |
| 验证问题检查清单（5 Questions SOP） | Subtasks | P1 |
| 验证人员 | Assignee | P1 |
| 附件（EOB截图/保险卡） | Attachments | P2 |
| 年度项目分组（2025/2026） | Project | P1 |
| 关联患者档案 | - | P0 |
| 验证完成后自动填充 `个人签字表表头` | - | P1 |

---

## 3. 差距汇总与优先级矩阵

### 3.1 当前系统（ClinicOS 原型）完全缺失的功能

| 功能模块 | 说明 | 优先级 |
|----------|------|--------|
| 保险信息字段（完整） | Plan Type, Carrier, Member ID, Group No, Copay, Deductible, OOP, Coverage%, Allow/Used Visits, Referral/Preauth required | **P0 — 核心运营必须** |
| 双份保险支持（Primary + Secondary） | 所有保险字段支持2列对比 | P0 |
| 就诊签字 + CC（共付额收款记录） | 每次就诊的患者签认+实收金额 | P0 |
| 治疗项目明细（多项同次） | visit_treatments 表 | P1 |
| 保险资格验证工作流（Eligibility） | 完整替代 Asana 流程 | P1 |
| In-Network / Out-of-Network 患者标记 | 患者层级标记 | P1 |
| 楼层分组的房间视图 | 16F/18F 分开展示 | P1 |
| 数字签名功能 | 患者每次就诊签名归档 | P2 |
| 签字表档案系统 | 替代 Notability 归档 | P2 |

### 3.2 当前系统有但不完整的功能

| 功能 | 差距 |
|------|------|
| 房间状态管理 | 缺楼层分组、缺 WD 字段 |
| 患者列表 | 缺 in-network 标记，缺保险关联显示 |
| 就诊记录 | service_type 单字段 → 需多模态治疗记录 |
| 日报 | 有合计但缺横向员工对比和共付额汇总 |
| 员工小时统计 | 已有，需加入每日实收共付额金额汇总 |

---

## 4. 数据模型变更需求

### 4.1 需新增字段：`insurance_policies` 表（保险信息）

```sql
-- 关联 patients，支持 primary/secondary
ALTER TABLE insurance_policies ADD COLUMN plan_type VARCHAR(20);         -- PPO/HMO/EPO
ALTER TABLE insurance_policies ADD COLUMN carrier VARCHAR(100);          -- Anthem/BCBS/Aetna
ALTER TABLE insurance_policies ADD COLUMN plan_code VARCHAR(20);
ALTER TABLE insurance_policies ADD COLUMN effective_date_start DATE;
ALTER TABLE insurance_policies ADD COLUMN effective_date_end DATE;
ALTER TABLE insurance_policies ADD COLUMN referral_required BOOLEAN DEFAULT FALSE;
ALTER TABLE insurance_policies ADD COLUMN preauth_required BOOLEAN DEFAULT FALSE;
ALTER TABLE insurance_policies ADD COLUMN allow_visits INTEGER;          -- 年度限额
ALTER TABLE insurance_policies ADD COLUMN used_visits INTEGER DEFAULT 0;
ALTER TABLE insurance_policies ADD COLUMN office_visit_copay NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN deductible_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN deductible_individual_met NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN deductible_family NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN deductible_family_met NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN oop_max_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN oop_met_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN coverage_pct NUMERIC(5,2);    -- e.g. 90.00
ALTER TABLE insurance_policies ADD COLUMN copay_per_visit NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN rx_bin VARCHAR(20);
ALTER TABLE insurance_policies ADD COLUMN rx_pcn VARCHAR(20);
ALTER TABLE insurance_policies ADD COLUMN rx_grp VARCHAR(20);
ALTER TABLE insurance_policies ADD COLUMN coverages TEXT;               -- Medical/Pharmacy/etc
ALTER TABLE insurance_policies ADD COLUMN checked_by VARCHAR(50);
ALTER TABLE insurance_policies ADD COLUMN is_primary BOOLEAN DEFAULT TRUE;
ALTER TABLE insurance_policies ADD COLUMN is_in_network BOOLEAN DEFAULT TRUE;
```

### 4.2 需新增字段：`visits` 表（就诊记录）

```sql
ALTER TABLE visits ADD COLUMN copay_collected NUMERIC(10,2);    -- CC: 实收共付额
ALTER TABLE visits ADD COLUMN patient_signed BOOLEAN DEFAULT FALSE;
ALTER TABLE visits ADD COLUMN patient_signature_at TIMESTAMPTZ;
ALTER TABLE visits ADD COLUMN wd_verified BOOLEAN DEFAULT FALSE; -- 临时字段：当前实现将纸质表单中的 W/D 合并为单一布尔值，待业务确认后应重构
```

### 4.3 需新建表：`visit_treatments`（治疗项目多对一）

```sql
CREATE TABLE visit_treatments (
    treatment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id       UUID NOT NULL REFERENCES visits(visit_id),
    modality       VARCHAR(50) NOT NULL,  -- PT/OT/Eval/E-stim/Massage/Cupping/etc
    therapist_id   UUID REFERENCES staff(staff_id),
    duration_min   INTEGER,
    notes          TEXT,
    recorded_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.4 需新建表：`eligibility_cases`（保险资格验证工作流，替代 Asana）

```sql
CREATE TABLE eligibility_cases (
    case_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    insurance_id    UUID REFERENCES insurance_policies(policy_id),
    carrier         VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'pending', -- pending/in_progress/verified/failed
    verified_by     UUID REFERENCES staff(staff_id),
    verified_at     TIMESTAMPTZ,
    notes           TEXT,
    year            INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE eligibility_checklist_items (
    item_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID REFERENCES eligibility_cases(case_id),
    question    TEXT NOT NULL,   -- e.g. "Ask: Is PT covered under this plan?"
    answered    BOOLEAN DEFAULT FALSE,
    answer      TEXT,
    order_num   INTEGER
);
```

### 4.5 需新增字段：`patients` 表

```sql
ALTER TABLE patients ADD COLUMN network_status VARCHAR(20) DEFAULT 'in_network';  -- in_network/out_of_network
ALTER TABLE patients ADD COLUMN primary_insurance_id UUID;   -- FK to insurance_policies
ALTER TABLE patients ADD COLUMN secondary_insurance_id UUID; -- FK to insurance_policies
```

---

## 5. UI 变更需求

### 5.1 患者档案页——新增保险信息 Tab

在患者详情页中新增 **Insurance** Tab，包含：
- Primary Insurance 信息卡（所有 §4.1 字段）
- Secondary Insurance 信息卡（相同结构）
- 验证状态 + Checked By + 验证日期

### 5.2 就诊记录——新增共付额收款字段

在签到/就诊记录中：
- `CC (Copay Collected)` 输入框：当次实收金额
- `W / D` 字段：纸质表单存在两个列，当前业务含义未确认，不应继续假设其等同于单一 `WD Verified`
- `Patient Signed` 状态标记（Phase 2 支持数字签名）

### 5.3 就诊记录——新增多模态治疗项目记录

在就诊详情中：
- 可添加多个 `treatment` 条目（modality + therapist + duration）
- 内置治疗模态选项：PT、OT、Eval、Re-eval、E-stim、Massage、Cupping、Acupuncture、Speech、Taping 等
- 每个条目可指定不同治疗师

### 5.4 Ops Board——按楼层分组房间

在 Room Board 中按 `floor` 字段分组展示（16F / 18F 分开）

### 5.5 新增 Eligibility 工作流模块（Phase 2）

替代 Asana：
- 保险资格验证任务列表（按年度）
- 每个任务表单填写并关联患者
- 内置5问检查清单
- 完成后自动同步到患者保险信息卡

---

## 6. 事件合约补充

在现有事件模型基础上新增以下事件类型：

```
INSURANCE_CREATED       -- 保险信息新建
INSURANCE_UPDATED       -- 保险信息更新
ELIGIBILITY_VERIFIED    -- 保险资格验证完成
COPAY_COLLECTED         -- 共付额收款记录
PATIENT_SIGNED          -- 患者签字确认
TREATMENT_RECORDED      -- 治疗项目记录
```

---

## 7. 与现有 PRD 的关系

| 本文档章节 | 对应现有 PRD |
|-----------|-------------|
| §2.1 保险字段 | PRD-003 §11.7（Insurance Policy）→ **大幅扩展** |
| §2.2 就诊签字+CC | PRD-001 §Milestone1（Portal）→ **补充字段** |
| §2.3 每日签到总表 | PRD-001 §Milestone1 → **基本覆盖** |
| §2.4 诊疗记录表 | PRD-003 §11.6（Clinical Notes）→ **需新建 visit_treatments** |
| §2.5 房间排班表 | PRD-001 §Milestone1 → **补充楼层视图** |
| §2.6 签字总表 | PRD-003 §11.4（Documents）→ **Phase 2** |
| §2.7 保险资格查询 | PRD-003 §11.7 → **需新建 eligibility 模块** |

---

## 8. 实现优先级建议

### Phase 1（当前原型补充，紧急）
1. `insurance_policies` 表字段全量补充 — 立即支持前台日常操作
2. `visits.copay_collected` + `W/D` 字段定义确认 — 每次就诊金额记录已实现，但 W/D 的准确业务含义仍需确认
3. 患者详情页保险信息 Tab — 替代 Notability 的表头填写

### Phase 2（下一轮迭代）
4. `visit_treatments` 多模态治疗记录表
5. 房间按楼层分组视图
6. 患者 in-network/out-of-network 标记

### Phase 3（独立模块）
7. Eligibility 工作流（替代 Asana）
8. 数字签名归档（替代 Notability）
9. 签字总表档案系统

---

*本文档基于 Files/ 目录下 7 张实际使用表单的字段分析生成。优先级 P0 = 不实现则当前工作流无法数字化，P1 = 显著提升效率，P2 = 完整替代纸表。*
