# Mandol-AML Overlay（叠加包说明）

本目录是一份**纯增量叠加包**：把它下面的全部内容复制到
`AgentCombo/Mandol` 的 fork 仓库根目录后，即可得到参赛仓库
**Mandol-AML**（新增 AML Add/Search 适配层，不改动 Mandol 任何既有文件）。

> 本包**不含** Mandol 源码；Mandol 源码来自你 fork 的上游仓库本身。

## 如何生成参赛仓库（推荐流程）

1. 在 GitHub 上 fork `AgentCombo/Mandol` 到课题组账号（仓库建议保持公开，
   名称可沿用 `Mandol` 或改为 `Mandol-AML`）。
2. 克隆 fork 到本地/服务器：

   ```bash
   git clone https://github.com/<org>/Mandol.git
   cd Mandol
   git remote add upstream https://github.com/AgentCombo/Mandol.git
   ```

3. 把本目录内容复制进 fork 根目录（PowerShell）：

   ```powershell
   $overlay = "C:\...\outputs\Mandol-AML"
   Copy-Item -Path "$overlay\*" -Destination . -Recurse -Force
   ```

   或 bash：

   ```bash
   cp -r /path/to/Mandol-AML/. .
   ```

4. 提交并推送：

   ```bash
   git add -A
   git commit -m "feat(aml): add Agent Memory Leaderboard Add/Search adapter (Mandol-AML 0.1.0-aml.1)"
   git push origin main
   ```

5. 记录本次固定 commit（报名与 `aml/CHANGES.md` 需要）。

## 复制后新增了哪些文件（相对上游）

```
Dockerfile  docker-compose.yml  .dockerignore  aml.env.example  README_AML_OVERLAY.md
src/mandol_aml/        （适配包，全部新增）
tests/conftest.py  tests/test_contract.py
aml/README.md  aml/CHANGES.md  aml/ATTRIBUTION.md
aml/scripts/smoke_test.py
aml/docs/01_报名与提交信息表.md  aml/docs/02_方法说明.md
aml/docs/03_接口与运行说明.md    aml/docs/04_合规与诚信声明.md
aml/docs/05_Submission_Packet_EN.md
```

对上游既有文件（`src/mandol/`、`pyproject.toml`、`uv.lock`、README 等）**零修改**。
若你已有自己的 fork 分支，注意不要与本包在 `tests/conftest.py` 上冲突。

## 验证

```bash
uv sync --frozen --no-dev
pytest tests/test_contract.py -v
cp aml.env.example .env          # 按需修改
python -m mandol_aml
python aml/scripts/smoke_test.py --base-url http://127.0.0.1:8000
# 或 Docker
docker compose up -d --build
```

## 文档索引

- 适配层主文档：`aml/README.md`
- 改动披露（合规必需）：`aml/CHANGES.md`
- 方法与版权归属：`aml/ATTRIBUTION.md`
- 参赛材料：`aml/docs/01~05`
- 接口与运行说明：`aml/docs/03_接口与运行说明.md`
- 报名入口：<https://agentmemoryleaderboard.ai/evaluation>
