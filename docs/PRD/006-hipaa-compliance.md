# PRD-006：HIPAA 合规控制

**状态：** 草稿 v1
**日期：** 2026-04-04
**Owner：** 产品 / 合规
**相关：** `PRD/003-clinic-os-prd-v2.md`、`ADR/001-event-sourcing.md`、`RFC/001-auth-rbac-multitenancy.md`

---

## 1. 背景

ClinicOS 在患者、就诊、保险、治疗、note 和文档工作流中存储和处理 PHI（Protected Health Information）。当前系统已经具备：

- JWT authentication
- role-based access control
- 以 `clinic_id` 为边界的多租户隔离
- 用于写侧动作的不可变 append-only `event_log`

但这些控制仍不足以支撑面向生产环境、符合 HIPAA 预期的使用方式。当前主要缺口包括：

- 对 PHI 读取的审计还不完整
- 空闲会话超时未强制执行
- 尚未实现字段级加密
- 最小必要访问（minimum necessary access）不完整
- 缺少 lockout、breach detection 和 break-glass 机制
- event log 尚未做加密哈希链完整性校验

本 PRD 定义下一阶段面向合规的交付切片。

---

## 2. 目标

- 为 ClinicOS 增加最高优先级的 HIPAA 对齐技术保护措施
- 降低诊所日常运营中的 PHI 暴露风险
- 提升内部复盘与未来合规评审所需的可审计性
- 保持现有 FastAPI + SQLAlchemy + PostgreSQL / Supabase 架构

## 3. 非目标

- 完整法律认证或正式 HIPAA attest
- 应用之外的 BAA、合同、制度与流程文件
- 替换 Supabase 自带的磁盘加密
- 本阶段引入完整 SIEM / SOC
- 组织级 IAM / SSO

---

## 4. 当前 PHI 清单

| 表 | PHI 字段 | 敏感度 |
|---|---|---|
| `patients` | `first_name`, `last_name`, `date_of_birth`, `phone`, `email`, `address`, `mrn` | High |
| `insurance_policies` | `member_id`, `group_number`, `carrier_name`, `copay_amount` | High |
| `clinical_notes` | `content`, `raw_input` | High |
| `visits` | `patient_name`, `patient_id`, `service_type`, `payment_amount`, `copay_collected` | Medium |
| `appointments` | `patient_id`, `appointment_date`, `appointment_time`, `notes` | Medium |
| `documents` | `metadata`, `file_ref`, `patient_id` | Medium |
| `visit_treatments` | `modality`, `therapist_id`, `notes`, `duration_minutes` | Medium |
| `tasks` | `patient_id`, `description` | Low |

---

## 5. 当前技术基线

### 已实现

- 基于 HS256 的 JWT auth
- bcrypt 密码哈希
- 通过 `require_role()` 实现 RBAC
- 核心表与查询基于 `clinic_id` 做租户隔离
- append-only 写事件日志
- Pydantic 请求校验

### 当前状态说明

- 当前登录标识是 `username`，不是 `email`
- 当前 clinic 创建接口是 `/prototype/auth/register-clinic`，且仅限 admin
- 当前 JWT access token 生命周期为 8 小时
- 当前 event log 覆盖写入，不覆盖完整 PHI 读取

---

## 6. 用户角色

| 角色 | 用途 | 合规相关性 |
|---|---|---|
| `admin` | 诊所管理与系统配置 | 权限最高，必须审计最严格 |
| `frontdesk` | patient intake、scheduling、checkout、insurance coordination | 需要看 demographics + insurance，但不应看完整 clinical notes |
| `doctor` | 治疗、note review、临床决策 | 需要临床上下文，但不应看到不必要的财务细节 |

---

## 7. 功能

## P0 — 必须优先交付（Sprint 1）

### HIPAA-01：PHI 审计日志

**问题：** 当前 `event_log` 覆盖了写侧事件，但没有覆盖所有 PHI 读取访问。

**要求：**
- 记录对 PHI 记录的每一次读取访问
- 记录内容包括：
  - 谁访问了数据
  - 访问了什么实体
  - 如适用，对应哪个 patient
  - 何时访问
  - route / action
  - source IP / user agent（如可获取）

**验收标准：**
- 读取 patient detail 时会生成审计记录
- 读取 clinical note content 时会生成审计记录
- 读取 insurance policy detail 时会生成审计记录
- 审计日志中不存储原始 PHI 值

### HIPAA-02：Session Timeout + Token 生命周期

**问题：** 当前 JWT 有 8 小时有效期，没有 idle timeout，也没有 key rotation 机制。

**要求：**
- 15 分钟无操作自动登出
- 前端主动清除本地 token / session 状态
- Access token 使用短生命周期（15 分钟 TTL）
- Refresh token 使用长生命周期（7 天），并在服务端以 hash 形式保存
- `SECRET_KEY` 必须可轮换，且不会导致所有用户在中途被强制退出
- 轮换流程需文档化，任何 admin 都能执行

**验收标准：**
- UI 中空闲 15 分钟后自动登出
- 过期 access token 返回 `401`
- Refresh token 有效时，可刷新 access token 而无需立即重新登录
- 通过更新环境配置 + 重新部署可轮换 `SECRET_KEY`；重叠窗口内仍可验证有效 refresh token
- 轮换动作作为 `KEY_ROTATED` 事件写入审计日志
- 轮换后，用旧 key 签发的 access token 立即失效

### HIPAA-03：静态加密（字段级）

**问题：** 虽然托管基础设施已有磁盘加密，但部分高敏感字段在应用层仍然是明文。

**要求：**
- 使用 Fernet 对以下字段增加应用层加密：
  - `patients.date_of_birth`
  - `patients.phone`
  - `patients.address`
  - `insurance_policies.member_id`
- 需要明确加密字段的搜索 / 索引策略

**验收标准：**
- 没有应用密钥时，数据库中的这些字段不可读
- 授权用户在应用层可透明解密
- 密钥管理基于环境配置

### HIPAA-04：传输中加密

**问题：** 应用层尚未显式强制 transport security。

**要求：**
- 生产环境强制 HTTPS
- 增加 HSTS headers
- 在生产部署中拒绝不安全的 HTTP 请求

**验收标准：**
- 生产响应带有 HSTS
- HTTP 请求会被重定向或拒绝
- 本地开发仍可在无 HTTPS 环境下使用

## P1 — 第二个 Sprint

### HIPAA-05：最小必要访问（Minimum Necessary Access）

**问题：** 虽然已有角色检查，但字段级 PHI 暴露仍然比业务所需更宽。

**要求：**
- 按角色做字段级过滤

**目标访问模型：**
- `frontdesk`：
  - demographics
  - insurance
  - scheduling
  - checkout data
  - 不能看完整 clinical note 内容
- `doctor`：
  - clinical notes
  - visit history
  - treatments
  - 除 copay 场景外，不看不必要的 payment 细节
- `admin`：
  - 诊所全量访问

**验收标准：**
- frontdesk 的 note 列表不返回 note content / body
- doctor 的财务视图不返回不必要金额字段
- admin 可以查看完整记录

### HIPAA-07：唯一用户识别

**问题：** 系统概念上已经是实名用户，但还缺乏更强的 user-identification 控制。

**要求：**
- 禁止共享登录账户
- 在所定义的唯一性范围内禁止重复用户名
- 记录 `last_login_at`
- 对新建用户启用首次登录强制改密

**验收标准：**
- 新用户首次登录时必须改密
- 按所选唯一性规则拒绝重复用户名
- 登录成功时更新 `last_login_at`

### HIPAA-08：登录锁定

**问题：** 当前对重复失败登录没有基于账号的限制。

**要求：**
- 失败登录 5 次后锁定 15 分钟
- 使用 `failed_attempts` 和 `locked_until` 跟踪

**验收标准：**
- 连续 5 次密码错误后账号被锁定
- 锁定期间即使密码正确也返回 locked error
- 登录成功后清空失败次数

## P2 — 第三个 Sprint

### HIPAA-06：Break-Glass 紧急访问

**问题：** 系统尚未定义应急情况下的特殊越权访问流程。

**要求：**
- 仅 admin 可使用的 emergency override
- 必须填写 reason string
- 记录为 `BREAK_GLASS_ACCESS`
- 4 小时后自动失效

**验收标准：**
- 开启 break-glass 必须提供明确原因
- 所有 break-glass 使用都可审计
- 授权会自动过期

### HIPAA-09：事件日志完整性

**问题：** event log 虽然是 append-only，但尚未做加密哈希链。

**要求：**
- 增加 SHA-256 hash chaining：
  - `prev_hash`
  - `row_hash`
- 每日校验任务验证整条链

**验收标准：**
- 新事件写入时带有 hash chain 值
- 校验任务能发现篡改或缺失
- 完整性失败时发出告警事件

### HIPAA-10：Breach Detection + Notification

**问题：** 当前不会自动发现异常访问 / 导出行为。

**要求：**
- 检测：
  - 单次请求导出超过 50 条 patient records
  - 同一 IP 5 分钟内失败认证超过 3 次
- 通过邮件告警 admin
- 记录 `BREACH_ALERT`

**验收标准：**
- 触发条件会产生 alert event
- 会向 admin 发送邮件告警
- 告警可在内部审计轨迹中查看

---

## 8. 用户故事

- 作为合规负责人，我希望每次 PHI 访问都被记录，这样我能调查不当访问。
- 作为诊所经理，我希望空闲设备会自动登出，这样不会因为无人值守而暴露 PHI。
- 作为患者，我希望自己的敏感数据在静态和传输中都被保护。
- 作为前台，我希望只看到完成工作所需的 PHI，而不是看到过多不必要内容。
- 作为 admin，我希望 emergency override 只在必要时启用，并且全程留痕。

---

## 9. 功能性要求

1. 系统必须记录 PHI 的写入和读取。
2. 系统必须用已认证用户标识每次访问。
3. 系统必须支持 session 过期与 idle timeout。
4. 系统必须在生产环境强制 HTTPS。
5. 系统必须支持基于角色的字段过滤。
6. 系统必须支持重复失败登录后的锁定。
7. 系统必须支持首次登录强制改密流程。
8. 系统必须支持带有效期的 break-glass override。
9. 系统必须支持事件历史的加密完整性校验。
10. 系统必须支持自动化可疑行为告警。

---

## 10. 安全 / 合规约束

- 应用日志或 HTTP error messages 中不得包含 PHI 值
- PHI 读取审计记录不得保存原始 PHI body
- JWT、Fernet、邮件服务等 secrets 必须通过环境变量管理
- 加密密钥不得存储在 source control 中
- 本地开发模式可放宽 transport 约束，生产环境不允许
- `SECRET_KEY` 必须按环境唯一（local ≠ production）
- `SECRET_KEY` 至少按季度轮换；若疑似泄露，应立即轮换
- 轮换必须写入 `KEY_ROTATED` 审计事件
- 当前实现的登录标识为 `username`；是否迁移到 `email` 见 Open Question #1

---

## 11. Edge Cases

- 用户在一个浏览器 tab 活跃，但另一个 tab 长时间空闲
- UI 仍缓存 access token，但 refresh token 已过期
- frontdesk 查看 patient detail 时页面中嵌入了 clinical note 预览
- doctor 绑定了 staff 记录，却查看另一位医生的 notes
- break-glass session 跨越午夜或跨时区
- event-chain 校验任务运行时，系统仍有写入发生
- 合法的大批量导出触发了 export threshold

---

## 12. 成功指标

- 100% 的 PHI 读取路由纳入 audit logging
- 100% 的受保护路由都要求 authenticated user context
- 在 UI 行为测试中，空闲 session 15 分钟后过期
- 所有指定字段都开启字段级加密
- Lockout 与 breach alerts 均由自动化测试覆盖验证

---

## 13. 本 PRD 当前不包含

- enterprise SSO
- device management / MDM
- 应用边界之外的工作站磁盘加密
- 业务制度 / 培训文档
- 超出应用级告警之外的法律 incident response workflow

---

## 14. 发布计划

### Sprint 1
- HIPAA-01
- HIPAA-02
- HIPAA-03
- HIPAA-04

### Sprint 2
- HIPAA-05
- HIPAA-07
- HIPAA-08

### Sprint 3
- HIPAA-06
- HIPAA-09
- HIPAA-10

---

## 15. 待确认问题

1. 登录唯一标识是否继续使用 username，还是改成 email？（RFC-001 使用 email，而当前实现使用 username —— 必须在 HIPAA-07 前确认）
2. 首次登录改密是只对 admin 创建的用户生效，还是对所有新用户生效？
3. 哪些导出动作应计入 breach / export threshold？
4. Break-glass 只在 clinic 内适用，还是将来也适用于多诊所支持团队？
5. 生产环境使用哪个邮件服务发送 breach notifications？
6. HIPAA-02 落地后，access token 的目标 TTL 是多少？（建议 15 分钟，与 idle timeout 对齐）
7. 是否需要支持零停机 key rotation，使旧 key 与新 key 在重叠窗口内同时有效？（如果 refresh token TTL > 0 且轮换时仍有有效会话，则这是必须能力，参见 RFC-002 §6）
