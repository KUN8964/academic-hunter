# 🔬 Academic Hunter

科研情报聚合平台 — AI 驱动的论文追踪工具。像 Google Alerts 一样监控研究方向，像 Feedly 一样阅读每日简报。

**无需注册即可使用** — 填入你的 API Key，即刻体验 AI 研究分析。

## ✨ 功能

- 🔍 **智能主题扩展** — 用自然语言描述研究方向，AI 自动扩展关键词、推荐相关子领域和研究者
- 📊 **可信度评分** — 基于发表 venue、引用数的混合加权模型，自动区分高/中/低可信度论文
- 🇨🇳 **AI 中文摘要** — 每篇论文自动生成中文摘要和标签
- 📰 **每日简报** — 按可信度分层（高可信 / 中可信 / 待验证）的 Markdown 简报
- 👤 **研究者追踪** — 追踪指定学者的最新成果（支持 arXiv + Semantic Scholar）
- 🔑 **自带 API Key** — 支持 DeepSeek、OpenAI、Claude 等任何 OpenAI 兼容 API，按用户隔离

## 🚀 快速开始

### 方式一：直接使用（无需部署）

1. 准备一个 AI API Key（DeepSeek / OpenAI / 其他 OpenAI 兼容接口）
2. 打开前端页面
3. 填入 Key → 描述研究方向 → 查看 AI 分析结果

### 方式二：本地部署

```bash
# 1. 克隆仓库
git clone https://github.com/KUN8964/academic-hunter.git
cd academic-hunter

# 2. 配置环境变量
cp .env.example backend/.env
# 编辑 backend/.env，填入 DATABASE_URL 和 JWT_SECRET

# 3. 启动 PostgreSQL（需要 pgvector 扩展）
docker run -d --name pgvector \
  -e POSTGRES_USER=hunter \
  -e POSTGRES_PASSWORD=hunter \
  -e POSTGRES_DB=academic_hunter \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 4. 启动后端
cd backend
uv sync
uv run uvicorn src.main:app --reload --port 8000

# 5. 启动前端
cd ../frontend
npm install
npm run dev
```

打开 http://localhost:5173 即可使用。

## 🏗️ 架构

```
academic-hunter/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 环境变量配置（含校验）
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── models/models.py     # SQLAlchemy ORM 模型
│   │   ├── routers/
│   │   │   ├── auth.py          # 注册/登录/用户设置
│   │   │   ├── public.py        # 无需认证的公开接口
│   │   │   ├── subscriptions.py # 订阅管理 + onboarding
│   │   │   ├── papers.py        # 论文搜索与详情
│   │   │   └── pipeline.py      # Pipeline 触发 + 简报查询
│   │   ├── services/
│   │   │   ├── auth.py          # 密码哈希 + JWT
│   │   │   ├── auth_middleware.py # 认证依赖
│   │   │   ├── ai.py            # AI 服务（按用户配置）
│   │   │   ├── pipeline.py      # 论文采集→评分→简报流水线
│   │   │   └── subscriptions.py # 订阅 CRUD
│   │   └── scrapers/
│   │       ├── arxiv.py         # arXiv API
│   │       └── semantic_scholar.py # Semantic Scholar API
│   ├── tests/                   # 单元测试
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── HomeView.vue     # 首页（guest 模式入口）
│   │   │   ├── LoginView.vue
│   │   │   ├── RegisterView.vue
│   │   │   ├── OnboardingView.vue # 引导流程
│   │   │   ├── DashboardView.vue  # 控制台
│   │   │   ├── SettingsView.vue   # AI 模型设置（guest+登录）
│   │   │   └── ...
│   │   ├── stores/auth.ts       # 认证状态 + guest 模式
│   │   └── router/index.ts
│   └── package.json
└── .env.example
```

## 📡 API 概览

### 公开接口（无需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/public/onboarding/expand` | AI 扩展研究方向（接受 api_key 参数） |
| GET | `/health` | 健康检查 |

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册（限流 5/min） |
| POST | `/auth/login` | 登录（限流 10/min） |
| GET | `/auth/me` | 当前用户信息 |
| GET | `/auth/settings` | 获取 AI 设置（key 脱敏） |
| PUT | `/auth/settings` | 更新 AI 设置 |

### 订阅 & Pipeline

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/subscriptions/topics` | 领域订阅管理 |
| GET/POST | `/subscriptions/researchers` | 研究者订阅管理 |
| POST | `/subscriptions/onboarding/expand` | 引导流程 AI 扩展 |
| POST | `/pipeline/run` | 触发每日简报生成 |
| GET | `/pipeline/briefs` | 简报列表 |
| GET | `/papers?q=...` | 论文搜索 |
| GET | `/papers/{id}` | 论文详情 |

## 🧪 测试

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://localhost/test \
JWT_SECRET=test-secret-min-32-chars \
uv run pytest tests/ -v
```

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)
