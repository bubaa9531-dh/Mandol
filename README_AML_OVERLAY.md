# Mandol-AML Overlay（公开仓库说明）

本仓库为课题组自研 Mandol 的**赛事开发分支**（fork 自主开发仓库，用于独立开发）。
本目录内容为**纯增量**：复制到赛事开发仓库根目录后，仅新增 AML Add/Search 适配层，
主仓库主体（`src/mandol/`、`pyproject.toml`、`uv.lock`）零修改。

## 公开仓库文件清单（已同步到 GitHub）

```
Dockerfile  docker-compose.yml  .dockerignore  aml.env.example  README_AML_OVERLAY.md
src/mandol_aml/          # AML 适配包（Add/Search/Health、隔离、鉴权、限流、留存）
tests/conftest.py  tests/test_contract.py  tests/test_service_logic.py
aml/README.md            # 适配层说明
aml/CHANGES.md           # 改动披露（赛事合规）
aml/ATTRIBUTION.md       # 系统归属与引用
aml/docs/02_方法说明.md  # 代码实现与方法说明（赛事复核）
aml/docs/03_接口与运行说明.md
aml/scripts/smoke_test.py
```

**说明**：报名信息、合规签字声明、英文填报摘要、内部验收清单与本地部署自测材料等，
属受控/内部信息，**不随公开仓库发布**，仅按赛事要求在平台表单与受控渠道提交，
团队在私有位置保留副本（勿上传本仓库）。

## 验证

```bash
uv sync --frozen --no-dev
pytest tests/ -q
cp aml.env.example .env          # 正式评测前设置 AML_MEMORY_SYSTEM_KEY
python -m mandol_aml
python aml/scripts/smoke_test.py --base-url http://127.0.0.1:8000
docker compose up -d --build     # 或容器化部署
```

## 文档索引（公开）

- 适配层主文档：`aml/README.md`
- 改动披露（合规必需）：`aml/CHANGES.md`
- 系统归属与引用：`aml/ATTRIBUTION.md`
- 代码实现与方法说明：`aml/docs/02_方法说明.md`
- 接口与运行说明：`aml/docs/03_接口与运行说明.md`
- 报名入口：https://agentmemoryleaderboard.ai/evaluation
