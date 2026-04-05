# PRD-007：保险 Intake 与资格自动查验

**状态：** 草稿 v1
**日期：** 2026-04-04
**Owner：** 产品
**相关：** PRD-003 §11.7、PRD-004（Gap Analysis）、RFC-003

---

## 1. 背景

ClinicOS 当前已经存储基础保险字段（`carrier_name`、`member_id`、`group_number`、`plan_type`、`copay_amount`、`deductible`、`priority`、`eligibility_status`），但仍然缺少诊所纸质签到表要求的完整字段集（PRD-004 中的 GAP-INS-01 至 GAP-INS-12）。目前 eligibility verification 仍通过 Asana 任务列表手工管理，staff 需要逐个登录 payer portal、查询患者信息，再把结果抄回纸质表单。

本 PRD 定义以下需求：
1. 一套完整的 insurance intake form，用于补齐 PRD-004 中的所有保险字段缺口
2. 一个基于 headless browser 抓取 payer portal 的自动 eligibility inquiry engine
3. 用于审计的不可变 inquiry snapshots，保存每一次查验结果

---

## 2. 目标

- **G1：** 关闭 PRD-004 中识别出的 100% 保险字段差距（GAP-INS-01 至 GAP-INS-12）
- **G2：** 消除人工 payer portal 查询，自动化 eligibility verification
- **G3：** 为每次 eligibility inquiry 建立可审计、不可变的结果记录
- **G4：** 支持周期性重复验证（例如每周、就诊前）而无需 staff 手工介入
- **G5：** 完整替代基于 Asana 的 eligibility workflow

---

## 3. 非目标

- EDI / X12 270 / 271 clearinghouse 集成（后续阶段）
- 就诊现场的实时 eligibility check（后续阶段）
- 自动 prior authorization 提交
- 面向患者的移动端保险卡上传
- Claims 提交或 billing（见 PRD-008）

---

## 4. 功能

| ID | 标题 | 优先级 | 描述 |
|----|-------|----------|-------------|
| INS-01 | 增强版保险 Intake Form | P0 | 带有 PRD-004 全部字段的完整保险表单 |
| INS-02 | 双保险支持 | P0 | 每位患者支持 Primary + Secondary policy |
| INS-03 | Payer 配置注册表 | P0 | 管理员维护支持的 payer、portal URL 与凭据存储 |
| INS-04 | 手动资格查验 | P0 | staff 触发的单患者 eligibility check |
| INS-05 | 不可变 Inquiry Snapshots | P0 | 对每次查验结果保存 append-only 记录 |
| INS-06 | 自动周期性重复查验 | P1 | Scheduler 按可配置周期重新验证资格 |
| INS-07 | 就诊前自动查验触发器 | P1 | 在预约前 48 小时自动校验资格 |
| INS-08 | Payer Adapter Library | P1 | 可插拔抓取适配器，支持 UHC、Aetna、BCBS、Cigna |
| INS-09 | Inquiry Dashboard | P1 | staff 查看 pending / completed / failed inquiries |
| INS-10 | Eligibility Alerts | P1 | 当资格状态变化（denied / expired）时通知 staff |
| INS-11 | 患者级 Inquiry History | P1 | 按患者展示完整 eligibility 检查时间线 |
| INS-12 | Pharmacy Benefit 字段 | P2 | 在 insurance policy 中支持 RxBIN、RxPCN、RxGRP |

### INS-01：增强版保险 Intake Form

**问题：** 当前 `insurance_policies` 表只有 15 个字段，而纸质签到表需要 30+ 个字段，包括 deductible 拆分、OOP 最大值、coverage 百分比、referral / preauth 标记和 verification metadata。

**要求：** 扩展 insurance policy 数据模型与 UI 表单，支持 PRD-004 §2.1 中的全部字段：

- Plan code、effective dates（start / end）
- Referral required（Y/N）、Pre-authorization required（Y/N）
- Deductible：individual amount、individual met、family amount、family met
- Out-of-pocket max：individual amount、individual met
- Coverage percentage
- Copay per visit、coinsurance
- In-network flag
- Checked by（核验员工）
- Visits authorized、visits used

**验收标准：**
1. Insurance policy create / edit form 包含上述所有字段
2. 所有字段可持久化到数据库，并显示在 patient detail view
3. 字段布局尽量与纸质 sign-in sheet 表头一致
4. 已存在的部分数据 policies 仍能继续工作（新字段允许为空）

### INS-02：双保险支持

**问题：** 很多患者同时拥有主保险和次保险。当前模型虽然有 `priority` 字段，但 UI 不能并排展示。

**要求：** Patient insurance tab 以双列方式展示 Primary 和 Secondary policies，与纸质表单布局一致。

**验收标准：**
1. Patient detail page 并排显示 Primary 与 Secondary insurance
2. 两份 policy 均可独立编辑
3. 强制 priority 规则：每个 patient 只能有 0-1 份主保险和 0-1 份次保险
4. Eligibility inquiry 会对两份 policy 独立执行

### INS-03：Payer 配置注册表

**问题：** 每家保险公司都有不同的 portal URL、登录流程与页面结构。系统需要一份带加密凭据的 payer registry。

**要求：** Admin 可管理 payer 配置，包括 portal URL、adapter type 和 credentials（静态使用 Fernet 加密）。

**验收标准：**
1. Admin 可对 payer configurations 执行 CRUD
2. Credentials 使用 Fernet 加密存储，绝不在 API 响应中返回
3. 每个 payer config 包含：`payer_name`、`portal_url`、`adapter_type`、`login fields`
4. Payer configs 以 `clinic_id` 为作用域
5. `adapter_type` 映射到具体 scraping adapter（例如 `"uhc"`、`"aetna"`、`"bcbs"`、`"cigna"`、`"generic"`）

### INS-04：手动资格查验

**问题：** 当前 staff 仍然要手工登录 payer portal 做 eligibility verification。

**要求：** staff 可一键为某个患者的 insurance policy 触发资格查验。系统使用 headless browser（Playwright）抓取 payer portal 并提取 eligibility data。

**验收标准：**
1. 患者 insurance card 上有 `Check Eligibility` 按钮
2. 系统会创建 inquiry record，状态流转为：`pending → running → completed / failed`
3. 完成后，将提取结果自动回填到 insurance policy 字段
4. 原始 inquiry 结果会保存为不可变 snapshot
5. 更新 policy `eligibility_status`（`verified / denied / expired`）
6. 更新 `eligibility_verified_at` 时间戳

### INS-05：不可变 Inquiry Snapshots

**问题：** Eligibility 状态会随时间变化。诊所需要保存每个时间点 payer portal 返回了什么，用于审计和争议处理。

**要求：** 每次 eligibility inquiry 都生成 append-only snapshot，包含原始与解析后的响应数据。

**验收标准：**
1. Snapshots 仅允许 `INSERT`，禁止 `UPDATE` 和 `DELETE`
2. 每个 snapshot 关联 `inquiry_id`、`policy_id`、`patient_id`
3. Snapshot 存储：`raw_html`（或 `raw_data`）、解析字段、payer response timestamp
4. Snapshots 可在 patient eligibility history 中查看
5. 发出 `ELIGIBILITY_SNAPSHOT_CREATED` 事件（仅实体 ID，不含 PHI）

### INS-06：自动周期性重复查验

**问题：** 保险资格随时可能变化，不应要求 staff 手工逐个复查。

**要求：** 通过可配置 scheduler 按固定间隔自动重新执行 eligibility checks（例如每周、双周）。

**验收标准：**
1. Admin 可按 clinic 配置重复查验周期（默认 7 天）
2. Scheduler 会为所有超过周期的 active policies 排队 re-inquiry
3. Re-inquiry 在可配置的 off-hours 窗口执行
4. 失败的 re-inquiry 采用 exponential backoff 重试（最多 3 次）
5. 若重复查验发现资格状态变化，通知相关 staff

### INS-07：就诊前自动查验触发器

**问题：** 患者到院后才发现 eligibility 失效，会导致 billing 问题。

**要求：** 对所有预约，在就诊前 48 小时自动触发 eligibility verification；前提是上次验证已超过配置阈值。

**验收标准：**
1. 默认在预约前 48 小时触发（可配置）
2. 仅当上次验证超过阈值（默认 7 天）时才执行
3. 若资格为 denied 或 expired，则生成 alert
4. Pre-visit 检查结果在 check-in 前可在 visit detail 中看到

### INS-08：Payer Adapter Library

**问题：** 每个 payer portal 都有不同的登录流程、导航路径和数据布局。

**要求：** 采用可插拔 adapter 模式，每个 payer 使用专用 scraping adapter 来处理该 portal。

**验收标准：**
1. 提供基础 adapter interface：`login()`、`search_member()`、`extract_eligibility()`
2. 适配器包括：UHC、Aetna、BCBS、Cigna（P1），以及 Generic fallback（P0）
3. 每个 adapter 负责：portal login、member search、eligibility data extraction
4. 所有 adapter 返回统一的 `EligibilityResult` schema
5. 新增 adapter 时无需修改核心引擎代码
6. Adapter 错误被捕获并记录，但不得暴露 PHI

### INS-09：Inquiry Dashboard

**问题：** 当前看不到哪些患者需要验证、哪些已完成、哪些失败。

**要求：** 提供按状态、payer、日期筛选的 eligibility inquiries dashboard。

**验收标准：**
1. 列表展示所有 inquiries，列包括：patient（ID）、payer、status、last checked、next scheduled
2. 支持按 `status`（`pending / running / completed / failed`）、payer、date range 筛选
3. 支持批量动作：重新执行失败 inquiries
4. 点击后可跳转到 patient eligibility history

### INS-10：Eligibility Alerts

**问题：** 患者两次就诊之间资格状态变化时，staff 可能注意不到。

**要求：** 当自动 re-inquiry 发现 eligibility_status 变为 `denied` 或 `expired` 时，系统生成 alert。

**验收标准：**
1. 当 `eligibility_status` 从 `verified` 变成 `denied / expired` 时创建 alert
2. Alerts 在 inquiry dashboard 和 patient detail 中都可见
3. Alert 包含：`patient_id`、`policy_id`、`old_status`、`new_status`、`checked_at`
4. staff 确认后可 dismiss alert

### INS-11：患者级 Inquiry History

**问题：** 当前没有患者维度的历史 eligibility 检查时间线。

**要求：** 在 patient detail page 中显示按时间排序的所有 eligibility inquiries 与 snapshots。

**验收标准：**
1. 在 patient insurance tab 中提供 timeline view
2. 每条记录显示：date、payer、status、关键字段（coverage%、deductible、copay）
3. 点击展开后可查看完整 snapshot 数据
4. 所有历史记录只读（不可变）

### INS-12：Pharmacy Benefit 字段

**问题：** 纸质表单中包含 RxBIN、RxPCN、RxGRP，但当前数据模型缺失。

**要求：** 在 insurance policy 中增加 pharmacy benefit 字段。

**验收标准：**
1. Insurance policy form 上增加 RxBIN、RxPCN、RxGRP
2. 如 payer portal 可提供这些字段，eligibility inquiry 时自动抓取
3. 这些字段显示在 patient insurance card 上

---

## 5. 用户故事

1. **作为前台人员**，我希望录入完整的保险信息，包括 deductibles、OOP max 和 coverage percentage，这样我就不需要继续维护纸质 sign-in sheet。
2. **作为前台人员**，我希望只点一个按钮就能验证患者资格，而不是手工登录各家 payer portal。
3. **作为 clinic admin**，我希望系统每周自动重新验证资格，这样能在患者到院前发现 coverage 变化。
4. **作为 billing coordinator**，我希望看到每位患者的完整 eligibility history，这样在和 payer 发生 claim dispute 时可以追溯证据。
5. **作为 clinic admin**，我希望能安全配置 payer portal 凭据，让自动化 inquiry 可以脱离 staff 手工介入运行。
6. **作为前台人员**，我希望当患者资格变成 denied 时立即收到提醒，以便在其下次就诊前沟通。

---

## 6. 安全与 HIPAA 注意事项

- **凭据加密：** Payer portal 凭据静态使用 Fernet 加密。绝不通过 API 返回。仅在 inquiry 执行时以内存方式解密。
- **抓取过程中的 PHI：** Payer portal 的原始 HTML / data 可能包含 PHI。需要加密存入 snapshot，绝不以明文方式写入日志。
- **事件 payload：** 所有事件只用实体 ID（`patient_id`、`policy_id`、`inquiry_id`），不把姓名、DOB、member ID 等 PHI 写进 `event_log`。
- **访问控制：** Payer config 管理仅限 admin。触发 inquiry 的权限开放给 frontdesk 及以上角色。
- **Headless browser 隔离：** 抓取引擎运行在隔离进程 / 容器中，每次 inquiry 后清理 browser profile。

---

## 7. Edge Cases

1. **Payer portal 宕机：** Inquiry 优雅失败，状态为 `failed`，稍后重试
2. **凭据失效：** Inquiry 失败，状态为 `auth_failed`，并通知 admin 更新凭据
3. **Portal 布局变化：** Adapter 提取失败，返回部分数据并附带 warning flag
4. **患者无保险：** Intake form 支持标记为 `self-pay`，不触发 inquiry
5. **双保险且同一 carrier：** 两份 policy 仍按 member_id 独立验证
6. **Policy 生效日期在未来：** 可保存，但 `eligibility_status` 置为 `not_yet_effective`
7. **正在 visit 时触发重复查验：** 当前 visit 继续使用 last-known eligibility，新检查排到次日执行

---

## 8. 成功指标

| 指标 | 目标 |
|--------|--------|
| 保险字段完整率 | >95% 的 active patients 填满全部 P0 字段 |
| 人工 portal 查询减少 | staff 登录 portal 的时间减少 >80% |
| Eligibility 信息新鲜度 | >90% 的 active patients 在 7 天内完成验证 |
| Inquiry 成功率 | >90% 的自动 inquiries 成功完成 |
| 发现 eligibility 变化的平均时延 | <48 小时 |

---

## 9. 当前不包含

- EDI 270 / 271 电子资格交易
- 就诊现场的亚秒级实时 eligibility
- 患者自助上传保险卡照片
- 自动化 prior authorization
- Claims 提交（由 PRD-008 覆盖）
- 与 practice management systems 的集成

---

## 10. 发布计划

### Phase 1 — 数据模型 + 手工 Intake
- INS-01：完整 intake form，补齐 PRD-004 字段
- INS-02：双保险 UI
- INS-12：药房福利字段

### Phase 2 — Automated Inquiry Engine
- INS-03：Payer 配置注册表
- INS-04：手动 eligibility inquiry
- INS-05：不可变 inquiry snapshots
- INS-08：Payer adapter library（generic + 1 个 payer）

### Phase 3 — 自动化 + 监控
- INS-06：自动周期性 re-inquiry
- INS-07：就诊前 inquiry trigger
- INS-09：Inquiry dashboard
- INS-10：Eligibility alerts
- INS-11：患者 inquiry history
- INS-08：新增 payer adapters（UHC、Aetna、BCBS、Cigna）

---

## 11. 待确认问题

1. **Rate limiting：** Payer portals 是否对自动查询做频控？需要按 payer 研究并实现 throttling。
2. **Terms of service：** 某些 payer portals 可能禁止自动化抓取，需要按 payer 做法律审查。
3. **Credential sharing：** 一套 portal credentials 能否覆盖所有患者，还是每个 clinic 都要有独立 provider portal account？
4. **Snapshot retention：** 原始 inquiry snapshots 应保存多久？建议按 HIPAA 相关要求保留 7 年。
5. **W / D 字段：** 纸质表单上的 W 和 D 列业务含义尚未确认（PRD-004 §2.2），上线前需由业务方明确。
