"""Zennに1日1本ずつ公開する（.github/workflows/zenn-publish-daily.yml から呼ぶ）。

Zennは直近24時間の投稿数に上限があり、まとめてpushすると弾かれる。
そこで公開待ちの記事は _queue/ に置き、このスクリプトが1回に1本だけ articles/ へ移す。

1. articles/ で published: true なのに、Zennで公開されていない記事があれば
   （前回、上限で弾かれた）、新しい記事は出さずに再デプロイだけする。
2. なければ、_queue/ の先頭（ファイル名順）の1本を articles/ へ移して published: true にする。
   _queue/ のファイル名は「01_<slug>.md」の形。「01_」は順番用で、移すときに外す。

結果は GITHUB_OUTPUT の action に書く：publish / retry / none。
"""

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = "tomoki_dojo"
ARTICLES = Path("articles")
QUEUE = Path("_queue")
QUEUE_NAME = re.compile(r"^\d+_([a-z0-9][a-z0-9_-]{10,48}[a-z0-9])\.md$")
PUBLISHED = re.compile(r"^published:\s*(true|false)\s*$", re.M)


def set_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    print(f"{key}={value}")


def is_live(slug: str) -> bool | None:
    """Zennで公開されていれば True、されていなければ False、確認できなければ None。"""
    req = urllib.request.Request(
        f"https://zenn.dev/api/articles/{slug}",
        headers={"User-Agent": f"zenn-content-publisher ({USERNAME})"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        print(f"確認できませんでした（{slug}）: HTTP {e.code}")
        return None
    except Exception as e:  # ネットワークの一時的な失敗など
        print(f"確認できませんでした（{slug}）: {e}")
        return None


def main() -> None:
    # 1. 前回弾かれた記事がないか
    for path in sorted(ARTICLES.glob("*.md")):
        m = PUBLISHED.search(path.read_text(encoding="utf-8"))
        if not m or m.group(1) != "true":
            continue
        live = is_live(path.stem)
        if live is None:
            set_output("action", "none")  # 確認できない日は何もしない（次の日にやり直す）
            return
        if not live:
            print(f"未公開のまま：{path.stem}（上限で弾かれた可能性）→ 再デプロイだけする")
            set_output("action", "retry")
            set_output("slug", path.stem)
            return

    # 2. キューから1本出す
    queued = sorted(p for p in QUEUE.glob("*.md") if QUEUE_NAME.match(p.name))
    if not queued:
        print("公開待ちの記事はありません")
        set_output("action", "none")
        return

    src = queued[0]
    slug = QUEUE_NAME.match(src.name).group(1)
    dest = ARTICLES / f"{slug}.md"
    if dest.exists():
        sys.exit(f"articles/{slug}.md がすでにあります。_queue/{src.name} を確認してください")

    text = src.read_text(encoding="utf-8")
    if not PUBLISHED.search(text):
        sys.exit(f"_queue/{src.name} に published: の行がありません")
    dest.write_text(PUBLISHED.sub("published: true", text, count=1), encoding="utf-8")
    src.unlink()
    print(f"公開：{slug}（残り {len(queued) - 1} 本）")
    set_output("action", "publish")
    set_output("slug", slug)


if __name__ == "__main__":
    main()
