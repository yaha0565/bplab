# BPLab Trace — 齿科检测实验室 LIMS 系统

前后端分离的实验室信息管理系统，专为齿科医疗器械 CMA 检测实验室设计。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI (Python 3.12+) + SQLAlchemy async + PostgreSQL |
| **前端** | Vue 3 (Composition API) + Element Plus + Vite |
| **认证** | JWT Bearer Token |
| **数据库** | PostgreSQL 14+ |
| **审计** | SHA-256 哈希链 + commission_no 全链路追踪 |

## 项目结构

```
bp-lims-main/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/             # API 路由 (24 个端点模块)
│   │   ├── core/               # 核心模块 (安全/审计/编码规则/实验模式)
│   │   ├── models/             # 数据模型
│   │   ├── schemas/            # Pydantic 验证模式
│   │   └── services/           # 业务服务 (Word 渲染/审计日志/预览)
│   ├── migrations/             # 数据库迁移脚本
│   ├── scripts/                # 种子数据脚本
│   └── tests/                  # 测试套件
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/              # 26 个页面组件
│   │   ├── components/         # 共享组件 (摄像头拍照等)
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # Pinia 状态管理
│   │   └── utils/              # 工具函数 (Axios 封装)
│   └── public/                 # 静态资源
├── templates/                  # DOCX 受控模板 (33 个)
│   ├── R001-R017_*.docx        # 原始记录模板 (14 种实验)
│   ├── SOP-001~017_*.docx      # 标准操作规程 (14 种)
│   └── FORM_*.docx             # 表单模板 (6 个通用表单)
├── data/                       # 运行时数据 (数据库/附件/签名/上传)
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 容器构建文件
└── CHANGELOG.md                # 变更记录
```

## 支持的实验类型 (14 项)

| 编号 | 实验名称 | 标准 |
|------|----------|------|
| I001 | 表面粗糙度试验 | YY/T 1702-2020 |
| I002 | 金属-陶瓷结合裂纹萌生试验 | YY 0621.1-2016 |
| I003 | 金属内部质量X射线灰度分析 | GB 17168-2013 |
| I004 | 翘曲变形试验 | YY/T 1702-2020 |
| I005 | 热膨胀系数试验 | YY 0621.1-2016 |
| I006 | 陶瓷牙耐急冷急热试验 | YY 0300-2009 |
| I007 | 弯曲性能试验 | YY/T 1702-2020 |
| I008 | 维氏硬度试验 | GB/T 4340.1-2024 |
| I009 | 增材制造金属试样厚度测量 | YY/T 1702-2020 |
| I010 | 牙科材料色稳定性试验 | YY 0710-2009 |
| I011 | 定制式固定义齿检验 | GB 17168-2013 |
| I012 | 定制式活动义齿检验 | GB 17168-2013 |
| I013 | 激光选区熔化金属材料密度试验 | YY/T 1702-2020 |
| I014 | 金属材料抗晦暗性能试验 | YY 0710-2009 |

## 用户角色

| 角色 | 权限 |
|------|------|
| **管理员** | 系统配置、用户管理、全部操作 |
| **样品管理员** | 委托创建、样品管理、任务分配 |
| **实验员** | 实验执行、拍照取证、提交复核 |
| **复核员** | 原始记录复核、退回/通过 |
| **质量负责人** | 报告审核、质量批准、报告签发/撤回 |

## 核心功能

### 业务流程
- **委托管理**: 委托单创建 → 样品组登记 → 任务包分配
- **实验执行**: 任务接收 → 模板表单填写 → 拍照取证 → 提交复核
- **复核流程**: 记录复核（通过/退回）→ 自动生成报告
- **报告管理**: 质量审核 → 批准签发 → 发放登记 → 撤回/作废
- **审计追踪**: 全链路 SHA-256 哈希链，按委托号追溯所有操作
- **DOCX 导出**: 受控模板引擎，填写实验数据到 Word 原始记录表和报告

### 单据中心
- 7 种单据: 原始记录 / 委托单 / 样品登记 / 借出归还 / 危废处置 / 检验报告 / 发放登记
- 在线预览 (iframe srcdoc) + Blob 下载
- 一键下载: 按委托号打包所有关联文档

### 审计追踪
- 按委托号查询完整操作时间线
- 颜色区分操作类型 (创建/修改/审核/批准/撤回等)
- 哈希链完整性验证
- 字段级修改日志

## 快速启动

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### 开发环境

```bash
# 1. 后端
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env  # 编辑数据库配置
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. 前端
cd frontend
npm install
npm run dev

# 3. 访问
# 前端: http://localhost:5173
# 后端 API 文档: http://localhost:8000/docs
# 默认账号: admin / admin123
```

### Docker 部署

```bash
docker-compose up -d --build
docker-compose exec backend python scripts/seed_v10.py
```

## API 端点概要

| 类别 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth/*` | 登录/登出/修改密码 |
| 委托 | `/api/v1/commissions/*` | 创建委托、样品组管理 |
| 任务 | `/api/v1/tasks/*` | 任务包创建/接收/时间标记 |
| 原始记录 | `/api/v1/records/*` | 保存/提交/复核/DOCX导出 |
| 报告 | `/api/v1/reports/*` | 生成/审核/批准/发放/撤回 |
| 导出 | `/api/v1/export/*` | Word 模板填充导出 |
| 审计追踪 | `/api/v1/traceability/*` | 审计日志/修改记录/哈希验证 |
| 实验配置 | `/api/v1/config/*` | 字段/列/拍照节点/设备绑定 |
| 设备 | `/api/v1/equipment/*` | 设备库管理 |
| 样品资料 | `/api/v1/catalog/*` | 检测项目资料库 |
| 模板 | `/api/v1/templates/*` | DOCX 模板管理 |
| 签名 | `/api/v1/signatures/*` | 电子签名上传/管理 |
| 通知 | `/api/v1/notifications/*` | 消息通知 |
| 系统 | `/api/v1/system/*` | 健康检查/初始化 |

完整 API 文档见 `http://localhost:8000/docs`

## 变更记录

详见 [CHANGELOG.md](CHANGELOG.md)

## 许可证

内部使用 — BPLab Trace © 2026
