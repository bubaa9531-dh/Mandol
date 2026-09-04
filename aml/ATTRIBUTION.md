# 系统归属与引用说明（Project Ownership & Citation）

> 说明：Mandol 为课题组**自研**的智能体记忆系统。本参赛系统为 Mandol 按 AML
> 赛事要求完成的适配版本（Add/Search 封装 + 部署与合规层），不改动 Mandol 主体。

## 1. 项目归属与基本引用

| 项 | 内容 |
| --- | --- |
| 项目名称 | Mandol: An Agglomerative Agent Memory System for Long-Term Conversations |
| 项目性质 | 课题组自研项目（负责人：*[待填写]*；机构/团队：*[待填写]*） |
| 论文 | https://arxiv.org/abs/2606.29778 |
| 论文作者 | Yuhan Zhang, Zhiyuan Guo, Ziheng Zeng, Wei Wang, Wentao Wu, Lijie Xu（以论文页为准） |
| 主开发仓库 | https://github.com/AgentCombo/Mandol（Apache-2.0；PyPI mandol 0.1.0；Python >=3.12,<3.13） |
| 许可证 | Apache-2.0 |

## 2. 参赛版本与仓库关系

| 项 | 内容 |
| --- | --- |
| 参赛系统名称 | Mandol-AML |
| 版本 | 0.1.0-aml.1 |
| 参赛组别/赛道 | 开源方法榜（学术方法榜）；文本记忆赛道 + 代码记忆赛道 |
| 赛事开发仓库 | https://github.com/bubaa9531-dh/Mandol（fork 自主开发仓库，便于赛事独立开发与版本管理） |
| 与主仓库同步基线 | `6d7af4f…`（fork 时与主仓库 main 一致） |
| 适配层代码提交 | `b4dc454149a29b34e669e73291d2e944e557f080` |
| 正式参评锁定 | tag `v0.1.0-aml.1`（提交 Full 前创建并锁定，以报名时为准） |

**分支关系说明**：主开发仓库 AgentCombo/Mandol 持续承载 Mandol 研发；赛事开发仓库
bubaa9531-dh/Mandol 为参赛适配分支，仅在主仓库代码之上**新增**赛事适配层文件，
`src/mandol/`、`pyproject.toml`、`uv.lock` 等主体内容与主仓库保持一致、未被修改。

## 3. 本次改动（参赛适配，主体不变）

仅新增：`src/mandol_aml/`（AML Add/Search/Health 适配包）、Dockerfile /
docker-compose / .dockerignore、aml.env.example、README_AML_OVERLAY.md、
`aml/`（说明文档与参赛材料）、`aml/scripts/smoke_test.py`、
`tests/conftest.py`、`tests/test_contract.py`。完整清单见 `aml/CHANGES.md`。

## 4. 第三方组件与许可证

- 运行时依赖（torch、sentence-transformers、faiss、rocksdict、fastapi、pydantic 等）
  由项目 `pyproject.toml` 声明，各自遵循其许可证。
- 赛事适配层新增代码遵循 Apache-2.0（与项目一致）。

## 5. 合规承诺与密钥说明

1. 参赛系统 = 自研 Mandol（主体未改动）+ 赛事适配层；已在材料中如实说明项目归属、
   论文、作者与全部改动。
2. Search 仅返回记忆证据，不生成最终答案；`user_id` 为唯一检索隔离边界。
3. 评测数据仅用于当次任务：不训练、不微调、不重建数据集、不对外传播；任务结束
   30 天内删除。
4. 未硬编码答案、未泄漏评测数据、未使用提示词注入或人工实时答题。
5. 密钥说明：Memory System Key（AML_MEMORY_SYSTEM_KEY）、Eval/Leaderboard Key、
   LLM provider Key（DeepSeek/DashScope 等）属必要敏感信息，由**项目总负责人**
   提供并在**部署端环境变量**配置，一律不写入公开仓库或文档正文。
