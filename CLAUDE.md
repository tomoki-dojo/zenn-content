# Zenn記事の書き方ルール（Claude向け）

## 位置づけ

- Zennは「エンジニア向けの開発記」の場。英クワたん（喋って！育てろ！英クワたん／UpskillEnglish）の流入源＋技術の実績づくりが目的。
- 方針の詳細は english-journal-stock の `_reference/monetization-strategy-memo.md` 11章。

## 書き方

- 実録・体験ベース。実際の数字（AI判定のコスト、回数の上限、課金の設計など）を出す。数字は上のメモの実測値を使い、推測の数字は推測と書く。
- 営業色は控えめに。アプリへの誘導は記事末のリンク＋プロフィール程度。
- アプリへのリンクには `utm_source=zenn&utm_medium=article&utm_campaign=<slug>` を付ける。
- 記事は `published: false` のまま書き、公開はどーじょーが判断する。Claudeは勝手に `true` にしない。
- 公開は `_queue/` に置くと GitHub Actions が1日1本ずつ行う（README参照）。`_queue/` に入れる＝公開の判断なので、Claudeはどーじょーの指示なしに `_queue/` へ移さない。
- 1記事1テーマ。関連記事は記事末で相互にリンクする。

## frontmatter

```yaml
---
title: ""
emoji: "🪲"
type: "tech" # 技術記事: tech / アイデア: idea
topics: [] # 最大5つ。英小文字・数字
published: false
---
```
