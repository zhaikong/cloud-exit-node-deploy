# 配置模板

## 服务端（云上实例内运行）

监听 `0.0.0.0`，端口与平台声明的一致；WS 路径固定 `/ws`，避免与其他服务冲突。

```json
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "port": 8080,
      "listen": "0.0.0.0",
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "<UUID>" }],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": { "path": "/ws" }
      }
    }
  ],
  "outbounds": [{ "protocol": "freedom", "settings": {} }]
}
```

平台侧通常以 443 对外提供 TLS 终止，实例内监听明文端口即可，不需要在实例内配置证书。

启动命令（进程必须脱离会话）：

```bash
chmod +x ./xray
(setsid ./xray run -c config.json > xray.log 2>&1 &)
sleep 5
(ss -tln 2>/dev/null || netstat -tln 2>/dev/null) | grep 8080 || echo NOPORT
```

## 客户端（本地验收用）

socks 入站 + vless/ws/tls 出站，`serverName` 与 `host` 都必须填平台分配的公网域名。

```json
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "tag": "socks",
      "port": 10813,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "settings": { "udp": false }
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "<host>",
            "port": 443,
            "users": [{ "id": "<UUID>", "encryption": "none", "flow": "" }]
          }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "security": "tls",
        "tlsSettings": { "serverName": "<host>", "fingerprint": "chrome" },
        "wsSettings": { "path": "/ws", "host": "<host>" }
      }
    }
  ]
}
```

注意：`wsSettings.host` 用顶层 `host` 字段，不要写成 `headers: {Host: ...}`（后者已废弃，会有告警）。

## 分享链接

```
vless://<UUID>@<host>:443?encryption=none&security=tls&sni=<host>&fp=chrome&type=ws&host=<host>&path=%2Fws#<备注>
```

`path` 必须 URL 编码为 `%2Fws`。
