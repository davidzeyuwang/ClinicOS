# PRD-008：Claims 自动填充 Chrome Extension

**状态：** 草稿 v1
**日期：** 2026-04-04
**Owner：** 产品 / 计费
**相关：** `docs/PRD/007-insurance-intake-eligibility-auto-inquiry.md`、`docs/RFC/004-claims-autofill-chrome-extension.md`

---

## 1. 背景

ClinicOS 正在从单纯的 visit operations 扩展到面向保险与 billing 的工作流。当前产品已经能够采集 patient、visit、treatment 和 insurance 数据，路线图中也已经纳入 claim 与 remittance 处理能力。当前缺失的，是 billing staff 在 payer portals 上执行的最后一公里工作：把 CMS-1500 数据手工重新录入到网页 claim form 里。

诊所需要一个 Chrome extension，用来：

- 通过 ClinicOS 完成认证
- 让 billing staff 选择一个 patient visit
- 从 ClinicOS 数据组装 CMS-1500 claim payload
- 将该 payload 映射到 payer portal 的字段
- 在保留审计轨迹的前提下自动填表

本 PRD 定义该 extension 及其支撑后端 API 的产品需求。

---

## 2. 目标

- 消除将 CMS-1500 claim 数据手工重复录入 payer portal 的流程
- 在 portal 提交前，对 ClinicOS 记录进行统一 claim assembly
- 支持通用 CMS-1500 映射，使同一个 extension 能适配多个 payer portals
- 降低手工输入造成的 billing 错误
- 保留完整、可追溯的 assembled / filled claim 审计记录

## 3. 非目标

- 直接向 clearinghouse 提交 EDI claim
- 自动 payment posting 或 denial adjudication
- 从扫描的 CMS-1500 纸表中做 OCR 抽取
- 完全无人审核的全自动 claim submission
- 本阶段支持 UB-04 或 dental claim 格式

---

## 4. CMS-1500 数据范围

该 extension 以标准 CMS-1500 字段集为目标，只填充 ClinicOS 能可靠提供的数据。代表性映射如下：

| CMS-1500 Box | 含义 | ClinicOS 来源 |
|---|---|---|
| 1, 1a | 保险类型、被保险人 ID | insurance policy + payer config |
| 2, 3, 5 | 患者姓名、DOB、地址 | patient demographic record |
| 11, 11a-c | policy / group / employment 元数据 | insurance policy |
| 17, 17b | 转诊医生 / NPI | provider / staff + billing config |
| 21 | 诊断代码 | visit diagnoses |
| 24A-J | DOS、place of service、CPT、modifier、diagnosis pointer、charges、units、rendering provider | visit + visit_treatments + billing config |
| 25, 26, 28, 31, 33 | tax ID、account number、total charge、signature、billing provider info | clinic billing config + visit |

任何没有可信来源的字段都必须保持为空，并高亮提示人工复核。

---

## 5. 功能

| ID | 标题 | 优先级 | 描述 |
|---|---|---|---|
| EXT-01 | 诊所 Billing 配置 | P0 | 存储诊所 billing identity、payer IDs、NPI、taxonomy、tax ID、地址 |
| EXT-02 | Claims 诊断信息录入 | P0 | 与 visit 关联的结构化 ICD-10 diagnosis codes |
| EXT-03 | Treatments 的 Procedure Coding | P0 | 在 visit treatments 上记录 CPT / HCPCS、modifiers、units 和 charges |
| EXT-04 | CMS-1500 Assembly API | P0 | 组装规范化 claim payload 的后端接口 |
| EXT-05 | Chrome Extension 壳层 | P0 | Manifest V3 extension，含 popup、service worker、content script |
| EXT-06 | Extension 认证 | P0 | Extension 与 ClinicOS 之间的安全登录 / session 模型 |
| EXT-07 | Patient / Visit Claim Selector | P1 | 搜索并选择可填充 claim 的 visits |
| EXT-08 | Portal Field Mapping Registry | P1 | 按 payer portal 管理 DOM selectors 与 transform rules |
| EXT-09 | Auto-Fill 执行引擎 | P1 | 内容脚本执行 review + retry 的字段填充 |
| EXT-10 | Fill Audit Trail | P1 | 记录 payload 版本、fill attempt、用户、portal 和结果 |

### EXT-01：诊所 Billing 配置

**问题：** Claim 提交需要诊所级 billing identifiers，而这些字段不属于当前运营模型。

**要求：**
- 增加 clinic 级 billing configuration，包含：
  - legal billing name
  - billing address
  - billing phone
  - tax ID / EIN
  - billing NPI
  - taxonomy code
  - default place of service
  - 必要时的 payer-specific submitter IDs

**验收标准：**
1. Admin 可以创建并更新 billing configuration
2. 每个 clinic 只有一份 active billing config
3. 高敏感标识符不会出现在非 admin 响应中
4. 如 billing config 缺失必填字段，CMS-1500 assembly 会明确报错，不可静默忽略

### EXT-02：Claims 诊断信息录入

**问题：** 当前 visit records 尚不能保证有适合 claim assembly 的结构化 diagnosis 数据。

**要求：**
- 支持每个 visit 记录 ICD-10 diagnosis codes
- 记录 diagnosis pointers 的顺序 / 位置，用于 CMS-1500 box 21 和 box 24E

**验收标准：**
1. 每个 visit 支持记录 1-12 个 diagnosis codes
2. Diagnosis 顺序必须保留
3. Claim assembly 返回的 diagnosis codes 顺序符合 CMS-1500 规则
4. 不合法的 ICD-10 格式必须被校验拒绝

### EXT-03：Treatments 的 Procedure Coding

**问题：** 如果没有 procedure codes、modifiers、units 和 charges，extension 无法填充 claim service lines。

**要求：**
- 扩展 `visit_treatments`，增加：
  - CPT / HCPCS code
  - 最多四个 modifiers
  - units
  - line charge
  - rendering provider

**验收标准：**
1. 每个 treatment line 都可携带 billing codes 和 units
2. Claim assembly 为每条 billable treatment 生成一条 CMS-1500 service line
3. 缺少 procedure code 时阻止 claim assembly
4. Total claim charge 根据 line items 自动汇总

### EXT-04：CMS-1500 Assembly API

**问题：** Extension 需要一个统一、标准的 claim payload，而不是拼接多个零散 API 调用。

**要求：**
- 增加 `GET /prototype/billing/visits/{visit_id}/cms1500`
- 响应包含：
  - 标准化 patient block
  - insured block
  - provider block
  - diagnosis block
  - service lines
  - validation warnings / errors

**验收标准：**
1. Endpoint 返回稳定的 JSON contract
2. 缺失数据必须通过 warnings / errors 显式暴露，不能静默丢弃
3. 响应包含 source version metadata，便于审计
4. 只有授权 billing 角色才能访问 claim assembly

### EXT-05：Chrome Extension 壳层

**问题：** 当前没有任何浏览器侧应用可执行 portal autofill。

**要求：**
- 构建一个 Manifest V3 extension，包含：
  - popup UI
  - background service worker
  - content script
  - 如有需要，增加 settings page 用于 debug / mapping inspection

**验收标准：**
1. Extension 可在 Chrome 中无报错安装
2. Popup 能识别当前页面是否为受支持的 payer portal
3. Content script 可以与 background worker 正常通信
4. Extension 中不得硬编码 PHI 或 secrets

### EXT-06：Extension 认证

**问题：** Extension 需要一种安全方式从 ClinicOS 拉取 claim 数据。

**要求：**
- Extension 使用 ClinicOS auth 完成认证，采用短生命周期 token，并支持显式 logout
- 必须保留 clinic 和 role 上下文

**验收标准：**
1. 用户可在 extension popup 中登录
2. Extension session 的过期行为与后端 auth policy 保持一致
3. 未授权请求会被拦截并提示重新登录
4. Tokens 不会暴露到 page DOM 或 portal forms 中

### EXT-07：Patient / Visit Claim Selector

**问题：** Billing staff 需要一种聚焦的方式找到要填的那次 visit。

**要求：**
- 按 patient、DOS、payer、provider 或 visit ID 搜索近期可用于 claim 的 visits
- 在开始 fill 前展示 claim completeness warnings

**验收标准：**
1. Selector 只列出 claim-eligible visits
2. 支持按 patient name、visit date、payer 搜索
3. 选中某个 visit 后可预览 claim warnings
4. staff 可以在 fill 前刷新 claim data

### EXT-08：Portal Field Mapping Registry

**问题：** 每个 payer portal 的 DOM 结构和字段名都不一样。

**要求：**
- 存储按 portal 区分的 mapping definitions：
  - domain match
  - page match
  - CSS / XPath selectors
  - field transforms
  - required / optional 标记

**验收标准：**
1. Admin / developer 可以定义 mappings，而无需为每个 payer 修改 extension 代码
2. 每次 fill attempt 都绑定 mapping version
3. 开始 fill 前，系统会标出未映射的必填字段
4. 同一个 portal 可维护多个版本的 mappings

### EXT-09：Auto-Fill 执行引擎

**问题：** 当前 claim form 填写流程完全人工，既费时又容易出错。

**要求：**
- Content script 支持：
  - preview mode
  - fill mode
  - retry logic
  - post-fill validation

**验收标准：**
1. Fill engine 只向已映射的 inputs 写值
2. 用户在最终提交前可人工复核
3. 填充失败的字段会高亮并给出原因
4. v1 中 extension 不会点击最终 submit，最终提交必须保留人工确认

### EXT-10：Fill Audit Trail

**问题：** 诊所需要知道某个 claim 数据是何时组装的、又是谁执行了 autofill。

**要求：**
- 记录每次 assembly + fill attempt，包括：
  - actor user
  - clinic
  - visit
  - portal domain
  - mapping version
  - outcome
  - changed / failed field counts

**验收标准：**
1. 每次 fill attempt 都会创建审计记录
2. 审计记录中的 event payload 不包含原始 PHI 值
3. staff 可按 visit 查看历史 fill attempts
4. 失败的 fills 提供结构化错误分类

---

## 6. 用户故事

1. 作为 billing staff，我希望选中一条已 checkout 的 visit 并自动填 CMS-1500，这样无需重新手工录入 patient 和 insurance 数据。
2. 作为 clinic admin，我希望配置 billing identity 和 payer mappings，让 extension 能在我们使用的 portals 上运行。
3. 作为 biller，我希望在 fill 开始前就看到缺失的 diagnosis 或 CPT 字段，这样可以先修正 chart 再填单。
4. 作为审计人员，我希望知道哪个用户为哪个 visit 组装并填充了 claim 数据，以便后续调查 billing 问题。

---

## 7. 安全与 HIPAA 注意事项

- Extension 不能在浏览器存储中保留超出必要时长的 PHI
- Tokens 只能保存在 extension 自身作用域的存储中，不能暴露到页面上下文
- Audit events 只使用 entity IDs，不使用患者姓名等原始 demographics
- Portal mappings 中不得写入硬编码 PHI 样本
- Autofill 必须由用户主动触发；后台自动提交不在范围内

---

## 8. Edge Cases

1. Payer 更新后 portal DOM 变化：extension 检测到未映射字段后安全终止 fill。
2. Visit 缺少 diagnosis codes：selector 在开始 fill 前阻止该 visit。
3. 次保险 claim：assembly API 返回所选 insurance priority 和 payer-specific warnings。
4. 多条 treatment 超出 portal 当前可见 service line 行数：extension 分页处理，或停止并给出人工操作提示。
5. Fill 过程中 session 过期：extension 暂停，并提示重新认证后重新加载 claim data。

---

## 9. 成功指标

| 指标 | 目标 |
|---|---|
| 平均手工 claim 录入时间下降 | >60% |
| 无需人工重录即可完成的 claim fill 比例 | >75%（在已映射 portals 中） |
| Fill audit 覆盖率 | 100% 的 extension 发起 fill 都有审计 |
| Claim assembly 预检发现缺失数据的命中率 | >90% |

---

## 10. 发布计划

### Phase 1
- EXT-01 到 EXT-06
- backend claim assembly contract
- extension shell + auth

### Phase 2
- EXT-07 到 EXT-09
- 第一批 mapped payer portals
- staff 端到端试点

### Phase 3
- EXT-10
- admin mapping tools
- 向更多 portals 扩展 rollout

---

## 11. 待确认问题

1. 第一批生产环境支持的 payer portals 是哪些？
2. Claim fill 能力应开放给 `frontdesk`、`admin`，还是新增 `billing` 角色？
3. 当源数据尚未结构化时，CMS-1500 哪些 boxes 在 v1 可以保留人工填写？
4. 诊所未来是否希望 extension 辅助提交，还是永久保留人工最终 submit review？
