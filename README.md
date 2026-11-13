# swingattr · 指标波动归因与维度贡献度分解台

> 把「GMV 掉 8.3%，开会 2 小时翻 Excel 找原因」压成一条可复现链路：选基线 → 判异常 → 拆维度 → 出日报。

## 真实场景

**客户**：沃田生鲜 · 经营分析组（8 人）。每日 GMV 看板，全国 3 城、4 大品类、3 个渠道、8 家门店、2 类客群。

**现有工作流**：分析师把各维度报表导出 Excel 逐一对比，凭经验写结论发群；下次同类波动重来一遍。

**三个痛点**

1. 人工下钻慢且漏维度组合：人只会看「城市」「品类」几个大数，交叉组合基本靠猜。
2. 维度组合爆炸：城市 × 品类 × 渠道 × 门店 × 客群 = **576 种组合**，不可能穷举。
3. 结论不成文、口径不统一：这次用环比、下次用同比，谁也说不出为什么，结论散在聊天记录里。

**上下游**：上游 = 订单明细汇总的日事实 + 维度表 → 本台替代「人工下钻 + Excel 对比」→
下游 = 早会结论、日报分发（飞书 / 邮件 / 企微记录）。

## 角色与权限

| 角色 | 邮箱 | 主要页面 | 权限点 | 典型动作 |
|---|---|---|---|---|
| `admin` 分析负责人 | `admin@swingattr.io` | 全部 | `metric:read/write` `baseline:read` `attribution:run` `report:read/write` `report:distribute` `export:read` `audit:read` | 改指标口径、跑归因、生成并**分发**日报 |
| `analyst` 分析师 | `analyst@swingattr.io` | 看板 / 归因 / 下钻 / 基线 / 日报 | `metric:read` `baseline:read` `attribution:run` `drilldown:read` `report:read/write` `export:read` | 跑归因、确认异常、写结论、导出 MD |
| `exec` 管理层（只读） | `exec@swingattr.io` | 看板 / 日报 | `metric:read` `report:read` | 只看趋势与日报，不改不跑不分发 |

密码统一 `Demo@2026`。**服务端真实 403**：`exec` 调归因 / 基线 / 生成日报 / 分发全部 403；
`analyst` 调分发与改指标口径也是 403（不是前端藏按钮）。

## 一天的工作剧本（2026-11-10 晨会前）

| 时间 | 谁 | 做什么 | 真实数值 |
|---|---|---|---|
| 08:05 | 周到（analyst） | 打开观测台 | GMV 11-09 935,340，前一日 1,020,000 左右浮动 |
| 08:06 | 周到 | 选基线 | 11-09 是**周一**，11-08 是周日 → 日环比会被周末效应污染；算法选**周环比 11-02** |
| 08:07 | 周到 | 判异常 | Δ = −84,660（−8.30%），MAD = 20,650，**z = 4.10 > 3** → 异常·关注 |
| 08:09 | 周到 | 跑归因 | 36 个三元组 + 33 个二元组扫描；头号因子 **华东 × 水产 × 社区团购 −53,040 元**（−5.2pp，占总降幅 62.7%） |
| 08:11 | 周到 | 量价拆解 | 订单量 8,000 → 7,240（−9.50%），客单价 127.50 → 129.19（+1.33%）→ **降的是量不是价** |
| 08:13 | 周到 | 生成日报 | 自动写 markdown（因子表 + 量价表 + 结论 + 口径） |
| 08:15 | 林清河（admin） | 分发 | 飞书群 + 邮件，**2 条分发记录** |
| 08:20 | 苏未（exec） | 看日报 | 只读，无分发按钮，服务端也拒 |

## 主要功能（5 个模块串成链路）

1. **指标看板**（`/dashboard`）：5 个指标的趋势（等压线 + 风玫瑰刻度自绘）、日环比、峰谷均值、最近归因批次、五维度成员树。
2. **基线设置**（`/baseline`）：4 个候选基线（环比 / 周环比 / 近 4 周中位数 / 节假日位移）全部列出并给不可用原因；MAD 稳健离散与 z 值；**选中理由逐条可读**。
3. **归因分析**（`/attribution`）：瀑布图、Contribution Top-N 表、量价拆解、单维完整划分、守恒与残差校验、一键生成日报。
4. **维度下钻**（`/drilldown`）：city → category → channel → store → segment 逐层收窄，面包屑可回退。
5. **日报与分发**（`/reports`）：markdown 正文、分发记录、导出 `.md`。

## 两个真算算法

### 算法 1 · 波动分解（`backend/src/services/swing_service.py`）

```
加法指标（订单量 / 新客数 / 毛利额）
  Δ = value_now − value_base
  contribution_i = v_now,i − v_base,i
  Σ contribution_i == Δ            同一维度是完整划分 → 残差 0、解释度 100%

乘法指标（GMV = 订单量 × 客单价）
  Δln = ln(v_now / v_base) = ln(量比) + ln(价比)
  量/价效应按 Δln 占比回摊到金额：contribution_i = Δ × Δln_i / Δln
  → 量效应 + 价效应 == Δ（严格守恒）

组合扫描（痛点②：576 个组合无法穷举）
  只扫前 3 维的 36 个三元组（完整划分，不与 2 维对重复计数），按 |Δ| 排名取 Top-N
  残差 = Δ − Σ Top-N（显式返回）
  解释度 = Σ|Δ_TopN| / Σ|Δ_36组|（绝对覆盖，恒 ≤ 100%；有符号口径 signed_pct 另存）
```

实测（2026-11-09 GMV，top_n=8）：`−5.2pp`（华东 × 水产 × 社区团购）、`62.65%`（占总降幅）、
Top-8 绝对覆盖 `75.42%`（有符号 80.41%）、残差 `−16,583`（其余 28 个三元组）、守恒校验通过。

### 算法 2 · 基线选择与节假日校正（`backend/src/services/baseline_service.py`）

```
候选基线：prev_day（上一日） / same_weekday（同星期） / median_4w（近 4 周中位数） / holiday_shift（节假日位移）
稳健离散：MAD = median(|x − median(x)|)     近 4 周同星期序列
稳健异常：z = |Δ| / MAD                     > 3 判异常，≥ 5 升级「重大」
异常等级：normal / warning / critical
选基线规则：
  1) 命中节假日日历且能对齐上一个同类节点 → holiday_shift
  2) 上一日与同星期差异 < 3%              → prev_day（更贴运营直觉）
  3) 目标日为周一（上一日是周日）          → same_weekday（剔除周末效应）
  4) 其它                                  → same_weekday
```

实测：11-09 选中 `same_weekday`（11-02），Δ = −84,660（−8.30%），MAD = 20,650，**z = 4.10** → `warning`；
11-01 命中「双十一预热首日」→ 自动切到 `holiday_shift`，对齐 10-17「秋季会员日」。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 前端 http://localhost:18248 · 后端 http://localhost:19248/api/health
```

5 个服务：`frontend`(Nginx+dist) / `backend`(FastAPI) / `worker`(Celery) / `db`(MySQL 8.0) / `redis`(7)，全部 healthcheck。
`SEED_DEMO=true` 时 backend 启动自动跑一次幂等 seed（失败只记日志）。

本地开发：

```bash
cd backend && pip install -r requirements.txt && uvicorn src.main:app --reload --port 8000
cd frontend && npm install && npm run dev     # 5173，/api 代理到 19248
```

## 演示账号

| 邮箱 | 角色 | 密码 |
|---|---|---|
| `admin@swingattr.io` | 分析负责人 | `Demo@2026` |
| `analyst@swingattr.io` | 分析师 | `Demo@2026` |
| `exec@swingattr.io` | 管理层（只读） | `Demo@2026` |

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite 5 + React Router 6，图表全部 SVG 自绘（无图表库） |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 |
| 任务 | Celery 5.4（worker 容器；beat 心跳 + 每 15 分钟 GMV 波动巡检） |
| 数据库 | MySQL 8.0（utf8mb4；JSON 列存量价拆解与分发记录） |
| 缓存 | Redis 7（限流、worker 心跳、最近波动摘要） |
| 视觉 | 气象观测站风 · Barlow Condensed + Source Serif 4 · oklch · 等压线 / 风玫瑰刻度 / 观测卡 |

## 目录

```
backend/
  src/{config,constants,models,schemas,services,controllers,routes,middlewares,utils}/
  scripts/{seed_demo.py,demo_config.py,fact_builder.py,worker_healthcheck.sh}
  migrations/0001_initial.sql
frontend/
  src/{api,stores,types,components/common,components/layout,hooks,pages,router,utils,constants,styles}/
docker-compose.yml  .env.example
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | Compose 项目名 / 容器前缀 | `swingattr` |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 端口映射 | `18248` / `19248` / `17748` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_ROOT_PASSWORD` | MySQL | 见 `.env.example` |
| `JWT_SECRET` | JWT 签名密钥 | 见 `.env.example` |
| `REDIS_URL` | Celery broker / 限流 | `redis://redis:6379/0` |
| `SEED_DEMO` | 启动是否自动 seed | `true` |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_WRITE_PER_MINUTE` | 限流额度 | `300` / `60` |

## 共享枚举出现位置

| 枚举 | 后端 | 前端 |
|---|---|---|
| 角色 `Role` | `backend/src/constants/enums.py` · `constants/roles.py` | `frontend/src/constants/roles.ts` · `types/models.ts` |
| 指标类型 `MetricKind` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| 基线类型 `BaselineKind` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| 异常等级 `AnomalyLevel` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| 因子类型 `FactorKind` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| 日报状态 `ReportStatus` / 分发渠道 `DeliveryChannel` | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |

## 数据口径

- 事实粒度：`(日期, 城市, 品类, 渠道, 门店, 客群)`，30 天共 **5,000 条**；日粒度聚合由 SQL `GROUP BY` 派生。
- 11-09 的三组变化按绝对量精确闭合到 −84,660：组合 −53,040 / 华东其余 +2,800 / 华北+华南其余 −34,420。
- 生成完全确定性（整数权重 + 最大余额法），不含随机数与当前时间，两次 seed 数值逐字一致。

## 已知简化

见 `batch-20261112/test-artifacts/gb-575/TESTING.md` 的「已知差异」一节。

## License

MIT
