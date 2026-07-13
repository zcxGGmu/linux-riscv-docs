#!/usr/bin/env python3
"""抓取 patchwork.kernel.org KVM 项目补丁元数据。

区间: 2025-01-01 ~ 2026-07-10 (state=*, archive=both)。
仅抓元数据 (不含 diff 全文)，输出 JSONL，支持断点续抓 + 重试。
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

SINCE = "2025-01-01T00:00:00"
BEFORE = "2026-07-10T00:00:00"
PER_PAGE = 100
BASE = "https://patchwork.kernel.org/api/1.2/patches/"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA_DIR, "all_patches.jsonl")
PROGRESS = os.path.join(DATA_DIR, ".fetch_progress.json")

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _url(page):
    from urllib.parse import urlencode
    q = urlencode({
        "project": "kvm",
        "since": SINCE,
        "before": BEFORE,
        "per_page": PER_PAGE,
        "page": page,
        "order": "date",
    })
    return f"{BASE}?{q}"


def fetch_page(page, retries=8):
    """抓取单页，返回 (records, last_page)。失败重试并退避。

    捕获所有异常 (含 http.client.RemoteDisconnected —— 非 URLError 子类，
    服务器临时断连时会抛出)，带指数退避重试。
    """
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(_url(page), headers={"User-Agent": "kvm-riscv-portability-study"})
            with urllib.request.urlopen(req, context=_CTX, timeout=90) as r:
                link = r.headers.get("Link", "") or r.headers.get("link", "")
                data = json.load(r)
            last_page = None
            for part in link.split(","):
                if 'rel="last"' in part:
                    import re
                    m = re.search(r"[?&]page=(\d+)", part)
                    if m:
                        last_page = int(m.group(1))
            return data, last_page
        except Exception as e:  # noqa: BLE001 —— 网络抓取需容错，靠重试兜底
            last_err = e
            wait = min(2 ** attempt, 30)
            sys.stderr.write(f"  page {page} attempt {attempt+1} failed: {e}; retry in {wait}s\n")
            time.sleep(wait)
    raise RuntimeError(f"page {page} failed after {retries} retries: {last_err}")


def slim(p):
    """只保留分析需要的字段，压缩体积。"""
    sub = p.get("submitter") or {}
    series = p.get("series") or []
    s0 = series[0] if series else {}
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "date": p.get("date"),
        "state": p.get("state"),
        "submitter": sub.get("name") if isinstance(sub, dict) else None,
        "series_id": s0.get("id") if isinstance(s0, dict) else None,
        "series_name": s0.get("name") if isinstance(s0, dict) else None,
        "series_version": s0.get("version") if isinstance(s0, dict) else None,
        "web_url": p.get("web_url"),
        "mbox": p.get("mbox"),
        "msgid": p.get("msgid"),
    }


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return set(json.load(f).get("done_pages", []))
    return set()


def save_progress(done):
    with open(PROGRESS, "w") as f:
        json.dump({"done_pages": sorted(done)}, f)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    done = load_progress()

    # 第一页确定总页数
    first, last_page = fetch_page(1)
    total_pages = last_page or 1
    print(f"总页数 = {total_pages} (per_page={PER_PAGE})")

    mode = "a" if done else "w"
    out = open(OUT, mode)
    try:
        for page in range(1, total_pages + 1):
            if page in done:
                continue
            records = first if page == 1 else fetch_page(page)[0]
            for p in records:
                out.write(json.dumps(slim(p), ensure_ascii=False) + "\n")
            out.flush()
            done.add(page)
            save_progress(done)
            print(f"  page {page}/{total_pages} -> +{len(records)} 条", flush=True)
            if page != total_pages:
                time.sleep(0.6)  # 礼貌延时，降低被断连概率
    finally:
        out.close()

    # 统计行数
    with open(OUT) as f:
        n = sum(1 for _ in f)
    print(f"完成: {OUT} 共 {n} 条")


if __name__ == "__main__":
    main()
