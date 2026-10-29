---
title: "絵を1枚も足さずに、虫に20種類のアクションをさせる：CSSアニメーション＋「覚えている動き」を返す関数1つ"
emoji: "🪲"
type: "tech"
topics: ["css", "react", "typescript", "nextjs"]
published: true
---

英語学習アプリ「喋って！育てろ！英クワたん」を個人で作っている、どーじょーです。開発は Claude と一緒にやっています（アプリ全体の話は[前の記事](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)に書きました）。

英クワたんでは、捕まえた虫が棚の水槽を歩き回っています。v1.1.0 で、成虫が**ときどきアクションを見せる**のと、**習得した英語をつぶやく**アクションを入れました。

アクションは全部で 20 種類（共通 12・種ごと 3・特別 5）追加したんですが、虫の絵は 1 枚も足していません。その作り方の話です。

## アクションは「体全体を動かす CSS アニメーション」だけ

虫の絵は、体・脚・大顎などの SVG パーツを組み合わせて歩かせています。アクションのたびに新しいポーズの絵を描くのは大変なので、**虫を包んでいる要素ごと `transform` で動かす**だけにしました。

```css:src/app/globals.css
@keyframes kw-act-hop { 0%,100%{transform:translateY(0)} 20%{transform:translateY(-14%)} 40%{transform:translateY(0)} 60%{transform:translateY(-14%)} 80%{transform:translateY(0)} }
@keyframes kw-act-chew { 0%,100%{transform:scale(1)} 15%,45%,75%{transform:scale(1.06,.94)} 30%,60%,90%{transform:scale(.96,1.04)} }
@keyframes kw-act-bow { 0%,100%{transform:rotate(0)} 40%,70%{transform:rotate(18deg) translateY(4%)} }
```

`hop`（ぴょんぴょん）は上下、`chew`（もぐもぐ）は縦横に潰す、`bow`（ぺこり）は前に傾ける。これだけでも、歩いている虫が急にやると結構かわいいんですよねぇ笑

アクションの名前と長さは TS 側に置いて、CSS の keyframes 名と揃えています。

```ts:src/lib/kuwagata-actions.ts
  hop: { id: "hop", label: "ぴょんぴょん", durationMs: 1400 },
  chew: { id: "chew", label: "もぐもぐ", durationMs: 1500 },
  // …
  beam: { id: "beam", label: "ビーム", durationMs: 2000 },
  "sp-daily": { id: "sp-daily", label: "ほっこり", durationMs: 3600, effect: "glow-pink" },
```

```tsx:src/components/roadmap/kuwagata-shelf.tsx
style={actionId ? { animation: `kw-act-${actionId} ${ACTIONS[actionId].durationMs}ms ease-in-out` } : /* … */ undefined}
```

えー…プレクワたんというクワガタはビームを撃ちます笑

プレクワたんのビームだけは、体を少し揺らすのに加えて、光の玉とビームの線を `span` で重ねています（これも絵ではなく CSS のグラデーションと `box-shadow`）。

## 「この個体が見せられるアクション」を返す関数を 1 つにする

アクションには解放条件がいろいろあります。

- 共通アクション（12 種）：色の実で色づけした個体が、そのシーンのアクションを覚える
- 種ごとのアクション（3 種）：プレクワたん＝ビーム、ネゴクワたん＝地鳴らし、テレクワたん＝電波。（実は他にも種固有のアクションをするやつがいます、お気に入りはコメたん。今回の追加分は 3 種ということです。）
- 特別アクション（5 種）：日常・ビジネスのシーンを全部習得、限定種 8 種コンプ、金銀の縁の個体だけ…

これを画面側で if 文だらけにすると大変なので、「この個体が今見せられるアクションの一覧」を返す関数を 1 つにまとめました。

```ts:src/lib/kuwagata-actions.ts
export function availableActions(
  tintKey: string | null,
  rimKey: "silver" | "gold" | null,
  flags: ActionFlags,
  speciesCode?: string
): ActionId[] {
  const list: ActionId[] = [];
  if (speciesCode && SPECIES_ACTIONS[speciesCode]) list.push(...SPECIES_ACTIONS[speciesCode]);
  const common = tintKey ? COMMON_ACTION_BY_SCENE[tintKey] : undefined;
  if (common) list.push(common);
  if (flags.daily > 0) list.push("sp-daily");
  if (flags.business > 0) list.push("sp-business");
  if (flags.limitedComplete) list.push("sp-limited");
  if (rimKey === "silver" || rimKey === "gold") list.push("sp-silver");
  if (rimKey === "gold") list.push("sp-gold");
  return list;
}
```

入力は「個体の色（tintKey）」「金銀の縁（rimKey）」「ユーザーの達成状況（flags）」「種」の 4 つだけ。達成状況はサーバーで数えて棚に渡しています。

色の実のシーンとアクションの対応も、ただの表です。

```ts:src/lib/kuwagata-actions.ts
export const COMMON_ACTION_BY_SCENE: Record<string, ActionId> = {
  // Stage4
  旅行: "hop",
  外食: "chew",
  // …
  // Stage5
  "住まい・手続き": "stretch",
  "銀行・契約": "nod",
  // …
};
```

Stage4 は 12 シーンに 1 つずつ、Stage5 の 8 シーンは近い動きを使い回しています。純粋な関数と表だけなので、サーバー・ブラウザのどちらからも使えます。

## 動かすタイミングは、個体ごとにずらす

あとは、返ってきた一覧からランダムに選んで、ときどき動かすだけです。

```tsx:src/components/roadmap/kuwagata-shelf.tsx
    const rnd = seededRandom(seedKey + ":action");
    const schedule = () => {
      timer = setTimeout(() => {
        if (cancelled) return;
        const id = list[Math.floor(Math.random() * list.length)];
        setActionId(id);
        timer = setTimeout(() => {
          if (cancelled) return;
          setActionId(null);
          schedule();
        }, ACTIONS[id].durationMs);
      }, 9000 + Math.random() * 14000);
    };
    timer = setTimeout(schedule, rnd() * 6000);
```

間隔は 9〜23 秒。最初の 1 回だけ、個体ごとのシードで 0〜6 秒ずらしているので、水槽を開いた瞬間に全員が同時に動き出す…ということはありません。

## つぶやき：色づいた子は、そのシーンの表現を約 7 割

成虫は、ユーザーが習得した英語の表現を吹き出しでつぶやきます（タップで音声と日本語訳）。色の実で色づけした子は、そのシーンに近い表現を優先します。

```ts:src/lib/kuwagata-murmur.ts
// つぶやく表現を1つ選ぶ。色づけ個体は、そのシーンの表現が約7割。直前と同じものは避ける。
export function pickMurmur(murmurs: Murmur[], tintKey: string | null, previousId: string | null): Murmur | null {
  if (murmurs.length === 0) return null;
  const tags = preferredTagsOf(tintKey);
  const preferred = tags.length > 0 ? murmurs.filter((m) => m.sceneTags.some((t) => tags.includes(t))) : [];
  const pool = preferred.length > 0 && Math.random() < 0.7 ? preferred : murmurs;
  const candidates = pool.length > 1 ? pool.filter((m) => m.id !== previousId) : pool;
  return candidates[Math.floor(Math.random() * candidates.length)] ?? null;
}
```

100%そのシーンにしないのは機械的な印象を避けるためですね。直前と同じ表現も避けています。

つぶやきは、最初が 6〜26 秒後、そのあとは 25〜50 秒ごと。吹き出しは 5 秒で消えますが、タップして訳を開いている間は消えないようにしています。ミュート中は訳だけ出して、音声は鳴らしません。

水槽にいる虫が色んな表現をつぶやくと、「復習」と「勉強してきたなぁ」というのがわかって、眺めているだけでも面白い＆なんとなく復習になります。

## まとめ

- アクションは新しい絵を描かず、虫全体を `transform` で動かす CSS アニメーションにした
- 解放条件は「個体の色・縁・達成状況・種」から一覧を返す純粋関数 1 つに集めた
- タイミングは個体ごとにずらして、水槽全体が同時に動かないようにした
- つぶやきは、色づいたシーンの表現を約 7 割にして、直前と同じものは避けた

色々実装したい、というのとそのコストは考えどころですよねぇ。

## 関連記事

- [元教員が 1 人で「喋って育てる英語＆育成ゲーム」を作って、課金機能まで付けた全体像](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)
- [60 種以上の虫を 20 色に染める：種ごとの「体の色相」を測って CSS の hue-rotate で回す](https://zenn.dev/tomoki_dojo/articles/kuwatan-color-fruit-hue-rotate)
- [ご褒美を「あとから」「二重なく」配る：(user_id, event_key) の台帳テーブル 1 つで遡及付与する](https://zenn.dev/tomoki_dojo/articles/kuwatan-reward-ledger-backfill)

【どーじょー記入：関連記事は未公開のものもあるので、公開順に合わせて残すか消すか】

アプリはこちら：[喋って！育てろ！英クワたん](https://app.upskillenglish.bear-fruit.online/welcome?utm_source=zenn&utm_medium=article&utm_campaign=kuwatan-tank-actions-css)
