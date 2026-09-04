# 方法与版权归属声明（Attribution）

## 1. 原始方法与作者（完整披露）

| 项 | 内容 |
| --- | --- |
| 方法名称 | Mandol: An Agglomerative Agent Memory System for Long-Term Conversations |
| 论文 | https://arxiv.org/abs/2606.29778 |
| 论文作者 | Yuhan Zhang, Zhiyuan Guo, Ziheng Zeng, Wei Wang, Wentao Wu, Lijie Xu（以论文页为准） |
| 上游代码 | https://github.com/AgentCombo/Mandol（Apache-2.0；PyPI mandol 0.1.0） |
| 维护组织 | Mandol Team（AgentCombo） |
| 复现说明 | 上游 `paper-repro` 分支承载论文冻结实验；本参赛使用上游 `main` 公开实现 |

## 2. 本参赛系统

| 项 | 内容 |
| --- | --- |
| 系统名称 | Mandol-AML |
| 版本 | 0.1.0-aml.1 |
| 参赛组别/赛道 | 开源方法榜（学术方法榜）；文本记忆赛道 + 代码记忆赛道 |
| Fork 仓库 | https://github.com/bubaa9531-dh/Mandol |
| 上游同步点 | `6d7af4f…` |
| 适配层代码提交 | `b4dc454149a29b34e669e73291d2e944e557f080` |
| 正式参评锁定 | tag `v0.1.0-aml.1`（提交 Full 前创建并锁定，以报名时为准） |
| 性质 | 在 Mandol 之上新增的赛事接入封装（Add/Search HTTP、部署与合规层）；不改 Mandol 算法主体 |

## 3. 第三方组件与许可证

- 运行时依赖（torch、sentence-transformers、faiss、rocksdict、fastapi、pydantic 等）
  均由上游 `pyproject.toml` 声明，各自遵循其许可证。
- 本适配层新增代码遵循 Apache-2.0（与上游一致）。

## 4. 合规承诺

1. 已如实披露原始方法、作者、技术报告与本次改动（详见 `aml/CHANGES.md`）。
2. 评测数据仅用于完成当次评测任务；不用于训练、微调、产品分析、数据集重建或对外传播；
   任务结束后 30 天内删除。
3. 未硬编码答案、未泄漏评测数据、未使用提示词注入或人工实时答题；
   Search 仅返回记忆证据，不生成最终答案。
