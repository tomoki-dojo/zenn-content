---
title: "ご褒美を「あとから」「二重なく」配る：(user_id, event_key) の台帳テーブル1つで遡及付与する"
emoji: "🥚"
type: "tech"
topics: ["supabase", "postgresql", "nextjs", "typescript"]
published: false
---

英語学習アプリ「喋って！育てろ！英クワたん」を個人で作っている、どーじょーです。開発は Claude と一緒にやっています（アプリ全体の話は[前の記事](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)に書きました）。

v1.1.0 で、Stage5 の会話のお題を習得するたびに、そのシーンの「限定クワたん」のタマゴが届くようにしました。8 シーンなので、全部やると 8 種です。

で、ここで困るのが**機能を入れる前に Stage5 を進めていた人**。その人たちにも、習得済みのお題の分だけタマゴを配りたい。しかも何回部屋を開いても、2 個目は届かないようにしたい。

これを「台帳」テーブル 1 つでやっている話です。

## 台帳テーブル

```sql:docs/kuwagata_egg_events.sql
create table if not exists public.kuwagata_egg_events (
  user_id uuid not null references auth.users(id) on delete cascade,
  event_key text not null,
  individual_id uuid references public.kuwagata_individuals(id) on delete set null,
  granted_at timestamptz not null default now(),
  primary key (user_id, event_key)
);
```

ポイントは主キーが `(user_id, event_key)` なことですね。「このユーザーに、このイベントのご褒美を渡したか」を 1 行で表します。

`event_key` は文字列で、用途ごとにプレフィックスを変えています。

- `limited:<シナリオID>`：限定クワたんのタマゴ（お題ごとに 1 つ）
- `rim:silver` / `rim:gold`：銀星・金星のカケラ
- `rare:50` など：レア確定チャンスのお知らせ

テーブルを用途ごとに作らずに済むので、ご褒美を足すたびにマイグレーションしなくていいのが楽です。

## 「習得済み − 台帳にあるもの」を配る

配る処理は、イベントが起きた瞬間（習得した瞬間）ではなく、**部屋を開いたとき**に呼んでいます。

```ts:src/lib/supabase/kuwagata-egg-events.ts
// Stage5のシナリオを習得した分だけ、そのシーンの限定種の卵を配る（部屋に入ったときに呼ぶ）。
// 習得済みのシナリオごとに台帳へ「limited:<シナリオID>」を記録するので、二重には配らない。
// 機能の追加前に習得済みだったシナリオも、初回の呼び出しでまとめて配られる。
export async function grantLimitedEggs(userId: string, loadGrantedKeys?: LoadGrantedKeys): Promise<void> {
  // …公開中のStage5シナリオと、そのユーザーの習得済みシナリオを取得…

  const grantedKeys = await (loadGrantedKeys ?? createGrantedKeysLoader(userId))();
  const pending = masteredIds.filter((id) => !grantedKeys.has(`${LIMITED_EVENT_PREFIX}${id}`));
  if (pending.length === 0) return;
  // …
```

要は「今の習得状況」と「台帳」の差分を配っているだけです。なので

- 機能を入れる前に習得していた人 → 初めて部屋を開いたときに、まとめて届く（遡及付与）
- もう配った人 → 差分がないので何も起きない

という動きが、特別な移行スクリプトなしで実現できます。「習得した瞬間に配る」作りだと、過去の分を配るバッチを別に書く必要があったはずなので、ここはこの形にしてよかったところです。

## 先に台帳に書いてから、虫を作る

同じユーザーが 2 つの画面で同時に部屋を開くと、どちらも「まだ配ってない」と判断しちゃいます。なので、虫を作る前に台帳に書き込んで、**書き込めた方だけ**が配ります。

```ts:src/lib/supabase/kuwagata-egg-events.ts
    // 先に台帳へ記録して、同時に開いた別の画面と二重に配らないようにする。
    const { data: claimed, error: claimError } = await supabaseAdmin
      .from("kuwagata_egg_events")
      .upsert({ user_id: userId, event_key: eventKey }, { onConflict: "user_id,event_key", ignoreDuplicates: true })
      .select("event_key");
    if (claimError) throw new Error(`限定種のタマゴの配布記録に失敗しました: ${claimError.message}`);
    if ((claimed?.length ?? 0) === 0) continue;
```

`ignoreDuplicates: true` の upsert は、すでに行があると何も返しません。返ってきた行が 0 件なら「別の画面が先に取った」ということなので、スキップします。主キーの一意制約に判定を任せているので、アプリ側でロックを取らなくていいんですよねぇ。

## 虫の作成に失敗したら、台帳を戻す

台帳を先に書くと、今度は「台帳には書いたのに、虫の作成に失敗した」ときに、二度と配られなくなります。なのでその場合は台帳の行を消して、次に部屋を開いたときにやり直せるようにしています。

```ts:src/lib/supabase/kuwagata-egg-events.ts
    if (insertError || !inserted) {
      await supabaseAdmin.from("kuwagata_egg_events").delete().eq("user_id", userId).eq("event_key", eventKey);
      throw new Error(`限定種のタマゴの登録に失敗しました: ${insertError?.message ?? "不明なエラー"}`);
    }

    await supabaseAdmin
      .from("kuwagata_egg_events")
      .update({ individual_id: inserted.id })
      .eq("user_id", userId)
      .eq("event_key", eventKey);
```

成功したら、作った虫の ID を台帳に残しておきます。「どのイベントでどの虫が届いたか」があとから追えます。

ちなみに、限定種がまだ公開されていないシーンは `continue` で飛ばしていて、台帳にも書きません。なので、あとから限定種を公開すれば、その時点で過去の習得分が届きます。

## 台帳の読み込みは 1 回にまとめる

部屋を開いたときには、限定種のタマゴ・金銀のカケラ・レア確定のお知らせ…と、台帳を見る処理がいくつも走ります。毎回 SELECT するのはもったいないので、読み込みを 1 回にまとめる関数を渡せるようにしています。

```ts:src/lib/supabase/kuwagata-egg-events.ts
export function createGrantedKeysLoader(userId: string): LoadGrantedKeys {
  let cached: Promise<Set<string>> | null = null;
  return () => {
    cached ??= (async () => {
      const { data, error } = await supabaseAdmin
        .from("kuwagata_egg_events")
        .select("event_key")
        .eq("user_id", userId);
      if (error) throw new Error(`タマゴの配布記録の取得に失敗しました: ${error.message}`);
      return new Set((data ?? []).map((row) => row.event_key as string));
    })();
    return cached;
  };
}
```

Promise ごとキャッシュしているので、同時に呼ばれても読み込みは 1 回です。

## まとめ

- `(user_id, event_key)` を主キーにした台帳テーブル 1 つで、いろんなご褒美の「渡したか」を管理する
- 「今の状況 − 台帳」の差分を配る作りにすると、機能追加前の人への遡及付与がタダでついてくる
- 二重配布は、先に台帳へ `upsert(ignoreDuplicates)` して、書けた方だけが配ることで防ぐ
- 後の処理が失敗したら台帳を消して、次回やり直せるようにする

こういうイベントの処理ってタイミングが難しいですよね…。色々と考えないといけないことも多いですが、こういう細かい処理は丁寧にやっていきたいところです。

## 関連記事

- [元教員が 1 人で「喋って育てる英語＆育成ゲーム」を作って、課金機能まで付けた全体像](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)
- [60 種以上の虫を 20 色に染める：種ごとの「体の色相」を測って CSS の hue-rotate で回す](https://zenn.dev/tomoki_dojo/articles/kuwatan-color-fruit-hue-rotate)
- [絵を 1 枚も足さずに、虫に 20 種類のアクションをさせる：CSS アニメーション＋「覚えている動き」を返す関数 1 つ](https://zenn.dev/tomoki_dojo/articles/kuwatan-tank-actions-css)

アプリはこちら：[喋って！育てろ！英クワたん](https://app.upskillenglish.bear-fruit.online/welcome?utm_source=zenn&utm_medium=article&utm_campaign=kuwatan-reward-ledger-backfill)
