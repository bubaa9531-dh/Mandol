# 改动披露（Change Disclosure）

> 赛事合规要求：复用他人论文/仓库/代码时，必须注明原作者、技术报告与许可证，
> 并写清本次做了哪些改动。本文档即为此而设。

## 上游来源

- 仓库：<https://github.com/AgentCombo/Mandol>
- 论文：Mandol: An Agglomerative Agent Memory System for Long-Term Conversations
  （<https://arxiv.org/abs/2606.29778>）
- 作者 / 维护团队：Mandol Team（AgentCombo）
- 许可证：Apache-2.0（见上游 LICENSE）
- 本 fork 基于的上游提交：`main` 分支（固定 commit：**[待填写，创建 fork 后记录]**，
  对应 Mandol PyPI 版本 0.1.0，Python 3.12）

## 本次改动清单（相对上游 main）

**原则：不改动上游任何既有文件，全部为新增文件；Mandol 核心（`src/mandol/`）、
`pyproject.toml`、`uv.lock` 均保持不变。**

| 新增文件 | 作用 | 是否影响 Mandol 核心 |
| --- | --- | --- |
| `src/mandol_aml/*` | AML Add/Search/Health HTTP 适配层（FastAPI） | 否，仅调用 Mandol 公共 API |
| `Dockerfile`、`docker-compose.yml`、`.dockerignore` | 服务容器化 | 否 |
| `aml.env.example` | 适配层环境变量模板 | 否 |
| `aml/README.md`、`aml/CHANGES.md`、`aml/ATTRIBUTION.md`、`aml/docs/*` | 文档与参赛材料 | 否 |
| `aml/scripts/smoke_test.py` | 按 AML 契约的本地冒烟客户端 | 否 |
| `tests/test_contract.py`、`tests/conftest.py` | 契约字段单元测试 | 否（上游 tests/ 无同名文件） |

### 行为说明

1. `Add`：将赛事下发的消息块转换为 Mandol `MemoryUnit`（`text_content` 保存正文，
   `role/timestamp/user_id/session_id/request_id` 存入元数据），经
   `SemanticGraph.batch_add_units()` 写入；**同步**返回 200（数据立即可检索）。
2. 隔离：`user_id` 是唯一检索边界。默认 `shared` 后端为每个 `user_id` 在共享
   `SemanticGraph` 内建独立 `MemorySpace`，检索限定在该空间内，杜绝跨用户泄漏；
   `isolated` 后端为每个 `user_id` 单独建图（模型权重仍经 Mandol 模型管理器共享）。
3. `Search`：默认使用 `SemanticGraph.search_similarity_in_graph()`（稠密检索，
   按空间/用户限定）；可选 `isolated` 后端 + `MultiRetriever.smart_search()`
   混合检索。返回按相关度降序的 `{id, content, score?, created_at?}`。
4. 高层记忆（可选，默认关闭）：`AML_HIGH_LEVEL_MEMORY=1` 时在后台调用
   `mandol.auto_builder.build_high_level_memory()`，构建分层摘要/情景/实体关系
   记忆（与上游 `benchmark_self_host` 同源），需要 LLM provider Key。
5. 合规机制：默认 30 天数据自动清理；日志不记录消息正文；未启用任何硬编码答案、
   数据集泄漏或评测数据复用。

### 与上游“主体”的关系

本适配不构成对 Mandol 方法的修改或再训练，仅在赛事要求的
「Add/Search 接口」与 Mandol 本体之间做工程封装（接口适配、部署、隔离、鉴权、
限流、留存）。任何检索/记忆算法能力均来自 Mandol 本身。

## 备注

- 若后续对 `src/mandol/` 或 `pyproject.toml` 做了修改（例如调参、增量高层记忆、
  新增后端），必须在本文件与报名材料中**追加披露**，并更新固定 commit/版本号。
