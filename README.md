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

## プレビューのしかた

```
npm run preview
```

→ http://localhost:8000 を開く（止めるときは Ctrl + C）

- Zenn CLI は Node 22.12以上が必要。Macの Node は 18 のままなので、`npm run preview` の中で `npx -p node@22` を使い、そのときだけ Node 22 で動かしている
- 直接打つなら：`npx -y -p node@22 node node_modules/.bin/zenn preview`
- Macの Node を22以上に上げたら、package.json の scripts を `zenn preview` に戻してよい
