---
name: cloud-exit-node-deploy
description: 在免卡云沙箱/容器平台上部署轻量网络出口节点（VLESS+WS+TLS）的完整工程流程：平台可用性评估、注册与登录自动化、API 凭据获取、二进制上传与进程保活、端到端连通性验收、订阅与二维码交付。当用户要求在免费云平台部署自建远程访问节点、需要自动化完成平台注册与认证、需要从零打通某个平台的部署链路，或需要对已部署节点做端到端验收与交付时使用。
---

# 云出口节点部署

把"在某云平台上线一个自用网络出口节点"这件事拆成可验证的五步。每一步都有明确产出和验收口径，任何一步没过就不要宣称完成。

## 交付标准（缺一不算完成）

一个可用节点必须同时具备四项，缺任何一项都只能算"部署了"而不是"能用了"：

1. **分享链接**：`vless://<uuid>@<host>:443?encryption=none&security=tls&sni=<host>&fp=chrome&type=ws&host=<host>&path=%2Fws#<备注>`
2. **二维码**：690×690 PNG，手机客户端直接扫
3. **实测出口**：真实代理出网后拿到的公网 IP + 归属（国家/城市/ASN）
4. **限额说明**：该平台的时间上限、流量/并发限制、到期行为、失效后如何恢复

只有"进程起来了""端口在 LISTEN"不构成交付。

## 五步流程

### 第 1 步：平台评估

在动手注册之前，先用 5 分钟判断平台能不能承载。**评估顺序很重要，越早否决越省时间**：

| 检查项 | 判据 | 常见否决点 |
|---|---|---|
| 是否要绑卡 | 注册页/条款里搜 `credit_card`、`billing`、`payment method` | 免费档强制验卡 → 直接换 |
| 人机验证 | 注册/登录页是否有 Turnstile、reCAPTCHA、hCaptcha | 硬挑战无法自动过 → 换 |
| 部署自由度 | 能否上传并运行自有静态二进制 | 只接受 git push / 只跑指定 runtime → 看是否可绕过 |
| 公网访问方式 | 是否需要额外开关或 token | 默认关公网、需要 access token → 记录参数名 |
| 进程存活 | 命令返回后进程是否被杀 | 无 `setsid` 就死 → 部署时必须后台化 |
| 时长限制 | 单实例/session 最长多久 | 1 小时上限 → 只能做临时补充，不能当主力 |
| AUP 条款 | 搜 `proxy`、`vpn`、`tunnel`、`prohibited` | 明文禁止 → 不要尝试，会封号 |

详细平台矩阵（含已实测结论，避免重复踩坑）见 [references/platforms.md](references/platforms.md)。

### 第 2 步：认证自动化

目标：拿到一个能调用平台 API 的凭据（API Key / Token），且**不需要人工点击**。

按平台形态选路径：

- **有公开 API Key 页面** → 登录后进控制台创建，从网络响应里抓 key（比读页面 DOM 可靠）
- **Ory / Kratos 体系**（`/self-service/login`）→ 在浏览器页面上下文内 `fetch` 直接 POST，见 [references/auth-automation.md](references/auth-automation.md)
- **Firebase 体系** → `identitytoolkit` 的 `signInWithPassword` 换 idToken，注意该域名在部分网络环境不可达，需先自建可用出口
- **只有 OAuth 第三方登录** → 评估是否可接受；纯 Discord/Google OAuth 且无邮箱注册的，通常不值得投入

凭据到手后，**先用一个最轻的只读接口验证 header 名称**。同名概念在不同平台差别很大，例如：

- `Authorization: Bearer <api_key>` —— 有些平台只认 OAuth access token，传 API key 会报 invalid token
- `X-API-Key: <api_key>` —— 另一些平台只认这个

用错 header 会得到误导性的 401，浪费大量时间。验证方法：拿一个已知应返回 200 或空数组的列表接口试。

### 第 3 步：部署

最小可靠部署序列：

1. 创建实例/沙箱，**把所有 create-only 的网络开关一次配齐**（公网访问、端口白名单、Host 处理），因为这些参数建完就改不了，漏了只能重建
2. 上传二进制与配置（配置里 inbound 监听 `0.0.0.0`，不要 `127.0.0.1`）
3. `chmod +x` 后以 `setsid ... &` 方式后台启动，**同一条命令内 sleep 数秒再检查监听状态**
4. 用 `ss -tln` 或 `netstat -tln` 确认端口在 LISTEN，再取公网域名

配置模板见 [references/config-templates.md](references/config-templates.md)。

### 第 4 步：端到端验收

**必须走真实代理链路，不能在服务端 curl localhost 就算通过。**

1. 先在外部直连测试公网域名：返回 404/400 属正常（说明边缘层通了且转发到了服务）；返回 **403 且 body 提到 token** 说明公网访问没开
2. 本地起一个 xray 客户端（socks 入站 → vless+ws+tls 出站）
3. 通过该 socks 请求 `https://www.gstatic.com/generate_204`，**必须返回 204**
4. 通过该 socks 请求 IP 查询接口，核对出口 IP 与归属
5. 两项目都过才算验收通过

自动化验收脚本：[scripts/verify_node.py](scripts/verify_node.py)。用法：

```bash
python3 scripts/verify_node.py --host <host> --uuid <uuid> --xray /path/to/xray
```

脚本会自建临时客户端配置、起进程、跑两项检测、打印出口归属、最后清理进程。

### 第 5 步：交付

按"交付标准"四件套输出。二维码生成：

```bash
python3 scripts/gen_qr.py --url "<vless链接>" --out node.png
```

**交付时必须主动说明限额**，尤其是时间上限。如果平台单实例只能活 1 小时，要明确告诉用户这是临时节点，并给出两种选择：接受定时重建（域名会变，订阅文件与二维码需要跟着更新），或改用无时长限制的平台做主节点。

## 关键坑（都是实际踩过的）

| 现象 | 根因 | 处理 |
|---|---|---|
| 公网 403，body 含 `traffic access token` | 公网访问默认关闭 | 创建时传 `network={"allow_public_traffic": True}`（Python SDK）/ `network: {allowPublicTraffic: true}`（Node SDK）；**create-only，改不了只能重建** |
| 公网 403/404 反复 | 端口未在白名单 | 创建时一并声明 `https_ports` / `httpsPorts` |
| 命令返回后进程消失 | 前台进程随会话回收 | `setsid ./svc run -c cfg > log 2>&1 &`，并在同一命令内 sleep + 检查 |
| 客户端 accepted 连接但无后续 | 上游 WS 握手失败 | 先直连测域名；403 优先怀疑公网开关，000 怀疑 TLS/Host |
| `pkill -f "xray run"` 让当前 shell 退出 | 匹配到了自己所在命令行 | 改用 `killall xray`，或用精确 pid |
| 浏览器自动化填不进 React 输入框 | headless 下键盘事件无效 | 用 native setter + `dispatchEvent(new Event('input',{bubbles:true}))` |
| Chromium 下载极慢 | 官方源跨境 | 换 npmmirror 的 `chrome-for-testing` 镜像，速度可差三个数量级 |
| 页面内 fetch 报 CSRF 不匹配 | flow 与 cookie 不在同一会话 | 让浏览器从入口完整走一遍，不要用 curl 单独建 flow |

## 安全与边界

- 只使用用户自己注册的账号，不代替用户接受任何付费条款、不绑定任何支付方式
- 涉及费用、绑卡、实名认证时停下来交给用户决定
- 平台 AUP 明文禁止的网络用途，直接放弃该平台，不尝试绕过
- 用户凭据不写入 Skill 文件、不写日志、不在回复中回显

## 参考文件

- [references/platforms.md](references/platforms.md) —— 平台评估矩阵与已实测结论
- [references/auth-automation.md](references/auth-automation.md) —— 登录与 API 凭据自动化套路
- [references/config-templates.md](references/config-templates.md) —— 服务端/客户端配置模板
- [scripts/verify_node.py](scripts/verify_node.py) —— 端到端验收
- [scripts/gen_qr.py](scripts/gen_qr.py) —— 二维码生成
