# 参赛版本改动披露（Change Disclosure）

> 说明：Mandol 为课题组自研项目；本参赛系统是在主开发仓库基础上为 AML 赛事建立的
> **赛事开发分支**（bubaa9531-dh/Mandol），仅做赛事适配包装，**不修改 Mandol 主体**。
> 本文档披露“赛事分支相对主仓库基线”的全部改动，供赛事方资格与合规复核。

## 1. 项目与基线

- 项目：Mandol: An Agglomerative Agent Memory System for Long-Term Conversations（课题组自研）
- 论文：https://arxiv.org/abs/2606.29778
- 论文作者：Yuhan Zhang, Zhiyuan Guo, Ziheng Zeng, Wei Wang, Wentao Wu, Lijie Xu（以论文页为准）
- 主开发仓库：https://github.com/AgentCombo/Mandol （Apache-2.0；PyPI mandol 0.1.0；Python >=3.12,<3.13）
- 赛事开发仓库：https://github.com/bubaa9531-dh/Mandol
- 与主仓库同步基线：`6d7af4f…`（fork 时与主仓库 `main` 一致）
- 适配层代码完成提交：`b4dc454149a29b34e669e73291d2e944e557f080`
- 正式参评版本：`v0.1.0-aml.1`（提交 Full 前打 tag 并锁定，以报名时为准）

## 2. 改动范围（相对基线，全部为新增文件）

**原则：不修改主仓库任何既有文件。`src/mandol/`、`pyproject.toml`、`uv.lock`、
README 等主体内容保持不变。**

| 新增文件/目录 | 作用 | 是否影响 Mandol 主体 |
| --- | --- | --- |
| `src/mandol_aml/` | AML Add/Search/Health HTTP 适配层（FastAPI），含契约校验、鉴权、限流、留存 | 否，仅调用 Mandol 公共 API |
| `Dockerfile`、`docker-compose.yml`、`.dockerignore` | 容器化部署 | 否 |
| `aml.env.example` | 适配层环境变量模板（不含任何真实密钥） | 否 |
| `README_AML_OVERLAY.md` | 赛事分支使用与叠加说明 | 否 |
| `aml/README.md`、`aml/CHANGES.md`、`aml/ATTRIBUTION.md`、`aml/docs/*` | 文档与参赛材料 | 否 |
| `aml/scripts/smoke_test.py` | 按 AML 契约的本地冒烟客户端 | 否 |
| `tests/conftest.py`、`tests/test_contract.py` | 契约单元测试（主仓库 tests/ 无同名文件） | 否 |

## 3. 适配层行为说明

1. **Add**：将平台下发的消息块转换为 Mandol `MemoryUnit`（正文存 `text_content`；
   `role/timestamp/user_id/session_id/request_id` 存 metadata），经
   `SemanticGraph.batch_add_units()` 写入；写入完成且立即可检索后才返回 HTTP 200。
2. **隔离**：`user_id` 是唯一检索隔离边界。默认 `shared` 后端为每个 `user_id`
   在共享语义图内建独立 MemorySpace，检索限定在该空间；`isolated` 后端为每个
   `user_id` 单独建图（模型权重经 Mandol 模型管理器共享），可支持混合检索且不跨用户泄漏。
3. **Search**：默认 `SemanticGraph.search_similarity_in_graph()` 稠密检索（按用户空间限定）；
   可选 `isolated` + `MultiRetriever.smart_search()` 混合检索。仅返回记忆证据，不生成答案。
4. **可选实验特性（默认关闭）**：`AML_HIGH_LEVEL_MEMORY=1` 时在后台调用
   `mandol.auto_builder.build_high_level_memory()` 做记忆组织（与主仓库
   `benchmark_self_host` 同源）；需 LLM provider Key；只整理记忆、不参与答题。
5. **合规机制**：默认 30 天数据自动清理；日志不含消息正文；未启用任何硬编码答案、
   数据集泄漏或评测数据复用；Memory System Key 等凭证不入仓库。

## 4. 与主仓库主体的关系

赛事开发分支 = 主仓库 Mandol（算法主体，未改动）+ 赛事适配层（接口封装、部署、
隔离、鉴权、限流、留存）。检索与记忆能力均来自 Mandol 本身；适配层不构成对
Mandol 方法的修改、再训练或评测集适配。

## 5. 后续维护义务

若后续修改 `src/mandol/`、`pyproject.toml` 或检索策略，须在本文件与报名材料中
**追加披露**，并更新锁定版本/tag。
