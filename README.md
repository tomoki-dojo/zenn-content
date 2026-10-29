# zenn-content

どーじょーのZenn記事。Zenn CLIで書いて、GitHubにpushすると公開される（Zennのダッシュボードでこのリポジトリを連携済みの場合）。

## 使い方

```sh
npm install          # 初回だけ
npm run preview      # http://localhost:8000 でプレビュー
npm run new:article  # 新しい記事ファイルを作る
```

- 記事は `articles/<slug>.md`。下書きの間は先頭の `published: false` のまま。
- **公開するときは `_queue/` に移す**（`articles/` で直接 `true` にしてまとめてpushすると、Zennの「直近24時間の投稿数の上限」で弾かれる）。
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

## 1日1本の自動公開（GitHub Actions）

Zennは直近24時間に公開できる本数に上限がある（本数は非公開。まとめてpushすると1本しか通らないことがある）。そこで、公開待ちの記事は `_queue/` に置いて、GitHub Actions が毎朝7:30（日本時間）に1本ずつ公開する。

- 公開したい記事は `_queue/<番号>_<slug>.md` に置く（例：`_queue/04_kuwatan-xxx.md`）。番号の小さい順に出る。`published: false` のままでよい（移すときに `true` にする）
- 置いたらcommit・pushしておく。あとは自動
- 前の日の記事が上限で弾かれていたら、その日は新しい記事を出さずに再デプロイだけする（公開されたかは `https://zenn.dev/api/articles/<slug>` で確認）
- 今すぐ1本出したいときは、GitHubの「Actions」タブ →「Zennに1日1本公開」→「Run workflow」
- 中身：`.github/workflows/zenn-publish-daily.yml`、`.github/scripts/publish_next.py`
- 初回だけ：GitHubのリポジトリの Settings → Actions → General →「Workflow permissions」を「Read and write permissions」にする
