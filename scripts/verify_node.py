#!/usr/bin/env python3
"""端到端验收：本地起 xray 客户端，走真实代理链路检测连通性与出口。

用法：
    python3 verify_node.py --host <host> --uuid <uuid> --xray /path/to/xray
    python3 verify_node.py --host <host> --uuid <uuid> --xray ./xray --path /ws --port 443

通过判据：
    generate_204 返回 204，且能取到出口 IP。
退出码：0 通过，1 失败。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

GENERATE_204 = "https://www.gstatic.com/generate_204"
IP_ECHO = "https://api.ipify.org"
IP_DETAIL = "http://ip-api.com/json/?fields=query,country,regionName,city,isp,as"


def build_client(host, uuid, socks_port, path, port, server_name):
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks",
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": False},
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": host,
                            "port": port,
                            "users": [
                                {"id": uuid, "encryption": "none", "flow": ""}
                            ],
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "tlsSettings": {
                        "serverName": server_name or host,
                        "fingerprint": "chrome",
                    },
                    "wsSettings": {"path": path, "host": server_name or host},
                },
            }
        ],
    }


def curl_socks(url, socks_port, timeout=30, want_body=False):
    cmd = [
        "curl", "-s", "--max-time", str(timeout),
        "--socks5-hostname", f"127.0.0.1:{socks_port}",
        "-w", "\n%{http_code}", url,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10).stdout
    except subprocess.TimeoutExpired:
        return None, None
    if "\n" not in out:
        return None, out.strip() or None
    body, _, code = out.rpartition("\n")
    return code.strip(), (body if want_body else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="公网域名")
    ap.add_argument("--uuid", required=True, help="VLESS UUID")
    ap.add_argument("--xray", required=True, help="xray 可执行文件路径")
    ap.add_argument("--path", default="/ws")
    ap.add_argument("--port", type=int, default=443)
    ap.add_argument("--socks-port", type=int, default=10899)
    ap.add_argument("--sni", default=None)
    args = ap.parse_args()

    if not os.path.isfile(args.xray):
        print(f"[FAIL] xray 不存在: {args.xray}")
        return 1

    tmpdir = tempfile.mkdtemp(prefix="verify_node_")
    cfg_path = os.path.join(tmpdir, "client.json")
    proc = None
    ok = False
    try:
        cfg = build_client(args.host, args.uuid, args.socks_port, args.path, args.port, args.sni)
        with open(cfg_path, "w") as f:
            json.dump(cfg, f, indent=2)

        xray_bin = args.xray
        if not os.access(xray_bin, os.X_OK):
            xray_bin = os.path.join(tmpdir, "xray")
            shutil.copy(args.xray, xray_bin)
            os.chmod(xray_bin, 0o755)

        proc = subprocess.Popen(
            [xray_bin, "run", "-c", cfg_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(4)

        print("=== 1. 连通性 (generate_204) ===")
        code, _ = curl_socks(GENERATE_204, args.socks_port)
        print(f"generate_204: {code}")
        if code != "204":
            print("[FAIL] 未返回 204")
            return 1

        print("=== 2. 出口 IP ===")
        code, body = curl_socks(IP_ECHO, args.socks_port, want_body=True)
        ip = (body or "").strip()
        print(f"exit_ip: {ip or 'FAIL'}")
        if not ip or not ip[0].isdigit():
            print("[FAIL] 取不到出口 IP")
            return 1

        print("=== 3. 出口归属 ===")
        code, body = curl_socks(IP_DETAIL, args.socks_port, want_body=True)
        detail = (body or "").strip()
        print(detail or "N/A")

        print()
        print("[PASS] 验收通过")
        ok = True
        return 0
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmpdir, ignore_errors=True)
        if not ok:
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
