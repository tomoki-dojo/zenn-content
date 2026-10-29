---
title: "60種以上の虫を20色に染める：種ごとの「体の色相」を測ってCSSのhue-rotateで回す"
emoji: "🎨"
type: "tech"
topics: ["css", "typescript", "nextjs", "react"]
published: true
---

英語学習アプリ「喋って！育てろ！英クワたん」を個人で作っている、どーじょーです。開発は Claude と一緒にやっています（アプリ全体の話は[前の記事](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)に書きました）。

v1.1.0 で「色の実」という機能を入れました。Stage4・5 で会話のお題を習得するとシーンごとの色の実がもらえて、成虫にあげるとその色に染まる、というものです。

色は全 20 色（Stage5 の 8 シーン＋ Stage4 の 12 シーン）。染める対象の虫は、色づけの基準表に入っているだけで 61 種あります（そのうち無彩色扱いは 1 種）。

この記事ではいわゆる「画像の色変え」のためにやったことを書きます。

## まずは素直に hue-rotate…だとダメだった

色づけは CSS の `filter: hue-rotate()` でやっています。

要は**その画像に使っている色の色相をそれぞれ同じだけ回す**んですね。

体・羽・ツノなどの色の違いは残したまま、全体の色味だけ回せるので、SVG の塗りを 1 枚ずつ書き換えるよりずっと楽です。ていうか、全部塗り直しなんか拷問ですよ笑。

ただ、全部の虫を同じ角度で回すと、**元の色が違うので仕上がりの色がバラバラ**になります。赤い虫を 120° 回すと緑っぽくなりますが、青い虫を 120° 回すと赤っぽくなる。「交渉の実（緑っぽくなる）をあげたのに、虫によって色が全然違う」になっちゃうんですよねぇ。

## 種ごとに「体のおもな色の色相」を持たせる

そこで、種ごとに「体のおもな色」の色相を表にしました。

```ts:src/lib/kuwagata-base-hue.ts
// 種ごとの「体のおもな色」の色相（度）。public/roadmap/kuwagata の正面の体・羽のSVGから、
// 彩度の高い色を重み付けして平均した値（色の実で色づけするときの回転角の基準に使う）。
// 灰色・白・黒が主体でほぼ無彩色の種はnull（色相を回しても変わらないので、別の方法で色を付ける）。
// 新しい種のアートを足したら、ここにも追記する（無い種は、色の実ごとの固定の角度で回す）。
export const KUWAGATA_BASE_HUE: Record<string, number | null> = {
  "KW-0001": 0,
  "KW-0002": 25,
  "KW-0003": 176,
  // …
  "KW-0063": 299,
  "KW-0064": 350,
  "KW-0065": 176,
  "KW-0066": 94,
};
```

SVG の彩度の高い色を重み付けして平均した値です。画像は Claude が参照できるので Claude に測ってもらいました。

あとは「色の実の色相 − 体の色相」だけ回せば、どの虫でも体のおもな色が実と同じ色相になります。

```ts:src/lib/kuwagata-tint.ts
export function tintFilter(key: string | null | undefined, speciesCode?: string): string | undefined {
  if (!key) return undefined;
  const deg = shizukuHueDeg(key);
  if (deg === null) return undefined;
  if (speciesCode && speciesCode in KUWAGATA_BASE_HUE) {
    const target = shizukuTargetHue(key);
    const base = KUWAGATA_BASE_HUE[speciesCode];
    if (target !== null) {
      if (base === null) {
        // セピア色の色相はおよそ38度
        return `sepia(1) saturate(1.6) hue-rotate(${(((target - 38) % 360) + 360) % 360}deg)`;
      }
      return `hue-rotate(${(((target - base) % 360) + 360) % 360}deg)`;
    }
  }
  return `hue-rotate(${deg}deg)`;
}
```

ポイントは `base === null` の分岐ですね。灰色・白・黒が主体の虫は、色相を回しても色がないので何も変わりません。なので一度 `sepia(1)` で茶色っぽく色を付けて（セピアの色相はだいたい 38°）、そこから回しています。

コードの中の名前が `shizuku` なのは、最初「色のしずく」という名前だった名残です笑

## 20 色を、隣どうしが似ないように散らす

各シーンの色（回す角度）は、手で決めずに計算で出しています。

```ts:src/lib/kuwagata-tint.ts
// 隣り合うシーンの角度が大きく離れるように、7刻み（18°×7=126°）で散らす。
// 20個で1周するので、20個までは角度が重ならない。
const HUE_STEP_DEG = 18;
const HUE_SPREAD = 7;

export function shizukuHueDeg(key: string): number | null {
  const index = (SHIZUKU_SCENES as readonly string[]).indexOf(key);
  if (index < 0) return null;
  const slot = (index * HUE_SPREAD) % SHIZUKU_SCENES.length;
  // 0°（変化なし）は避けて、1つ目から始める
  return ((slot + 1) * HUE_STEP_DEG) % 360;
}
```

360° を 20 等分すると 18° 刻み。ただ、順番に 18° ずつにすると、Stage5 の「住まい・手続き」と「銀行・契約」みたいに並んでいるシーンの色がほぼ同じになっちゃいます。

そこで、`index × 7 を 20 で割った余り` で並べ替えています。7 と 20 は互いに素なので、20 個が全部別の場所に入って…簡単に説明すると**隣どうしは 126° 離れます**。

まぁ、それでも 18° しか違わない色の組はあるので、「隣り合う色が見分けにくい実がある」のは許容しました。

## 金・銀の縁は drop-shadow を重ねる

Stage4・5 を全部習得すると、「銀星・金星のカケラ」というアイテムも手に入る、という設定にしました。輪郭を光らせる＆特別なアクションをしはじめる、というアイテムです。

こっちは体の色を変えずに縁だけ光らせたいので、`drop-shadow` を重ねています。

```ts:src/lib/kuwagata-tint.ts
export function rimFilter(rim: RimKey | null | undefined): string | undefined {
  if (!rim) return undefined;
  const c = RIM_COLOR[rim];
  return `drop-shadow(0 0 1.2px ${c.edge}) drop-shadow(0 0 1.2px ${c.edge}) drop-shadow(0 0 4px ${c.edge}) drop-shadow(0 0 14px ${c.glow})`;
}
```

細い影を 2 回重ねて「縁取り」、少し広い影と大きいぼかしで「光」を出しています。色づけの `filter` のあとにつなげるので、色の実と金銀は両立します。

## まとめ

- `hue-rotate` を全種同じ角度で回すと、元の色の違いで仕上がりがバラバラになる
- 種ごとに「体のおもな色相」を持たせて、「目標の色相 − 体の色相」だけ回す
- 無彩色の種は `sepia()` で一度色を付けてから回す

色相環基準で回すと、機械的に計算で再配色ができるから楽チンですね。

## 関連記事

- [元教員が 1 人で「喋って育てる英語＆育成ゲーム」を作って、課金機能まで付けた全体像](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)
- [ご褒美を「あとから」「二重なく」配る：(user_id, event_key) の台帳テーブル 1 つで遡及付与する](https://zenn.dev/tomoki_dojo/articles/kuwatan-reward-ledger-backfill)
- [絵を 1 枚も足さずに、虫に 20 種類のアクションをさせる：CSS アニメーション＋「覚えている動き」を返す関数 1 つ](https://zenn.dev/tomoki_dojo/articles/kuwatan-tank-actions-css)

アプリはこちら：[喋って！育てろ！英クワたん](https://app.upskillenglish.bear-fruit.online/welcome?utm_source=zenn&utm_medium=article&utm_campaign=kuwatan-color-fruit-hue-rotate)
