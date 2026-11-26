---
name: appstore-capture
description: >-
  App Store 提出用スクリーンショットを iOS シミュレータから「ネイティブ解像度で直接」撮る。サンプルデータ投入・権限付与・ステータスバーの固定・アルファ除去・寸法と提出先の枠の検証・デスクトップ複製まで自動実行する。引数でスロットを指定（例: /appstore-capture iphone-6.3）。既存の画像を別の寸法へ変換するなら /appstore-screenshots を使う。
---

<!-- 配布元: https://github.com/nzw/claude-code-skills
     capture.sh と同じフォルダに置いてください（個人なら ~/.claude/skills/appstore-capture/、リポジトリなら .claude/skills/appstore-capture/）。
     寸法の表は 2026-10-14 に App Store Connect の画面で、2026-11-25 に Apple の仕様の表で確かめた値です。提出の前に、枠に表示される対応サイズと突き合わせてください。 -->

# /appstore-capture — App Store スクリーンショット撮影スキル

シミュレータの**ネイティブ解像度がそのまま提出サイズ**になる機種で撮る。
拡大縮小しないので、文字がにじまず、円が楕円に潰れることもない。

> **既にある画像を別の寸法へ変換するのは `/appstore-screenshots` の担当。** 変換は情報が減るだけで
> 増えないので、撮り直せるなら撮り直す。

---

## 実行

```bash
bash <このスキルのフォルダ>/capture.sh <config> [スロット名...]
# 個人に入れたなら   ~/.claude/skills/appstore-capture/capture.sh
# リポジトリに入れたなら .claude/skills/appstore-capture/capture.sh
```

プロジェクト側にラッパーがあるならそれを使う（例: `bash tool/screenshots.sh iphone-6.3`）。
スロット名を省略すると conf の全スロットを撮る。
`SKIP_BUILD=1` を付けるとビルド済みアプリを再利用する（スロット追加時に有効）。
提出できない画像が 1 枚でもあると、最後に終了コード 1 で止まる。ビルドの失敗は `<OUT_DIR>/build-<SHOT>.log` に全文が残る。

---

## 提出サイズ（ここを間違えると弾かれる）

**スロットごとに許容寸法が違う。** 「1個以上のスクリーンショットの寸法が正しくありません」は
たいてい別スロット用の画像を入れているのが原因。

**必須の iPhone の枠は「Dynamic Island 搭載 iPhone（中型ディスプレイ）」。**
2026-10-14 に App Store Connect の画面で確かめ、2026-11-25 に Apple の
[Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications)
と突き合わせた。中型の枠が受け付けるのは **1206×2622 / 1179×2556 だけ**（アプリプレビューは
1920×886 / 886×1920）。**6.5" の 1242×2688 をこの枠へ上げたら、6 枚とも「サイズが無効です」で弾かれた。**
1242×2688 は古い寸法ではなく、6.5" の枠の寸法。枠を取り違えたのが原因。

| 枠 | 許容寸法 | ネイティブな機種（シミュレータ） |
| --- | --- | --- |
| **iPhone 中型（6.3"・6.1"）★必須** | **1206×2622** / 1179×2556 | **iPhone 17 / 17 Pro**（1206×2622）、iPhone 16 / 15 Pro（1179×2556） |
| iPhone 大型（6.9"・6.7"） | 1320×2868 / 1290×2796 / 1260×2736 | iPhone 16 Pro Max / 17 Pro Max（1320×2868） |
| iPhone Face ID 大型（6.5"） | 1284×2778 / 1242×2688 | iPhone 11 Pro Max（1242×2688） |
| iPhone Face ID 中型（6.1"・5.8"） | 1170×2532 / 1125×2436 / 1080×2340 | iPhone 13 / 14（1170×2532） |
| iPad 13"（iPad で動くなら必須） | 2064×2752 / 2048×2732 | iPad Pro 13-inch (M4/M5) |

横向きは幅と高さを入れ替えた寸法も可。**画面のドロップ欄の下に書いてある対応サイズが正。**
表と食い違ったら、画面に合わせて表と `capture.sh` の `SLOT_OF` を直す。

`capture.sh` は撮った画像ごとに **「上げる枠」** を出す。どの枠にも当たらない寸法と、
conf の期待寸法と違うものは NG。conf に中型の枠の寸法が 1 つも無いときは、最後に警告を出す。

> **大きい枠に上げた画像は、小さい枠へ縮小して流用される**。これは
> **小さい枠を空のままにした場合**の話。App Store Connect の画面で
> 別の枠に自分でドラッグすると、その枠の寸法で検証される。
> 枠に入れるなら、その枠のサイズで撮ること。

必要な機種が無ければ作る:

```bash
xcrun simctl list devicetypes | grep -i "iPhone 17"
xcrun simctl create AS-iPhone63 com.apple.CoreSimulator.SimDeviceType.iPhone-17
```

`AS-` 接頭辞は撮影専用デバイスの目印。普段の開発用シミュレータと混ざらないようにする。

---

## 設定ファイル

プロジェクトに 1 つ置く（例: `tool/appstore-capture.conf`）。Flutter プロジェクトの中ならどこでもよい。
`capture.sh` は conf の場所から上へたどって `pubspec.yaml` を探し、そこをプロジェクトとして扱う。

```bash
BUNDLE_ID="jp.example.app"
SHOT_ENTRYPOINT="lib/main_shot.dart"   # 撮影専用エントリポイント
SHOT_DEFINE="SHOT"                     # 画面切り替えの dart-define 名
SHOTS=(01:search 02:library 03:detail) # <連番>:<SHOT 値>
SLOTS=(                                # <出力名>:<機種名>:<幅>:<高さ>
  "iphone-6.3:AS-iPhone63:1206:2622"
  "ipad-13:iPad Pro 13-inch (M5):2064:2752"
)
SEED_SCRIPT="tool/seed_prefs.py"       # 任意。plist パスを引数に取る
TCC_SERVICES=(kTCCServiceMicrophone)   # 任意。事前に許可しておく権限
OUT_DIR="build/appstore-shots"
DESKTOP_DIR="$HOME/Desktop/MyApp-appstore-shots"
LAUNCH_WAIT=7
```

---

## 撮影専用エントリポイントが要る理由

**`simctl` だけではタップを送れない。**（XCUITest などを組めば送れるが、撮影のためだけに持つには重い）
そのため「撮りたい画面を起動時の `home` に直接差し込む」エントリポイントを別に持つ。

```dart
// lib/main_shot.dart
const _shot = String.fromEnvironment('SHOT', defaultValue: 'library');

Widget _pageFor(String name) => switch (name) {
  'search' => const SearchPage(initialQuery: '会'),
  'detail' => const EntryDetailPage(entryId: 'seed-002'),
  _ => const LibraryPage(),
};

// MaterialApp に debugShowCheckedModeBanner: false が必須。
// シミュレータビルドは debug なので、これが無いと DEBUG リボンが写り提出できない。
```

画面によっては、撮影のためだけに既定 off のフラグを足すことになる
（起動直後に検索欄へ語を入れる、設定画面を飛ばしてカードから始める、など）。
**通常動作に影響しない形で入れ、消さない。**

---

## スクリプトがやること

1. `SHOT` ごとにシミュレータ向けビルド（スロット間で `.app` を使い回す）
2. 一度起動してデータコンテナのパスを控える
3. **停止してから** サンプルデータを書き、TCC に権限を書く
4. 起動 → ステータスバーを固定 → 画面ごとに install / launch / 待機 / **ステータスバーを掛け直す** / `simctl io screenshot`
5. アルファを白背景で合成して除去し、**寸法と上げる枠を検証**
6. `DESKTOP_DIR` へ複製（スロット単位で作り直すので古い画像が混ざらない）
7. 提出できない画像があれば、終了コード 1 で止まる

---

## 落とし穴（すべて実際に踏んだもの）

- **サンプルデータの書き込みは必ず停止中に。** 起動中に plist を直接書くと
  `cfprefsd` がメモリ上のキャッシュを後から書き戻して**消える**。
  iPad で実際にこれが起き、真っ白なスクリーンショットが撮れた
- **`get_app_container` は起動中しか引けない。** だから
  「起動 → パスを控える → 停止 → 書く → 起動」という順序になる
- **ステータスバーは撮る直前に固定し直す。** `simctl status_bar ... override` は、端末が
  起動していないと終了コード 0 のまま黙って効かない。入れ直しや再起動でも元に戻る。
  固定しないと、撮った時刻と電池の残量がそのまま写る（実時刻の「16:17」が写って気づいた）
- **アルファは必ず落とす。** `simctl io screenshot` の PNG は RGBA。
  App Store は RGB のみ受け付ける
- **DEBUG リボン。** シミュレータビルドは常に debug。
  `debugShowCheckedModeBanner: false` が無いと提出できない画像になる
- **白紙判定を閾値でやらない。** iPad は余白が広く、正常な画面でも背景色が 97% を占める。
  **最後は必ず目視する**
- **実行中のスクリプトを編集しない。** bash はスクリプトを逐次読むため、
  編集でバイト位置がずれて `syntax error near unexpected token` が出る。
  処理自体は途中まで正常に終わっていることがあり、原因を誤診しやすい
- **全角文字が直後に来る変数展開は `${VAR}` と囲む。** ロケールが `C.UTF-8` だと
  bash が全角括弧のバイト列を識別子に取り込み、`$VAR）` が別名になって
  `unbound variable` で落ちる

---

## 撮ったあと（必ず目視する）

Read ツールで実際に画像を開き、次を確認する。**寸法が合っていることと、
見た目が良いことは別。**

- DEBUG リボン・権限ダイアログ・空の画面が写っていないか
- サンプルデータが期待どおり描画されているか
- **iPad で余白が過大になっていないか。** iPhone 向けレイアウトのまま iPad で撮ると、
  内容が上部 1/3 に寄って文字が相対的に小さくなる。寸法は通るが訴求力が落ちる。
  一覧系の画面は埋まりやすく、カード / 詳細系は空きやすい

問題が無ければ App Store Connect の該当スロットへドラッグする。
