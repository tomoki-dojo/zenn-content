# zenn-content

どーじょーのZenn記事。Zenn CLIで書いて、GitHubにpushすると公開される（Zennのダッシュボードでこのリポジトリを連携済みの場合）。

## 使い方

```sh
npm install          # 初回だけ
npm run preview      # http://localhost:8000 でプレビュー
npm run new:article  # 新しい記事ファイルを作る
```

- 記事は `articles/<slug>.md`。下書きの間は先頭の `published: false` のまま。公開するときに `true` にしてpushする。
- 画像は `images/<slug>/` に置き、記事からは `/images/<slug>/xxx.png` で参照する。
- 書き方のルールは `CLAUDE.md`。
