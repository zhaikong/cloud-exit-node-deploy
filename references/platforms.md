# 平台评估矩阵

按"能否在无人值守的情况下从零跑到可用节点"排序。结论来自实际探测，仅供快速否决，平台策略会变，用前先复核关键项。

## 可用

| 平台 | 形态 | 免卡 | 时长限制 | 公网访问 | 备注 |
|---|---|---|---|---|---|
| E2B（e2b.dev） | Firecracker 沙箱 | 是 | **单 session 上限 1 小时** | 创建时需 `allow_public_traffic=True` | Hobby 档一次性赠送额度，2vCPU/4GiB 约 $0.166/h；出口 Google Cloud；必须定时重建 |
| Unikraft Cloud | unikernel 实例 | 是 | 无（scale-to-zero 可休眠） | 自动分配域名 | 只跑 `kraftcloud/x86_64` 镜像；配额**按 metro 独立**（每 metro 2 live / 5 实例）；适合做长期主力 |

## 已否决

| 平台 | 否决原因 |
|---|---|
| Alwaysdata | 免费档强制验信用卡 |
| blitz.cloud | 注册页 Cloudflare Turnstile |
| Serv00 | reCAPTCHA + 直接 403 |
| ClawCloud Run | 域名不可达（连接超时） |
| Waifly | reCAPTCHA + 条款禁止网络转发用途 |
| Deployxa | 免费档 AUP 明文禁止代理/隧道类负载，上传时静态扫描拦截 |
| Pterodactyl 系面板 | 只支持 Discord OAuth 注册 |
| Hugging Face Spaces | Cloudflare challenge + 需登录态 |
| Back4App Containers | 控制台为 SPA + Google OAuth |
| Vercel / Zeabur / Sevalla / Choreo / Qovery | 只支持 git 部署或需 GitHub 授权，无法跑静态二进制 |
| Railway / Fly / Koyeb / Render / Northflank | 需 GitHub 授权或绑卡 |
| Modal / Beam / Replicate / Fal / Lightning | 需账号审核或绑卡，且不适合长连接 |
| Clever Cloud | 仅 git 部署 |

## 评估清单（新平台按此顺序过）

1. 注册页搜 `credit card`、`billing`、`verify` → 有强制验卡即否决
2. 注册页搜 `turnstile`、`recaptcha`、`hcaptcha`、`challenge` → 有人机挑战即降级
3. 条款搜 `proxy`、`vpn`、`tunnel`、`prohibited`、`restricted` → 明文禁止即否决
4. 文档确认能否上传并运行自有 linux/amd64 静态二进制
5. 文档确认公网访问是否需要额外开关/token，记录准确参数名
6. 文档确认单实例最长存活时间
7. 确认命令执行返回后进程是否保留（是否需要 setsid）

前 3 项任一项命中硬否决，直接换平台，不要试图绕过。
