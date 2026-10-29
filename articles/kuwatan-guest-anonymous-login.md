---
title: "Supabaseの匿名ログインで「登録なしで試す」を作って、登録時にそのまま引き継ぐ"
emoji: "🪲"
type: "tech"
topics: ["supabase", "nextjs", "typescript", "auth"]
published: true
---

<!-- 自動下書き（2026-10-28）／元にした変更：コミット c8a2fcf「ゲスト体験（匿名ログイン）とGoogleログインを追加」・共有ボード 2026-10-28 [実装]「設計（ゲスト体験・匿名ログイン方式）」「本番デプロイ済み」／【要確認】2・【どーじょー記入】3／コードは c8a2fcf の実ファイルからの抜粋（一部省略） -->

英語学習アプリ「喋って！育てろ！英クワたん」を個人で作っている、どーじょーです。開発は Claude と一緒にやっています（アプリ全体の話は[前の記事](https://zenn.dev/tomoki_dojo/articles/kuwatan-solo-dev-overview)に書きました）。

今回、**登録しなくても少し遊べる「ゲスト体験」**を追加しました。結論から言うと「Supabase の匿名サインインで本物の一時アカウントを作り、登録のときは同じアカウントに Google／メールを紐付ける」方式です。これだと、ゲスト中のデータを本アカウントへ移す処理を書かなくて済みます。

## 背景：最初の一歩が「メールを開く」だった

これまでは /welcome から先が全部ログイン必須で、初めての人は「メールアドレス入力 → メールを開く → リンクを押す」まで何も触れませんでした。

まぁやっぱり「何か入力する」ってのは面倒だし、メール開くのも面倒だし…。でも逆にこういうアプリは登録してもらってなんぼなので…。

そこで「Stage1 を 1 ラウンド → 採集チャンス 1 回 → 虫を 1 匹つかまえる → 棚で見る」までを登録なしで遊べるようにして、あわせてログイン画面に「Google でログイン」も足しました。

## 方式の比較：ローカルに持つか、匿名アカウントか

ゲストのデータを localStorage などに持っておいて登録時にサーバーへ移す、というやり方もありますが、それだと既存の Stage1・採集・棚の API を全部「ゲスト用」に分ける必要が出てきます。

Supabase の `signInAnonymously()` を使うと、匿名でも `auth.users` に本物のユーザーができるので、既存の API・DB トリガー（最初のクワたんのタマゴが届くトリガーなど）がそのまま動きます。ポイントはここですね。ゲスト用の別ルートをほぼ作らずに済むので。

あと、後述しますがそのまま本登録したときにデータの移行も簡単です。

## 1. 「登録なしで試す」ボタン

```tsx:src/components/roadmap/guest-start-button.tsx（抜粋）
const start = async () => {
  setStatus("starting");
  const supabase = createClientBrowser();
  const { error } = await supabase.auth.signInAnonymously();
  if (error) {
    setStatus("error");
    return;
  }
  trackEvent("guest_start");
  window.location.href = `/roadmap/title/enter?next=${encodeURIComponent("/roadmap/stage1")}`;
};
```

押した瞬間に匿名ユーザーができて、タイトル画面経由で Stage1 へ。GA4 に `guest_start` を送っています。

## 2. ゲストが使える範囲はミドルウェアで絞る

匿名でも本物のユーザーなので、放っておくと AI 判定を使う Stage3〜5 や課金ページにも入れてしまいます。お試しなので、そこまでいかれるとコッチもユーザーもお互い lose-lose な状況になっちゃいます。（あんまり匿名で続けられても…＆クッキーが消えたら同じアカウントにログインできない）

```ts:src/lib/guest-access.ts（抜粋）
const GUEST_PAGE_PREFIXES = [
  "/welcome",
  "/auth",
  "/terms",
  "/privacy",
  "/tokushoho",
  "/roadmap/title",
  "/roadmap/stage1",
  "/roadmap/shelf",
  "/roadmap/register",
];

const GUEST_API_PREFIXES = [
  "/api/auth",
  "/api/roadmap/guest",
  "/api/roadmap/stage1",
  "/api/roadmap/kuwagata",
  "/api/roadmap/word-lookup",
];

export function guestGuardDecision(pathname: string): GuestGuardDecision {
  if (pathname.startsWith("/api/")) {
    return GUEST_API_PREFIXES.some((p) => matchesPrefix(pathname, p)) ? "allow" : "api_forbidden";
  }
  return GUEST_PAGE_PREFIXES.some((p) => matchesPrefix(pathname, p)) ? "allow" : "redirect";
}
```

```ts:src/lib/supabase/middleware.ts（抜粋）
const {
  data: { user },
} = await supabase.auth.getUser();

// ゲスト(匿名ログイン)は、Stage1・採集・棚と登録の画面だけ。
if (user?.is_anonymous === true) {
  const decision = guestGuardDecision(request.nextUrl.pathname);
  if (decision === "api_forbidden") {
    return NextResponse.json(
      { error: "登録すると使えます", code: "guest_restricted" },
      { status: 403, headers: { "Cache-Control": "no-store" } }
    );
  }
  if (decision === "redirect") {
    const url = request.nextUrl.clone();
    url.pathname = request.nextUrl.pathname === "/login" ? "/roadmap/register" : "/roadmap/stage1";
    url.search = "";
    const redirect = NextResponse.redirect(url);
    supabaseResponse.cookies.getAll().forEach((c) => redirect.cookies.set(c));
    return redirect;
  }
}
```

許可リスト方式にしているので、あとでページを増やしてもゲストには閉じた状態になります。`guest-access.ts` は Edge のミドルウェアから読むので、node 専用モジュールは入れていません。redirect のときに Cookie を付け直しているのは、`getUser()` で更新されたセッションの Cookie を落とさないためです。

## 3. 採集チャンスは「1 回だけ」をべき等に

普段の採集チャンスは「表現を 10 個習得するごと」ですが、ゲストは Stage1 を 1 ラウンド終えたら 1 回だけ渡します。結果画面を開き直したりしても増えないようにしています。

```ts:src/lib/supabase/guest.ts（抜粋）
export async function grantGuestCatchChance(userId: string): Promise<boolean> {
  const pending = await getPendingCatchState(userId);
  if (pending.pendingCatchCount > 0) return true;

  const { count, error } = await supabaseAdmin
    .from("kuwagata_individuals")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId)
    .eq("obtained_via", "roll");
  if (error) throw new Error(`ゲストの採集履歴の確認に失敗しました: ${error.message}`);
  if ((count ?? 0) > 0) return false;

  const { error: rpcError } = await supabaseAdmin.rpc("add_kuwagata_catch_chance", {
    p_user_id: userId,
    p_guaranteed: false,
  });
  if (rpcError) throw new Error(`採集チャンスの付与に失敗しました: ${rpcError.message}`);
  return true;
}
```

「もうチャンスを持っている」「もう採集で虫をつかまえたことがある」のどちらかなら何もしない、という 2 段のチェックです。呼び出し側の API（`/api/roadmap/guest/round-complete`）は、匿名ユーザー以外が呼んでも `catchChance: false` を返すだけにしています。

なお、ゲストは最初の会話クイズを飛ばして Stage1 から始まるように、`ensureGuestRoadmapState()` で状態を作っています。

## 4. 登録は「新しく作る」のではなく「紐付ける」

ここが一番おいしいところです。登録画面（`/roadmap/register`）では、新規アカウントを作らずに、今の匿名アカウントに Google やメールを紐付けます。

```ts:src/components/roadmap/guest-register-form.tsx（抜粋）
// Google
const { error: linkError } = await createClientBrowser().auth.linkIdentity({
  provider: "google",
  options: { redirectTo: callback() },
});

// メール
const { error: updateError } = await createClientBrowser().auth.updateUser(
  { email },
  { emailRedirectTo: callback() },
);
```

ユーザー ID が変わらないので、つかまえた虫も練習の記録も、何もしなくてもそのまま残ります。引き継ぎ処理を書かなくていいのは結構デカいですね。

すでに登録済みのメールアドレスを入れた場合は「このメールアドレスはすでに登録されています」と出して、「登録済みの方はサインイン」へ（この場合、ゲストのデータは引き継がれません）。

Supabase 側の設定は、ダッシュボードで Anonymous sign-ins を ON、Manual linking を ON、Google プロバイダの設定、です。

## 5. 計測と、残っていること

どこで止まっているかを見るために、GA4 に 4 つのイベントを送っています。

- `guest_start`：「登録なしで試す」を押した
- `guest_caught_bug`：ゲストで虫をつかまえた
- `guest_register_view`：登録の案内が表示された（Stage1 の結果・採集の結果・棚のどこで出たか付き）
- `guest_signup`：ゲストから登録した

残っているのは、登録しないまま 30 日たった匿名アカウントの掃除です。SQL 関数 `cleanup_stale_anonymous_users(days=30)` は用意したんですが、定期実行はまだ設定していません。

## おわりに

まぁ正直これがどのくらい効くのかわかりませんが、匿名で試せる＆Google アカウントでログイン機能は悪くはないはず笑

アプリはこちら：[喋って！育てろ！英クワたん](https://app.upskillenglish.bear-fruit.online/welcome?utm_source=zenn&utm_medium=article&utm_campaign=kuwatan-guest-anonymous-login)
