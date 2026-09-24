# 本 Fork 与上游的差异说明

> 面向:看到本仓库(有 star)但不清楚它与上游关系的人。
> 上游: [`Fly143/workbuddy-desktop-api`](https://github.com/Fly143/workbuddy-desktop-api)
> 本 fork: [`Twelve-eight/workbuddy-desktop-api`](https://github.com/Twelve-eight/workbuddy-desktop-api)

## 一句话

本 fork 把上游**从国内版(CodeBuddy)整体切到国际版(WorkBuddy AI)**,并补了三个
上游兼容性修复与一套 Windows 服务化脚本。**上游的全部修复已合流**(截至 v1.2.3.4)。

## 同步状态

| | |
|---|---|
| 合流点 | 上游 `v1.2.3.4`(25 个提交) |
| 上游独有提交 | **0** |
| 本 fork 独有 | 12 个提交 |
| 版本 | 跟随上游 `1.2.3.4` |

## 与上游的差异(全部)

### 1. 会话层切到国际版 — `app/workbuddy_session.py`

| 常量 | 上游 | 本 fork |
|---|---|---|
| `API_BASE` | `https://copilot.tencent.com` | **`https://www.workbuddy.ai`** |
| `AUTH_FILE_NAME` | `workbuddy-desktop.info` | **`workbuddy-desktop-ai.info`** |
| `DEFAULT_DOMAIN` | `www.codebuddy.cn` | **`www.workbuddy.ai`** |

这是本 fork 存在的**主要原因**:读国际版桌面客户端的会话。

### 2. 三个上游兼容性修复

**`app/workbuddy_client.py` — 首条消息必须是 system**
上游要求 `messages[0].role == "system"`,否则返回 **11-128**。本 fork 在缺失时自动补一条
`You are a helpful assistant.`。

**`app/workbuddy_client.py` — 思考参数(与上游已合流)**
原本写死 `reasoning_effort=medium`,实测会让上游 `content=0`(正文被思考吞掉)并触发内容安全
**11-128**。按 CodeBuddy 契约改为:
```
thinking 开 → reasoning_summary=auto(让上游定深度)
客户端显式给了档位 → 原样透传 reasoning_effort
thinking 开但无档位 → 兜底 high
thinking 关 → 不发送
```
> 注:上游独立地做了"透传 + 默认 high"。两者**互补而非冲突**,已合并保留。

**`app/utils.py` — 工具结果截断**
上游窗口约 102K 字符,而 agent 工具结果(如读整个文件)单条可达 20K+;多轮累积会撑爆窗口,
早期历史被静默丢弃,模型"失忆"后反复重读同一批文件。本 fork 对超长工具结果保留**头 60% + 尾 40%**,
默认 3000 字符,可用环境变量 `WORKBUDDY_TRUNCATE_TOOL_RESULTS` 调整。

### 3. 模型列表 — `app/routes.py`
新增 `deepseek-v4.1-flash`;并引入 `_append_extra_models()`,让云端列表拉取失败时也能补齐本地模型。

### 4. Windows 服务化与运维脚本(本 fork 新增,上游没有)
| 文件 | 作用 |
|---|---|
| `supervisor.py` | 进程守护(+213 行) |
| `install-svc.cmd` / `uninstall-svc.cmd` | 注册/注销 Windows 服务 |
| `gateway-window.cmd` | 可见状态窗 + 日志可外部读取 |
| `start.cmd` | 启动入口 |
| `.omp/hooks/pre/backup.ts` | 写入前自动 git 备份钩子 |
| `DEVLOG.md` | 部署/补丁/验证记录 |

## 状态:已退休

本仓库已归档到工作区的 `archive/retired/`,功能由 `workbuddy2api` 取代。
保留它是为了**历史参考**与**上游修复的溯源**,不再作为活跃开发线。

## 给上游用户的建议

如果你只是想用上游,直接用 `Fly143/workbuddy-desktop-api`。
只有当你需要**国际版(WorkBuddy AI)会话**时,本 fork 才有额外价值。