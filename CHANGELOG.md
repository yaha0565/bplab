# BPLab Trace — 变更记录 (CHANGELOG)

所有对项目的重要变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [V11.2] — 2026-08-11

### 🔧 修复 — 关键问题

- **原始记录 DOCX 模板引擎重写** (`record_template_engine.py`):
  - `build_context_values` 从实际 payload 结构读取数据 (`_template_fields`、`_form`、`_rows`、`_equipment_checks`)
  - 支持测量数据行按列标题映射（试样编号、粗糙度、孔隙率、结论等）
  - 修复 checkbox 选择逻辑：不再将"不符合"误选为"符合"（否定词检测）
  - 新增 `_fill_measurement_rows_v2` 替代旧版测量行填充
  - 记录下载现包含：任务编号、样品编号、设备管理编号、操作员/复核员、日期
- **检验报告导出修复** (`export.py`):
  - 修复 SQL 错误：`client_org` 不存在 → JOIN `organizations` 表获取 `org_name`
  - 修复数据来源：样品信息从 `sample_groups` 表查询（`commissions` 表无 `sample_name` 等列）
  - 重写填充逻辑：按中文标签匹配段落（"报告编号："、"委 托 单 位："等）
  - 填写设备表、环境表（温湿度）、检测项目表
- **报告发放登记下载修复**: `Content-Disposition` 中文文件名导致 UnicodeEncodeError → 全部改为 ASCII
- **DOCX 下载返回 JSON 修复**: 模板文件未找到时改为通用 DOCX 生成（不再降级为 JSON）

### ✨ 新增 — 审计追踪

- **全系统审计日志接入** — 所有写操作按委托号 (`commission_no`) 记录：
  | 模块 | 记录的操作 |
  |------|-----------|
  | `commissions.py` | 创建委托、创建样品组 |
  | `tasks.py` | 创建任务包、接收任务包、标记实验时间 |
  | `records.py` | 保存草稿/提交复核、复核通过、复核退回 |
  | `reports.py` | 生成报告、质量审核、批准签发、发放、撤回、作废、更正（9项） |
  | `signatures.py` | 上传签名、删除签名 |
  | `users.py` | 创建用户、重置密码、修改角色、删除用户 |
  | `hazardous_waste.py` | 登记危废 |
- **哈希链审计日志** (`audit_service.py`): 统一服务，SHA-256 哈希链，同步写入 `audit_logs` + `modification_logs` + `report_actions`
- **审计追踪 API** (`traceability.py`): 支持按委托号查询、按实体过滤、修改记录管理

### 🏗 前端增强

- **单据中心** (`DocumentCenter.vue`): 完整重写，支持 7 种单据类型查询、iframe srcdoc 预览、Blob 下载
- **一键下载** (`BatchDownload.vue`): 完整重写，显示 4 类通用表单 + 原始记录 + 检验报告 + 报告发放登记，勾选批量下载
- **审计追踪** (`AuditTrail.vue`): 按委托号输入，时间线展示所有操作，颜色区分操作类型
- **报告发放管理** (`ReportDelivery.vue`): 已发布报告只保留撤回按钮，撤回增加原因对话框
- 所有前端文件编译为纯 JavaScript（移除 TypeScript 类型注解）

### 🔒 权限改进

- 单据下载/预览权限扩展：`复核员` 和 `实验员` 加入允许角色（原仅 `质量负责人、管理员、样品管理员`）
- 报告撤回权限扩展：新增 `质量负责人` 角色（原仅 `管理员`）

### 🗺 模板配置

- 33 个 DOCX 受控模板：R001-R017 原始记录表 + SOP-001~017 标准操作规程 + 6 个 FORM 表单
- 模板引擎支持全角/半角空白标记、中文日期格式、checkbox 选择框、测量数据表

---

## [V11.1] — 2026-08-11

### 🔧 修复 — 关键问题

- **记录复核 500 错误修复** (`records.py`):
  - 修复 `reports` 表 INSERT 中引用不存在的 `experiment` 列
  - 修复 `records` 表 INSERT 中引用不存在的 `report_summary`、`report_conclusion`、`tester_self_check` 列，改为合并到 `payload` JSONB 字段
  - 修复 `source_versions` 类型不匹配（`CAST AS jsonb` → TEXT）
  - 清理死代码和不存在列的 SELECT 语句
- **I011/I012 设备绑定修复**: 修正实验名称（去除"综合"），使 `experiment_methods` 与 `experiment_equipment_bindings` 名称匹配
- **I011/I012 拍照节点 Key 修正**: `_EXPERIMENT_PHOTO_CHECKPOINTS` 中 key 名称同步更新

### ✨ 新增 — 功能完善

- **拍照时间戳**: `CameraCapture.vue` 拍照时在右下角叠加半透明时间戳水印（Canvas 2D 渲染）
- **数据隔离**: 实验执行页按 task 做数据隔离，切换任务时完全重置表单状态
- **提交强制校验**: 必填项未填或必拍照点未拍照时禁止提交，弹窗提示缺失项列表
- **日期/时间字段**: 日期字段自动填入当日，时间字段改为按钮调用系统时间

### 🗺 模板配置补全

- `_KIND_TO_TEMPLATE_CODE` 新增 `density: R016`、`tarnish: R017`
- `KIND_TO_TEMPLATE`、`RECORD_TEMPLATE_CODES` 新增 R016/R017
- `_KIND_MAP` (record_word_engine.py) 新增 density/tarnish
- `seed_v10.py` 新增 I010 到配置版本创建循环，修正 I011/I012 名称

### 🧹 项目清理

- 删除冗余模板文件（RECORD_R*、SOP_R* 英文命名重复项，保留中文命名模板）
- 删除 `资料/` 参考数据文件夹
- 移动 `experiment_schemas.py` 到 `backend/app/core/`
- 更新 `.gitignore`

### 📊 验证

- 全部 14 个实验配置 API 通过：字段、列、拍照节点、设备绑定、模板文件均正常

---

## [V11.0] — 2026-08-09

### 🏗 重大变更 — 前端架构升级

- **Vue 3 + Vite + Element Plus** 前端完整实现（26个页面）
- 前后端分离架构：FastAPI 后端 + Vite SPA 前端
- 分组菜单导航（工作台 / 业务与追溯 / 基础配置 / 系统管理）
- JWT Bearer Token 认证 + 路由守卫

### ✨ 新增 — 核心功能对齐

#### 任务包委托绑定增强
- `POST /tasks/packages` 创建任务包时强化委托绑定：
  - 验证委托存在且未作废（返回 400 vs 404）
  - 写入 `assigned_by`（分配人=当前操作用户）
  - 写入 `assigned_at`（分配时间）
  - 写入 `experiment_codes`（实验编码列表）
  - 返回结果包含 `assigned_by`
- `GET /tasks/packages` 列表返回 `assigned_by` 字段
- 前端 `TaskPackages.vue` 列表新增「分配人」列
- 前端 `TaskPackageDetail.vue` 详情页展示委托编号绑定

#### 实验配置版本管理
- `POST /config/{code}/versions` — 创建配置版本（含字段/列/拍照节点/预检查/验证规则/设备绑定子表）
- `PUT /config/{code}/versions/{v}` — 更新草稿版本（字段级替换）
- `PUT /config/{code}/versions/{v}/status` — 激活现行 / 归档历史
- `DELETE /config/{code}/versions/{v}` — 删除草稿版本
- 前端 `ExperimentMethods.vue` 新增版本管理对话框

#### SOP与模板版本管理
- `POST /templates/upload` — 上传新模板（multipart，拒绝重复文件名）
- `DELETE /templates/{filename}` — 删除模板文件
- `PUT /templates/{filename}/rename` — 重命名模板文件
- 修复 `TEMPLATE_DIR` 路径（相对→绝对），30个模板文件正常显示
- 前端 `Templates.vue` 新增上传/删除/重命名功能

#### 用户管理增强
- `DELETE /users/{username}` — 管理员删除用户（不可删除自己，自动解除任务包分配）
- `PUT /users/{username}/role` — 管理员修改用户角色
- 前端 `Users.vue` 新增删除按钮和角色修改按钮

#### 电子签名管理
- `GET /signatures` — 列出所有用户签名状态
- `POST /signatures/upload` — 管理员上传签名图片（PNG/JPG）
- `GET /signatures/{username}.png` — 获取签名图片
- `DELETE /signatures/{username}` — 删除签名
- 前端 `Signatures.vue` 签名预览/上传/删除

#### 修改中心
- 前端 `ModificationCenter.vue` — 按实体类型/操作人筛选修改日志
- 展示：谁/何时/改了什么/旧值/新值/原因
- 后端 `GET /traceability/modifications` 已支持（原有）

#### 系统初始化
- `GET /system/health` — 系统健康检查（DB连接 + 表行数统计）
- `POST /system/initialize` — 二次确认后清空业务数据保留基础数据
- 前端 `SystemInit.vue` — 健康仪表盘 + 初始化操作

### 🔧 修复 — 关键问题

- **实验执行页空白/卡死**: `GET /config/{experiment_code}` 在无 DB 配置版本时仅返回 `{message}` 不包含字段/列/拍照数据，导致 ExperimentRun 页空白。
  - 后端：端点自动回退到 `experiment_schemas.py` 硬编码 schema（按 `kind` 查找，如 `I001`→`rough`→51字段/12列/4拍照节点）
  - 后端：DB 字段名统一标准化映射（`field_key`→`key`, `field_label`→`label` 等）
  - 后端：新增 `GET /config/{code}/versions/{version}` — 加载任意历史版本，空版本自动回退硬编码模板
  - 拍照节点补齐：8 个通用节点 + 12 种实验专属节点，覆盖全部 13 种实验类型
  - 前端：空配置检测 — API 返回无 `fields` 且无 `columns` 时 `config.value = null`，显示 `<el-empty>` 而非空白表单
- **摄像头组件**: 新增 `CameraCapture.vue` — `getUserMedia()` API 实时预览+拍照，支持前后摄像头切换（PC 默认前置，手机默认后置），`enumerateDevices()` 自动检测设备方向，拍照失败时提供文件上传回退
- 修复 `task_packages`/`tasks` INSERT 缺少 `group_id`（NOT NULL 列）
- 修复 `sample_groups` INSERT 引用了不存在的列
- 修复 `catalog` POST JSONB 参数编码（`CAST(:ec AS jsonb)` + `json.dumps()`）
- 修复 `TEMPLATE_DIR` 从相对路径改为绝对路径
- 修复重复 task_no（切换为 `{package_no}-T{seq}` 格式）
- 修复测试套件 async→sync 转换（Python 3.14 兼容）
- 修复 FastAPI 参数顺序问题（`Form` 参数需在有默认值的参数之后）
- 修复"实验配置版本"菜单错误跳转到 `/templates`（应指向 `/methods`）

### 🖥 前端功能补齐

- **检测项目与方法库**: 新增"新增检测项目"按钮+对话框 + 删除按钮（管理员/样品管理员）
- **样品资料库**: 新增"新增样品资料"按钮+对话框 + 删除按钮（管理员/样品管理员）
- **设备库**: 新增"新增设备"按钮+对话框 + 删除按钮（管理员/样品管理员）
- **单位信息库**: 新增删除按钮
- **实验执行页**: 全新 `ExperimentRun.vue` — 动态表单（从实验配置加载字段/测量列/拍照节点）+ 保存草稿/提交复核（实验员专属路由 `/experiment/:taskNo`）
- **摄像头拍照组件**: `CameraCapture.vue` — 支持前后摄像头切换、PC/移动端自动识别默认方向、实时预览拍照、Canvas 截图导出、文件上传回退
- **首页看板**: 按角色展示不同统计卡片和快捷操作
- **任务包管理**: 「新建任务包」按钮仅管理员/样品管理员可见；表单两级级联选择（先选委托→展示委托方→再选样品组）；实验员可「接收」分配给自己的待接收任务包
- **我的实验任务**: 重构为实验员工作台 — 顶部统计卡片(待接收/检测中/已完成) + 状态分Tab + 「开始实验」「结束实验」操作按钮
- **任务详情**: 新增开始实验/结束实验操作按钮 + 时间线可视化（创建→开始→结束）
- **新建委托**: 支持创建委托时同步添加样品组（材料名称/数量/检测项目/批号/炉号），一委托多样品组多检测项目的层级关系
- **菜单权限**: 管理员新增"电子签名""修改中心""系统初始化"菜单项；样品管理员新增"检测项目与方法库""设备库"菜单项

### 🔗 后端 API 补齐

- `POST /methods` — 新增检测项目端点（管理员/样品管理员）
- `DELETE /methods/{experiment_code}` — 删除检测项目（软删除）
- `DELETE /catalog/{catalog_id}` — 删除样品资料（软删除）
- `DELETE /equipment/{management_no}` — 删除设备（软删除）
- `DELETE /organizations/{org_id}` — 删除单位（软删除）

### 🧪 测试

- **167 passed, 5 skipped, 0 failed** — 零回归

### 📝 变更的文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/api/v1/experiment_config.py` | 修改 | 新增创建/更新/激活/删除配置版本端点 |
| `backend/app/api/v1/templates.py` | 修改 | 新增上传/删除/重命名端点 |
| `backend/app/api/v1/users.py` | 修改 | 新增删除用户/修改角色端点 |
| `backend/app/api/v1/signatures.py` | 新建 | 电子签名管理 API |
| `backend/app/api/v1/system.py` | 新建 | 系统初始化 API |
| `backend/app/config.py` | 修改 | TEMPLATE_DIR 绝对路径修正 |
| `frontend/src/views/ExperimentMethods.vue` | 修改 | 版本管理对话框 |
| `frontend/src/views/Templates.vue` | 修改 | 上传/删除/重命名 |
| `frontend/src/views/Users.vue` | 修改 | 删除用户/改角色 |
| `frontend/src/views/Signatures.vue` | 新建 | 电子签名管理 |
| `frontend/src/views/ModificationCenter.vue` | 新建 | 修改中心 |
| `frontend/src/views/SystemInit.vue` | 新建 | 系统初始化 |
| `frontend/src/views/Layout.vue` | 修改 | 新增菜单项 |
| `frontend/src/views/ExperimentRun.vue` | 新建 | 实验执行页（动态表单+测量表+拍照+保存/提交） |
| `frontend/src/components/CameraCapture.vue` | 新建 | 摄像头拍照组件（前后切换+PC/移动端+文件回退） |
| `frontend/src/views/MyTasks.vue` | 修改 | 新增「去实验」按钮链接到实验执行页 |
| `frontend/src/views/TaskDetail.vue` | 修改 | 新增「去实验」按钮链接到实验执行页 |
| `frontend/src/router/index.js` | 修改 | 新增 `/experiment/:taskNo` 路由 |

---

## [V10.0] — 2026-08-07

### 🔒 新增 — 安全加固（生产就绪）

#### 登录暴力破解防护
- 新增 `login_attempts` 数据库表，追踪每次登录尝试（成功/失败）
- `authenticate()` 现在强制执行 `MAX_LOGIN_ATTEMPTS`（默认 5 次）
- 连续失败 `MAX_LOGIN_ATTEMPTS` 次后，账户被临时锁定 `LOGIN_LOCKOUT_MINUTES` 分钟（默认 15 分钟）
- 新增 `reset_login_attempts()` 函数供管理员手动解锁
- 新增配置项：`LOGIN_LOCKOUT_MINUTES`

#### 密码复杂度策略
- 新增 `_validate_password_strength()` 函数
- 密码最小长度：`PASSWORD_MIN_LENGTH`（默认 8 个字符）
- 必须包含至少一个数字 + 一个字母
- 拒绝常见弱密码（admin123, password, 12345678 等）
- 新增 `PasswordValidationError` 异常类
- `add_user()` 创建用户时强制执行密码强度检查

#### 密码修改功能
- 新增 `change_password(username, old_password, new_password)` 函数
- 新增 `admin_reset_password(admin, target, new_password)` 函数
- 新增"修改密码"页面（所有角色可访问）
- 侧边栏新增"🔒 修改密码"快捷入口
- 密码修改后自动使所有旧会话失效

#### 会话安全增强
- 新增 `last_activity_at` 列到 `sessions` 表
- 新增 `touch_session()` 函数，每次请求更新活跃时间
- 会话不活跃超时：`SESSION_INACTIVITY_TIMEOUT_MINUTES`（默认 1440 分钟 = 24 小时）
- `session_user()` 同时检查过期时间和不活跃超时
- 移除了 URL query param 传递 session token 的遗留代码（安全提升）
- 新增 `list_active_sessions()` 和 `terminate_session()` 函数
- 新增 `cleanup_expired_sessions()` 函数（启动时自动执行）
- 新增 `invalidate_user_sessions()` 函数（密码修改时调用）

#### 配置安全加固
- `DEMO_MODE` 默认值从 `true` 改为 `false` — 生产环境默认安全
- DEMO_MODE 启用时在登录页和侧边栏显示醒目警告横幅
- 启动时自动检查 SECRET_KEY、DEMO_MODE 和 BPLAB_PRODUCTION 配置
- 新增 `BPLAB_PRODUCTION` 环境变量支持

### 🗄 新增 — 数据库管理功能

#### 数据库健康检查
- 新增 `db_health_check()` 函数
- 返回数据库大小、WAL 大小、每表行数、完整性检查、外键检查
- 新增管理员"数据库管理"页面，含健康仪表盘

#### 数据库备份与恢复
- 新增 `backup_database()` — 使用 SQLite online backup API（保证一致性）
- 新增 `restore_database()` — 恢复前自动备份当前数据库
- 新增 `list_backups()` — 列出所有备份文件
- 新增 `export_table_csv()` — 导出任意表为 CSV

#### 数据库维护
- 新增 `db_maintenance()` — 支持 optimize / vacuum / checkpoint
- 管理页面提供一键 VACUUM、WAL Checkpoint、PRAGMA optimize

#### 活跃会话监控
- 管理员"用户与权限"页面新增活跃会话列表
- 显示用户名、角色、登录时间、最后活动、空闲时间
- 一键清理过期会话

### 🔧 修复 — 功能问题

#### 错误处理加固
- 修复 app.py 中多个 `next()` 调用缺少默认值导致的潜在崩溃
- 修复 `experiment_engine.py` 中 `except Exception: pass` 静默吞异常问题（改为记录日志）

#### 审计日志改进
- 新增 `audit_logs_paginated()` 函数，支持分页和过滤查询（实体类型、操作人、操作类型、日期范围）

#### DOCX 预览
- 改进 LibreOffice 进程搜索路径

### 🧪 新增 — 测试覆盖

- 新建 `tests/test_security.py` — 29 个安全测试
  - 暴力破解防护（7 个测试）
  - 密码复杂度验证（6 个测试）
  - 密码修改流程（5 个测试）
  - 管理员密码重置（3 个测试）
  - 会话安全（6 个测试）
  - 演示模式安全（2 个测试）
- 新建 `tests/test_database.py` — 20 个数据库测试
  - 健康检查（5 个测试）
  - 维护操作（4 个测试）
  - 备份恢复（4 个测试）
  - 数据导出（2 个测试）
  - 并发访问（2 个测试）
  - 系统初始化（2 个测试）

### 📝 变更的文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `lims_db.py` | 修改 | 新增 20+ 函数，修改 authenticate/create_session/session_user 等 |
| `app.py` | 修改 | 新增密码修改页、数据库管理页、会话监控；修复 next() 调用；会话安全 |
| `config.py` | 修改 | 新增 5 个配置项；DEMO_MODE 默认 false |
| `constants.py` | 修改 | 新增"修改密码"和"数据库管理"菜单项 |
| `experiment_engine.py` | 修改 | 修复静默异常吞没 |
| `tests/test_security.py` | 新建 | 安全测试套件（29 个测试） |
| `tests/test_database.py` | 新建 | 数据库测试套件（20 个测试） |
| `tests/test_bplab_suite.py` | 修改 | 适配 sessions 表新列和密码复杂度 |
| `CHANGELOG.md` | 新建 | 本文档 |

---

## [V9.3] — 2026-08-05（基准版本）

### 初始记录
- Streamlit LIMS 系统，支持 10 种实验类型
- 5 种用户角色：管理员、样品管理员、实验员、复核员、质量负责人
- SQLite 数据库（WAL 模式），26 张业务表
- PBKDF2-SHA256 密码哈希（240,000 次迭代）
- DOCX 受控模板预览（LibreOffice + PyMuPDF）
- 移动摄像头现场拍照（水印）
- 哈希链式审计追踪（SHA-256）
- 三级报告审批流程
- 88 项设备目录
- 26 个受控 DOCX 模板

### 已知 3 个 commits
1. 初始提交（yaha0565/bplab master）
2. V9.3 版本发布
3. Windows 兼容性修复（LibreOffice 路径搜索、临时文件清理）

---

> **变更记录规范**：每次对项目进行代码修改、配置变更、流程调整或新增功能后，请在本文件顶部添加新版本条目。
> 格式：`## [VX.Y] — YYYY-MM-DD`，包含"新增/修复/变更/移除"分类。
