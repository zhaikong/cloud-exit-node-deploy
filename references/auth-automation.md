# 登录与凭据自动化

目标：在无人点击的前提下拿到平台 API 凭据。

## 通用顺序

1. **先找 API Key 页面**：多数平台在控制台有 "API Keys" 页，登录后创建即可
2. **再找可直接调用的登录 API**：Ory/Kratos、Firebase、自研 `/api/auth/*`
3. **最后才用浏览器点 UI**：UI 自动化最脆弱，作为兜底

## Ory Kratos / Hydra 体系

特征：`/self-service/login/browser`、`/self-service/login?flow=`、`sessions/whoami`。

要点：

- 不要用 curl 单独建 flow 再让浏览器提交，会 CSRF 不匹配
- 正确做法：**让浏览器自己走一遍入口**（带完整 OAuth 参数），拿到 flow id 与 csrf，然后在页面上下文内 fetch 提交

```js
// 浏览器页面上下文内执行
const r = await fetch(`/self-service/login?flow=${fid}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-CSRF-Token': csrf,
  },
  body: JSON.stringify({
    method: 'password',
    identifier: EMAIL,
    password: PASSWORD,
    csrf_token: csrf,
  }),
});
```

- 密码阶段返回 **422 `browser_location_change_required`** 属于成功信号，`error.reason` 里通常带完整跳转 URL，直接 `page.goto(该URL)` 即可完成 OAuth 落地
- `aal=aal2` 会要求第二因素，账号未配置时返回 "No authentication methods are available"，不要带这个参数

## 从网络响应里抓凭据

比读 DOM 可靠得多：监听 `page.on('response')`，匹配创建 key 的请求（常为 tRPC `?batch=1` 或 REST），直接取响应 JSON 里的 key 字段。

## 浏览器自动化要点（headless shell）

- 下载 Chromium 用镜像，别走官方源：`https://cdn.npmmirror.com/binaries/chrome-for-testing/<version>/linux64/chrome-headless-shell-linux64.zip`
- `page.type()` / `page.keyboard.type()` 在 headless shell 下常常输入值为空
- 填 React 受控组件用 native setter：

```js
const el = document.querySelector('input[name="name"]');
const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
set.call(el, 'value');
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

- 点按钮优先 `page.evaluate(() => btn.click())`，比 `elementHandle.click()` 稳
- 跨域被重置时给浏览器加代理：`--proxy-server=socks5://127.0.0.1:PORT`

## API header 验证

拿到 key 后，先打一个只读列表接口确认 header 名：

| header | 适用 |
|---|---|
| `X-API-Key: <key>` | 平台自签 API key 的常见形式 |
| `Authorization: Bearer <token>` | OAuth2 access token；部分平台不接受 API key |

用错会得到 `Invalid auth provider token` 之类的误导性 401。判据：同一 key 换 header 后从 401 变 200。

## 凭据落地

- 只存在运行环境的临时文件或密钥管理里，不写进 Skill 文件、不写日志、不在对话里回显
- 记录 key 的作用域（scope），只申请完成任务所需的最小权限
