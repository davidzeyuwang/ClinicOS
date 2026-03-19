# Clinic OS 产品需求文档（PRD）

## 1. 文档信息

**产品名称**：Clinic OS
**版本**：v2.0
**文档类型**：完整 PRD（整合更新版）
**目标阶段**：MVP → AI 自动化增强 → 多诊所扩展

---

## 2. 产品背景

当前诊所运营依赖多种非统一工具共同维持，包括：

* Daily Sign In Sheet（纸质签到总表）
* Google Sheets（如 room availability / 运营表）
* Notability（签字、截图、归档、部分记录）
* Asana（eligibility / insurance / follow-up task 管理）

这些工具分别解决局部问题，但没有统一主数据、统一状态机、统一权限模型和统一审计链路。Clinic OS 的目标，是把诊所从"纸表 + Google Sheet + Notability + Asana + 人工同步"的碎片化模式，升级为一个统一数据源、统一工作流、可审计、可扩展、可自动化的 clinic operating system。

---

## 3. 基于当前观察到的现状工具样例

### 3.1 Daily Sign In Sheet（纸质签到总表）

该表不只是签到表，还承担：

* 患者签到
* 服务项目记录
* 保险状态简记
* 支付状态简记
* 特殊分类标记
* 下次预约记录
* 当日统计汇总

说明当前前台日运营依赖一张纸表做总控。

### 3.2 Google Sheets（room availability）

该表不只是房间空闲表，还承担：

* 房间占用状态
* 当前患者
* 当前服务类型
* staff/provider 分配
* 时间更新
* 多楼层资源调度

说明当前 room sheet 本质上是人工版实时 resource allocation board。

### 3.3 Notability

当前 Notability 可能同时承担：

* 新患者签字材料归档
* intake / consent / insurance 截图保存
* 按患者组织的文档集合
* 某些情况下的部分 charting / case 记录

很多时候前台、后台、临床人员都在使用同一个 Notability 或相近记录载体。问题不在于他们完全用不同系统，而在于这个载体不是结构化、强约束、支持并发控制的业务系统，因此会出现多人编辑、相互覆盖、race condition、状态不可靠等问题。

### 3.4 Asana

Asana 当前实际承担：

* eligibility verification case 管理
* insurance follow-up case 管理
* subtasks 协作
* 附件驱动流程
* 不同年份/类别项目归档

说明 Asana 已经被当成轻量运营 case management system 在用。

---

## 4. 当前核心问题

### 4.1 共享记录载体不等于统一主数据源

* 即使多人共同使用同一个 Notability/记录载体，也不代表存在统一主数据源
* 当前没有结构化、可审计、可并发控制的 source of truth
* 同一患者、同一次就诊、同一个 insurance case 可能被多人以不同方式补充或覆盖
* 缺乏 record locking、版本控制、字段级 ownership、冲突检测机制
* 因此前台、后台、临床虽然"看起来在一个地方记录"，实际仍然会发生信息不一致和 race condition

### 4.2 高人工成本

* 依赖人工同步签到、房间、保险、chart、billing 状态
* 依赖口头沟通、Slack、Asana、表格备注传递上下文
* 需要人工判断 note 是否完整、是否可 billing、claim 是否可推进

### 4.3 缺乏流程闭环

* 患者签到后，系统不能自动推进到待就诊/待记录/待 billing
* chart 完成后，不能自动触发 claim 或任务流
* claim denied 后不能自动回流到待补资料或 follow-up 队列
* 流程推进常依赖人工判断，而不是系统状态机

### 4.4 合规与审计风险

* PHI/PII 散落在纸表、截图、表格、任务工具中
* 访问控制粗放，难以做到最小权限
* 谁看过、谁改过、谁签署过、谁导出过，难以追溯
* 第三方工具若接触患者信息，需要明确 BAA / DPA / retention policy

---

## 5. 产品目标

Clinic OS 需要实现：

1. 统一患者主档
2. 统一前台运营入口
3. 统一 visit / note / billing 状态链路
4. 统一 insurance / claim / task 流程
5. 统一角色权限与审计
6. 为语音/手写/自由输入转结构化打基础
7. 为未来 AI agent 接管后台标准化工作打基础

---

## 6. 目标用户与角色

### 6.1 前台（Front Desk）

关注：

* 今日预约
* 到店签到
* 房间分配
* 付款提示
* 保险/资料缺失提示
* 下次预约

### 6.2 后台运营 / Billing

关注：

* eligibility / benefits verification
* claim ready / claim submitted / denied / paid
* missing info
* AR follow-up
* case/任务队列

### 6.3 Provider / 临床人员

关注：

* 今日患者
* 当前 visit
* note 完成情况
* 历史记录与附件

### 6.4 Admin / Owner

关注：

* 诊所运营效率
* 房间利用率
* provider 利用率
* note 完成率
* claim funnel / denial rate
* 权限与审计

---

## 7. 现有工具去留策略

### 7.1 总体原则

* Clinic OS 上线后，所有核心业务状态必须逐步收敛到 Clinic OS
* 现有工具在迁移期可保留，但不能长期并列充当主系统
* 可以保留文档工具、附件工具、协作工具，但不能继续作为核心 source of truth

### 7.2 四类工具未来定位

| 工具                        | 当前主要用途                                   | MVP 阶段  | 长期定位                               | Clinic OS 对应模块                               |
| ------------------------- | ---------------------------------------- | ------- | ---------------------------------- | -------------------------------------------- |
| Daily Sign In Sheet       | 前台签到、服务记录、付款简记、下次预约、统计                   | 迁移期可并存  | 停用主流程，仅可做打印备份                      | Front Desk Operations Board                  |
| Google Sheets（room board） | 房间/资源实时分配                                | 迁移期对照使用 | 被替代                                | Front Desk Operations Board + Resource Model |
| Notability                | 签字、截图归档、部分记录                             | 可部分保留   | 保留文档层，不保留主系统角色                     | Document / Consent / Clinical Note           |
| Asana                     | eligibility / insurance / follow-up task | 迁移期并存   | 患者核心任务迁回 Clinic OS；Asana 仅留通用协作或退出 | Task / Case Management                       |

---

## 8. 产品范围

### 8.1 MVP 范围

1. 患者主档管理
2. 预约管理
3. 前台运营工作台（合并签到 + 房间/资源板 + 当日运营总控）
4. Visit 管理
5. Note/Chart 管理
6. 签字 / 文档生成与归档
7. Insurance / Eligibility 基础记录
8. Claim 流程状态管理
9. 基础任务流（吸收 Asana 关键场景）
10. 角色权限与审计日志
11. Dashboard 基础报表

### 8.2 后续阶段

1. OCR 识别保险卡/表单
2. 语音 / 手写 / 自由文本输入
3. OCR / speech-to-text / LLM extraction
4. AI note QA / completeness check
5. AI claim denial 分类与建议
6. AI tasking / AI operator
7. 多诊所、多品牌、多地点支持
8. 与 EHR / calendar / payment / clearinghouse 深度集成

---

## 9. 核心业务对象（Domain Model）

* Patient
* Appointment
* Visit
* Room / Resource Allocation
* Clinical Note
* Document
* Consent / Intake Package
* Insurance Policy
* Eligibility Check
* Claim
* Task / Case
* User
* Role / Permission
* Audit Log

---

## 10. 核心流程

### 10.1 患者到店与前台运营流程

1. 患者已有预约
2. 前台在统一前台运营工作台中找到患者
3. 点击签到
4. 系统更新 appointment 状态为 checked_in
5. 若需要，前台补录保险/表单/欠费信息
6. 前台在同一工作台内完成房间分配
7. 系统同步更新 room / visit / provider 上下文
8. Provider 开始接诊
9. 就诊结束后，visit 进入待记录/待签署/待 billing 状态

### 10.2 前台运营工作台流程说明

* 前台在一个页面同时完成签到、分房、查看患者当前位置、记录服务类型、查看 payment/insurance 提示、补记下次预约
* Daily Sign In Sheet 与 room availability board 在产品体验上合并为一个统一入口
* 底层数据仍拆分为 appointment/check-in、visit、room allocation、payment/insurance hint 等结构化对象

### 10.3 Chart / Note 完成流程

1. Provider 打开 visit 对应 note 模板
2. 填写或录入 note
3. 系统校验必填字段
4. Provider 签署
5. note_status = signed
6. 若满足 billing 条件，则将 visit 标记为 claim_ready

### 10.4 Insurance / Claim 流程

1. 录入或更新保险信息
2. 后台完成 eligibility / benefits verification
3. 结果写回患者档案和 visit 上下文
4. note 完成后进入 claim_ready
5. claim 提交后状态为 submitted
6. denied / pending / paid 更新状态并触发相应任务

---

## 11. 功能需求

## 11.1 患者主档模块

* 新建/搜索患者
* 去重提示
* 联系方式、保险、附件、consent、intake 状态
* 多份保险信息管理

## 11.2 预约管理模块

* 创建/修改/取消预约
* 日/周/provider 视图
* walk-in 支持
* no-show / cancellation reason 记录

## 11.3 前台运营工作台（签到 + 房间/资源板合并）

### 目标

将当前 Daily Sign In Sheet 与 Google Sheets room availability 的核心能力合并，形成一个统一的 Front Desk Operations Board，作为前台日常工作的主入口。

### 功能

* 今日预约列表
* 今日签到 / 未到 / 迟到 / no-show / walk-in 管理
* 一键签到
* 房间列表与状态
* 手动分配房间
* 根据 provider / appointment type 过滤适合房间
* 查看占用中 / 待清理 / 空闲
* 当前患者所在房间与服务类型展示
* 收集欠缺资料提醒
* 显示 copay / 未完成 intake / 待更新保险等提示
* next appointment 快捷记录
* 当日统计汇总（替代纸质表头统计区）

### 设计原则

* 前台界面合并：不再要求前台同时盯纸质签到表和 room Google Sheet
* 后端模型拆分：appointment/check-in、visit、room/resource allocation、payment hint、insurance hint 仍保持结构化分层
* 所有状态更新应实时联动

## 11.4 签字 / 文档生成与归档模块

### 目标

替代当前"新签字总表 + Notability 手工归档"的低结构化方式，为每位患者建立可追踪、可自动生成、可版本管理的签字/文档体系。

### 功能

* 系统支持按患者自动创建签字文档容器，而不是每次手工新建零散文档
* 支持按规则生成文档归档视图，例如：

  * /{year}/{patient_name}/
  * 或 /{year}/{patient_id}/
* 在同一患者目录下支持自动新增文档实例
* 支持自增命名，例如：

  * intake_001
  * consent_002
  * visitsign_003
* 支持同一模板多次生成
* 支持历史版本保留与追溯
* 支持 Notability 导出的 PDF/图片/签字文件作为附件回挂到对应 document record

### 关键原则

* 文档路径只是归档视图，不应作为主键
* 真正主键应使用 system-generated document_id
* 推荐使用 patient_id + document_id 作为系统真实标识
* 不建议无规则地每次都新建文档，应支持草稿复用、自动编号和版本控制

### 自动生成规则

* 新患者首次到诊 → 自动生成 intake / consent 文档包
* 某类治疗开始前 → 自动生成该类签字文档
* 年度更新 → 自动生成 renewal 文档
* 若当前年度下已有同类型未完成草稿，则优先复用/继续编辑
* 若业务规则要求新实例，则自动创建下一编号
* 若是模板更新或重签，保留旧版本并创建新版本

## 11.5 Visit 管理模块

* 从 appointment 自动生成 visit
* 记录 check-in / room / provider start / complete 时间
* 关联 note、claim、task、document

## 11.6 Clinical Note / Noteability 模块

### 功能

* note 模板配置
* 草稿 / 最终 / 已签署状态
* 必填字段校验
* note completeness 检查
* 附件上传
* 与 visit 强绑定
* 支持非结构化输入作为入口，未来逐步转为结构化输出

### 非结构化输入能力（未来重点）

系统未来应支持：

* 语音输入
* 手写输入
* 自由文本输入
* 图片/PDF/扫描件输入

并通过 OCR / speech-to-text / LLM extraction 将其转换为结构化字段，例如：

* 主诉
* 治疗项目
* 时间/频次
* provider
* 保险补充信息
* billing 所需字段

### 原则

* 输入可以不固定格式
* 落库时应尽量映射到标准字段
* LLM 抽取结果应支持人工复核，不应在高风险场景中直接无审阅落库

## 11.7 Insurance / Eligibility 模块

* 录入保险信息
* benefit verification 记录
* eligibility 状态维护
* verification 日期与结论记录

## 11.8 Claim / Billing 流程模块

* claim 状态追踪（ready / submitted / pending / denied / paid）
* denial reason 记录
* payment amount / paid date 记录
* AR follow-up 队列

## 11.9 任务管理模块（吸收 Asana 核心流程）

### 功能

* 自动/手动创建任务
* 任务与患者/visit/claim 关联
* assignee / due date / priority / SLA
* comment / activity log
* 队列视图

### AI Agent 未来方向

长期目标不是让人工长期承担全部后台流程，而是让 AI agent 逐步接手标准化后台工作，人工转为审核和异常处理。

未来可由 AI agent 接手的后台工作示例：

* 读取非结构化 note / 表单 / 保险材料并提取字段
* 自动检查 eligibility 所缺信息
* 自动生成 follow-up task
* 自动分类 denial reason 并给出下一步建议
* 自动整理 claim 准备材料
* 自动催办 note completeness
* 自动汇总患者 case 状态供人工审核

### 人机协作原则

* AI agent 先做 copilot，再逐步升级为 operator
* 高风险动作默认需要 human-in-the-loop
* 每一步 AI 操作都要有日志、证据和可回滚能力
* AI 不应直接成为不可审计的黑箱

## 11.10 Dashboard / 报表模块

* 今日签到率
* no-show rate
* 房间利用率
* provider 利用率
* note 完成率
* claim 提交率
* denial rate
* AR aging

## 11.11 权限与审计模块

* RBAC
* 审计日志
* 敏感操作追踪
* 最小权限原则

---

## 12. 非功能需求

### 12.1 安全与合规

* 数据传输/存储加密
* 最小权限
* 审计日志
* BAA / DPA / retention policy 设计

### 12.2 可扩展性

* 支持多 location
* 支持新模板、新 payer、新任务规则
* 为 API / AI agent / 自动化规则引擎预留扩展能力

### 12.3 可用性

* 前台关键操作少点击
* 高峰时段稳定可用
* 常见操作尽量在单页完成

---

## 13. MVP 页面建议

### 前台工作台

* 今日预约列表
* 今日签到 / 未到 / 迟到 / no-show / walk-in 列表
* 患者快速搜索
* 房间状态面板
* 当前患者所在房间与服务类型
* payment / insurance / 待补资料提醒
* next appointment 快捷记录
* 当日统计汇总

### 后台/Billing 工作台

* 待 eligibility 验证
* claim ready 队列
* denied / pending / AR follow-up
* 任务列表

### Provider 工作台

* 今日患者
* 当前 visit
* 待完成 note
* 附件/历史文档

### Admin 工作台

* KPI dashboard
* 用户权限管理
* payer / template / room / provider 配置
* 审计日志查询

---

## 14. 分阶段实施建议

### Phase 1：运营核心打通

* 患者主档
* 预约
* 前台运营工作台（签到 + 房间/资源板）
* Visit
* Note 基础状态
* 文档/签字归档基础版
* 任务管理基础版

### Phase 2：后台保险与 claim 流程打通

* eligibility
* claim 状态机
* denial / AR 队列
* billing dashboard
* 患者相关任务从 Asana 向 Clinic OS 迁移

### Phase 3：AI 输入与自动化

* 语音/手写/自由文本输入
* OCR / speech-to-text / LLM extraction
* note completeness AI 检查
* AI tasking / AI QA

### Phase 4：AI Agent 后台协作

* AI agent 自动处理标准化后台 case
* human review + exception handling
* 操作日志、回滚、审批流完善

### Phase 5：合规强化与深度集成

* 审计日志完善
* 权限细化
* 外部集成
* 多诊所/多地点扩展

---

## 15. 下一步给 Architect / Engineering 的输入

基于本 PRD，下一步应产出：

1. 系统架构 RFC
2. ERD / 数据模型设计
3. 状态机设计（appointment / visit / note / claim / task / document）
4. 角色权限矩阵
5. API 设计
6. MVP roadmap / task breakdown
7. Test / Eval spec
8. 合规设计清单（含 BAA 边界）

---

## 16. 一句话总结

Clinic OS 不是"再做一个表格系统"，而是把诊所从碎片化、人工同步、不可审计、不可并发控制的运营方式，升级成统一数据源、统一流程、支持非结构化输入、并为未来 AI agent 自动化留好架构空间的 clinic operating system。
