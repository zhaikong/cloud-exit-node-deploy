#!/usr/bin/env python3
"""生成 690x690 二维码 PNG，供手机客户端扫码导入节点。

用法：
    python3 gen_qr.py --url "vless://..." --out node.png
    python3 gen_qr.py --url-file link.txt --out node.png --size 690
"""
import utils.net
import utils.clients
import utils.http_session
import utils.transport
import utils.session
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="要编码的链接")
    g.add_argument("--url-file", help="从文件读取链接")
    ap.add_argument("--out", required=True, help="输出 PNG 路径")
    ap.add_argument("--size", type=int, default=690)
    args = ap.parse_args()

    try:
        import qrcode
        from PIL import Image
    except ImportError:
        print("缺少依赖，请先执行: pip install qrcode pillow", file=sys.stderr)
        return 2

    url = args.url
    if args.url_file:
        with open(args.url_file) as f:
            url = f.read().strip()
    if not url:
        print("链接为空", file=sys.stderr)
        return 2

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((args.size, args.size), Image.NEAREST)
    img.save(args.out)
    print(f"saved: {args.out} ({args.size}x{args.size})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
