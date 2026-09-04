# Mandol-AML：Agent Memory Challenge（AML）接入适配层

Mandol-AML 是课题组基于 [Mandol](https://github.com/AgentCombo/Mandol)
（论文 [arXiv:2606.29778](https://arxiv.org/abs/2606.29778)）参加
**Agent Memory Challenge（AML，智能体记忆公开挑战赛）** 的接入封装：

- **不改动 Mandol 主体**：本目录对上游仓库是**纯增量**（只新增文件，不修改
  `src/mandol/` 任何代码、不修改 `pyproject.toml` 与 `uv.lock`）。
- **只暴露赛事要求的两个接口**：`Add`（记忆写入）与 `Search`（记忆检索），
  另提供未鉴权的 `Health`。回答、评分、编排全部由 AML 平台完成。
- 面向赛道：**文本记忆赛道**与**代码记忆赛道**，参赛组别：**开源方法榜（学术榜）**。

> 平台接口文档：<https://agentmemoryleaderboard.ai/api-guide>
> 参赛说明：<https://agentmemoryleaderboard.ai/rules>
> 报名入口：<https://agentmemoryleaderboard.ai/evaluation>

---

## 1. 目录结构（叠加到 Mandol fork 根目录后）

```
<fork 根目录>
├── src/mandol_aml/        # 新增：AML 适配包（FastAPI Add/Search/Health）
│   ├── app.py             # FastAPI 应用：/add /search /health
│   ├── memory.py          # 基于 SemanticMap/SemanticGraph 的按 user_id 记忆服务
│   ├── schemas.py         # AML 契约字段模型（请求/响应校验）
│   ├── config.py          # AML_* 环境变量配置
│   ├── security.py        # Memory System Key 鉴权（Token/Bearer/X-Api-Key）
│   ├── ratelimit.py       # 进程内限流（RPM）
│   ├── retention.py       # 30 天数据留存清理（合规）
│   ├── high_level.py      # 可选实验性高层记忆（默认关闭）
│   └── __main__.py        # python -m mandol_aml 启动入口
├── Dockerfile             # 新增：在 fork 根目录构建的镜像
├── docker-compose.yml     # 新增
├── .dockerignore          # 新增
├── aml.env.example        # 新增：服务配置模板
├── aml/                   # 新增：说明与参赛材料
│   ├── README.md          # 本文档
│   ├── CHANGES.md         # 相对上游的改动披露（赛事合规必需）
│   ├── ATTRIBUTION.md     # 原始方法/作者/论文/许可证声明
│   ├── scripts/smoke_test.py
│   └── docs/              # 报名与提交材料（填写后提交）
└── tests/test_contract.py # 新增：契约字段单元测试
```

---

## 2. 快速开始（本地）

前置：Python 3.12、[uv](https://docs.astral.sh/uv/)、可访问
Hugging Face（首次会下载默认 embedding 模型 `Qwen/Qwen3-Embedding-0.6B`）。

```bash
# 在 fork 根目录（已包含本 overlay 的文件）执行
uv sync --frozen --no-dev            # 安装 Mandol 运行时依赖
cp aml.env.example .env              # 按需修改（如 AML_MEMORY_SYSTEM_KEY）

export $(grep -v '^#' .env | xargs)  # 或使用 dotenv 加载
python -m mandol_aml                 # 默认 0.0.0.0:8000
```

另开终端运行本地冒烟测试：

```bash
python aml/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

`smoke_test.py` 按 AML 契约依次检查：`/health` 就绪 → `Add` 返回 200 且
`success=true`、三个 ID 逐字回显 → `Search` 返回 `data` 数组、字段齐全、数量
不超过 `top_k`。

运行契约单元测试（无需 GPU/模型）：

```bash
pytest tests/test_contract.py -v
```

## 3. Docker 运行（fork 根目录）

```bash
docker build -t mandol-aml:0.1.0-aml.1 .
# 或
docker compose up -d --build
```

> 镜像较大（Mandol 固定 torch 2.8.0）。首次启动会下载 embedding 模型，
> `/health` 在就绪前返回 503，就绪后返回 200。

## 4. AML 契约符合性

| 项 | 实现 |
| --- | --- |
| Add 请求 | `POST /add`；`request_id/messages/user_id/session_id`，`role/content/timestamp` |
| Add 响应 | 数据**落盘并立即可检索后**才返回 `HTTP 200`；`{"success":true, request_id, user_id, session_id}` 逐字回显 |
| Search 请求 | `POST /search`；`query/options?/user_id/top_k` |
| Search 响应 | `{"data":[{id, content, score?, created_at?}]}`，按相关度降序，数量 ≤ `top_k` |
| 隔离 | `user_id` 是唯一检索边界；`session_id` 仅作元数据；绝不跨 `user_id` 检索 |
| 鉴权 | `Token` / `Bearer` / `X-Api-Key`（配置 `AML_MEMORY_SYSTEM_KEY` 后强制） |
| 错误 | 401/403/404/408/425/429/500/502/503/504 等标准语义，业务错误体 `{"detail":{"reason":...}}` |
| 数据留存 | 默认 30 天自动清理（`AML_DATA_TTL_DAYS=30`） |
| 隐私 | 日志不含消息正文；仅记录 request/user/耗时/数量级信息 |

## 5. 关键配置

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AML_MEMORY_SYSTEM_KEY` | 空 | 正式评测前务必设置 |
| `AML_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | 也可用 `BAAI/bge-m3`、`all-MiniLM-L6-v2` |
| `AML_BACKEND` | `shared` | `shared`=单图+按用户空间隔离（省内存，稠密检索）；`isolated`=每用户一图（可用混合检索/高层记忆） |
| `AML_RETRIEVAL_MODE` | `graph` | `isolated` 后端可选 `hybrid`（cosine+bm25[+splade]） |
| `AML_GENERATE_SPARSE_EMBEDDING` | `false` | 开启 SPLADE 稀疏向量（写更慢，混合检索更准） |
| `AML_RATE_LIMIT_RPM` | `0`（不限） | 对外宣称的限流 |
| `AML_DATA_TTL_DAYS` | `30` | 赛事合规留存期 |
| `AML_HIGH_LEVEL_MEMORY` | `false` | 实验性：用 Mandol auto_builder 构建分层/情景/实体高层记忆（需 LLM Key，建议 `isolated` 后端，先自测） |

## 6. 容量 / 超时 / 限流建议（提交时需填写）

- **建议实例**：8 vCPU / 16–32 GB 内存；检索以 CPU 即可，稠密编码可用 GPU 加速。
- **写入吞吐**：稠密模式（`shared` + `graph`）单实例可持续 ≥ 10 QPS；
  批量 Add（一条请求多条消息）更快。
- **超时**：Add 默认 60 s、Search 默认 30 s（`AML_*_TIMEOUT_SECONDS`）。
- **限流**：默认不设限；如需设限使用 `AML_RATE_LIMIT_RPM`，并在报名表如实填写。
- 单个进程默认内存驻留；超大语料可开启 RocksDB 分级存储（`AML_L2_DIR`）。

## 7. 接入与正式评测流程

1. 9/20 起在 <https://agentmemoryleaderboard.ai/evaluation> 提交报名（开源方法榜）。
2. 部署公网 HTTPS 接口，配置 Key；保证 2026-09-20 至 11-04 稳定可用。
3. 用平台 Smoke 检查 Add/Search/鉴权链路（也可先用本仓库 `smoke_test.py`）。
4. Smoke 通过后在 Evaluation 页面发起 Full 正式评测（每 3 个月配额 1 次，先核对 8 项检查清单）。
5. 通过资格与合规复核后进入公榜。

## 8. 已知边界与后续优化

- 默认路径为「共享语义图 + 按用户空间隔离 + 稠密检索」，稳定且省内存；
  该路径不启用 Mandol 的 LLM 高层记忆。
- 追求更高分数的可选项（需在自有环境先冒烟验证）：
  `isolated` 后端 + `hybrid`（BM25/SPLADE 需安装上游 `spacy-model` 依赖组），
  以及实验性 `AML_HIGH_LEVEL_MEMORY=1` 高层记忆。
- 评测数据只用于当次任务，30 天内删除；禁止用于训练、微调或对外传播。
