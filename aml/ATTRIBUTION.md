# 方法与版权归属声明（Attribution）

## 原始方法

- **名称**：Mandol（An Agglomerative Agent Memory System for Long-Term Conversations）
- **作者**：Mandol Team（AgentCombo，南京大学等团队发布）
- **论文**：<https://arxiv.org/abs/2606.29778>
- **代码**：<https://github.com/AgentCombo/Mandol>（Apache-2.0）
- **技术报告 / 复现分支**：上游 `paper-repro` 分支承载论文冻结实验

## 本参赛系统

- 名称：**Mandol-AML**
- 版本：0.1.0-aml.1（冻结上游 Mandol 0.1.0 / `main` @ [固定 commit]）
- 性质：在 Mandol 之上新增的 AML 赛事接入封装（Add/Search HTTP 接口、部署与合规层），
  不修改 Mandol 算法主体、不做评测集训练或微调。

## 使用的第三方组件

- 全部第三方依赖（torch、sentence-transformers、faiss、rocksdict、fastapi、
  pydantic 等）均由上游 `pyproject.toml` 声明，各自遵循其许可证。
- 本适配层新增代码遵循 Apache-2.0。

## 合规承诺

1. 已如实披露原始方法、作者、技术报告与本次改动（见 CHANGES.md）。
2. 评测数据仅用于当次评测任务，不用于训练、微调、产品分析、数据集重建或对外传播；
   按平台要求于任务结束后 30 天内删除。
3. 未硬编码答案、未泄漏评测数据、未使用提示词注入或人工实时答题。
