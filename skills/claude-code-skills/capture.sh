#!/bin/bash
# App Store スクリーンショットを iOS シミュレータから直接撮る（汎用）
#
#   bash <このスキルのフォルダ>/capture.sh <config> [スロット名...]
#
# 設定はプロジェクト側の conf に置く（例: tool/appstore-capture.conf）。
# conf は Flutter プロジェクトの中ならどこでもよい（上へたどって pubspec.yaml を探す）。
#
# 終了コード: 提出できない画像（どの枠にも当たらない寸法・conf と違う寸法）が 1 枚でもあれば 1。
# リサイズはしない。**必ずネイティブ解像度の機種で撮る**（引き伸ばすと文字がにじみ、円が潰れる）。
#
# conf で定義する変数:
#   BUNDLE_ID       アプリのバンドル ID
#   SHOT_ENTRYPOINT 撮影用 Dart エントリポイント（例: lib/main_shot.dart）
#   SHOT_DEFINE     画面切り替えに使う dart-define 名（既定 SHOT）
#   SHOTS           "<連番>:<SHOT 値>" の配列
#   SLOTS           "<出力名>:<シミュレータ機種名>:<幅>:<高さ>" の配列
#   SEED_SCRIPT     （任意）plist パスを引数に取るサンプルデータ投入スクリプト
#   TCC_SERVICES    （任意）事前許可する TCC サービス名の配列
#   OUT_DIR         出力先（既定 build/appstore-shots）
#   DESKTOP_DIR     （任意）複製先。Finder から提出するとき用
#   LAUNCH_WAIT     起動後の待ち秒数（既定 7）

set -euo pipefail

# 注: 全角文字が直後に来る変数展開は必ず ${VAR} と囲むこと。
# ロケールが C.UTF-8 だと bash が全角括弧のバイト列を識別子に取り込み、
# `$VAR）` が別名になって set -u で落ちる。
log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m[x] %s\033[0m\n' "$*" >&2; exit 1; }

CONFIG="${1:-}"
[ -n "$CONFIG" ] && [ -f "$CONFIG" ] || die "設定ファイルを指定すること: capture.sh <config> [スロット名...]"
shift

# conf の置き場所から上へたどり、pubspec.yaml のあるフォルダをプロジェクトとする。
# 以前は「conf の 2 つ上」と決め打ちしていて、conf をプロジェクト直下に置くと 1 つ上で動いた。
CONFIG="$(cd "$(dirname "$CONFIG")" && pwd)/$(basename "$CONFIG")"
find_project_dir() {
  local d; d="$(dirname "$CONFIG")"
  while [ "$d" != "/" ]; do
    [ -f "$d/pubspec.yaml" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}
PROJECT_DIR="$(find_project_dir)" || die "pubspec.yaml が見つからない（conf は Flutter プロジェクトの中に置くこと）: $CONFIG"

SHOT_DEFINE="SHOT"
OUT_DIR="build/appstore-shots"
DESKTOP_DIR=""
SEED_SCRIPT=""
LAUNCH_WAIT=7
TCC_SERVICES=()
# shellcheck disable=SC1090
source "$CONFIG"

cd "$PROJECT_DIR"
[ -n "${BUNDLE_ID:-}" ]       || die "conf に BUNDLE_ID が無い"
[ -n "${SHOT_ENTRYPOINT:-}" ] || die "conf に SHOT_ENTRYPOINT が無い"
[ "${#SHOTS[@]}" -gt 0 ]      || die "conf に SHOTS が無い"
[ "${#SLOTS[@]}" -gt 0 ]      || die "conf に SLOTS が無い"
[[ "$OUT_DIR" = /* ]] || OUT_DIR="$PROJECT_DIR/$OUT_DIR"

command -v xcrun >/dev/null || die "xcrun が無い（Xcode を入れること）"
python3 -c "import PIL" 2>/dev/null || die "Pillow が必要: pip3 install Pillow"

# 引数でスロットを絞れる。省略時は conf の全スロット。
WANTED=("$@")

udid_for() {
  xcrun simctl list devices available -j | python3 -c "
import json,sys
name=sys.argv[1]
for rt,devs in json.load(sys.stdin)['devices'].items():
    if 'iOS' not in rt: continue
    for d in devs:
        if d['name']==name and d.get('isAvailable'):
            print(d['udid']); sys.exit(0)
sys.exit(1)
" "$1" || die "シミュレータが見つからない: $1
   作る場合: xcrun simctl create '$1' <device-type-id>
   一覧:     xcrun simctl list devicetypes"
}

grant_tcc() {
  local udid="$1"
  [ "${#TCC_SERVICES[@]}" -gt 0 ] || return 0
  local tcc="$HOME/Library/Developer/CoreSimulator/Devices/$udid/data/Library/TCC/TCC.db"
  [ -f "$tcc" ] || { warn "TCC.db が無いので許可設定を飛ばす"; return 0; }
  for svc in "${TCC_SERVICES[@]}"; do
    sqlite3 "$tcc" "INSERT OR REPLACE INTO access
      (service, client, client_type, auth_value, auth_reason, auth_version,
       indirect_object_identifier, flags)
      VALUES ('$svc','$BUNDLE_ID',0,2,2,1,'UNUSED',0);" 2>/dev/null \
      || warn "TCC への書き込みに失敗（${svc}）"
  done
}

# ステータスバーの時刻・電池・電波を固定する。撮った時刻が画像に残らないように。
# 端末が起動していないと、終了コード 0 のまま黙って効かない。入れ直しや再起動でも戻るので、
# 起動のあとと、撮る直前の両方で掛ける。
fix_status_bar() {
  xcrun simctl status_bar "$1" override --time "9:41" \
    --batteryState charged --batteryLevel 100 \
    --dataNetwork wifi --wifiMode active --wifiBars 3 >/dev/null 2>&1 \
    || warn "ステータスバーを固定できなかった（時刻がそのまま写る）"
}

# simctl の PNG は RGBA。App Store はアルファ無しの RGB しか受け付けない。
# 併せて解像度も検証する（合っていないと提出時に弾かれる）。
finalize_png() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
from PIL import Image
path, want_w, want_h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
im = Image.open(path)
if im.mode in ('RGBA', 'LA', 'P'):
    im = im.convert('RGBA')
    bg = Image.new('RGB', im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[-1])
    im = bg
else:
    im = im.convert('RGB')
im.save(path, 'PNG', optimize=True)
w, h = im.size
# **寸法だけで「提出できる」と言わない。どの枠に上げる画像かまで出す。**
# 枠ごとに受け付ける寸法が違う。2026-10-14、6.5" 1242x2688 を OK と出したが、
# それを必須の「中型ディスプレイ」枠へ上げて 6 枚とも「サイズが無効です」で弾かれた。
# 1242x2688 自体は 6.5" の枠なら通る（古い寸法でもない）。枠を取り違えたのが原因。
# 表は Apple の Screenshot specifications（2026-11-25 に突き合わせ）と
# App Store Connect の画面（2026-10-14）。画面のドロップ欄の対応サイズが正。
SLOT_OF = {
    (1206, 2622): 'iPhone 中型（6.3"・6.1"）★必須の枠',
    (1179, 2556): 'iPhone 中型（6.3"・6.1"）★必須の枠',
    (1320, 2868): 'iPhone 大型（6.9"・6.7"）',
    (1290, 2796): 'iPhone 大型（6.9"・6.7"）',
    (1260, 2736): 'iPhone 大型（6.9"・6.7"）',
    (1284, 2778): 'iPhone Face ID 大型（6.5"）',
    (1242, 2688): 'iPhone Face ID 大型（6.5"）',
    (1170, 2532): 'iPhone Face ID 中型（6.1"・5.8"）',
    (1125, 2436): 'iPhone Face ID 中型（6.1"・5.8"）',
    (1080, 2340): 'iPhone Face ID 中型（6.1"・5.8"）',
    (2064, 2752): 'iPad 13"',
    (2048, 2732): 'iPad 13"',
}
SLOT_OF.update({(h_, w_): name + '・横' for (w_, h_), name in list(SLOT_OF.items())})
ok = (w, h) == (want_w, want_h)
slot = SLOT_OF.get((w, h))
tag = 'OK ' if (ok and slot) else 'NG '
print(f'    {tag} {w}x{h} (期待 {want_w}x{want_h}) alpha=no  {path.split("/")[-1]}')
if slot:
    print(f'        -> 上げる枠: {slot}')
else:
    print('        -> 提出できない寸法: App Store Connect のどの枠の寸法とも一致しない（SKILL.md「提出サイズ」）')
if not ok:
    print('        -> conf の期待寸法と違う。機種名（SLOTS）を確かめる')
sys.exit(0 if (ok and slot) else 1)
PY
}

build_shots() {
  mkdir -p "$OUT_DIR/apps"
  for pair in "${SHOTS[@]}"; do
    local shot="${pair##*:}"
    if [ "${SKIP_BUILD:-0}" = "1" ] && [ -d "$OUT_DIR/apps/$shot/Runner.app" ]; then
      echo "    ビルド済みを再利用: $shot"
      continue
    fi
    log "ビルド: ${SHOT_DEFINE}=$shot"
    local blog="$OUT_DIR/build-$shot.log"
    if ! flutter build ios --simulator --debug \
      -t "$SHOT_ENTRYPOINT" --dart-define="${SHOT_DEFINE}=$shot" >"$blog" 2>&1; then
      tail -n 30 "$blog" >&2
      die "ビルド失敗: ${shot}（全文は ${blog}）"
    fi
    rm -rf "$OUT_DIR/apps/$shot"
    mkdir -p "$OUT_DIR/apps/$shot"
    cp -R build/ios/iphonesimulator/Runner.app "$OUT_DIR/apps/$shot/Runner.app"
  done
}

capture_slot() {
  local label="$1" name="$2" want_w="$3" want_h="$4"
  local udid; udid="$(udid_for "$name")"
  local dest="$OUT_DIR/$label"
  mkdir -p "$dest"

  log "$label — $name (${want_w}x${want_h})"

  # 起動してデータコンテナのパスを控える。
  # get_app_container は起動中でないと引けないため、この順序になる。
  xcrun simctl boot "$udid" 2>/dev/null || true
  xcrun simctl bootstatus "$udid" -b >/dev/null 2>&1 || true
  fix_status_bar "$udid"
  local first="${SHOTS[0]##*:}"
  xcrun simctl install "$udid" "$OUT_DIR/apps/$first/Runner.app"
  xcrun simctl launch "$udid" "$BUNDLE_ID" >/dev/null 2>&1 || true
  sleep 3

  if [ -n "$SEED_SCRIPT" ] || [ "${#TCC_SERVICES[@]}" -gt 0 ]; then
    local container
    container="$(xcrun simctl get_app_container "$udid" "$BUNDLE_ID" data)" \
      || die "データコンテナを取得できない"
    # 停止してから書く。起動中に書くと cfprefsd がキャッシュを書き戻して消える。
    log "$label — サンプルデータと権限を書き込む（停止中）"
    xcrun simctl shutdown "$udid" 2>/dev/null || true
    sleep 2
    [ -n "$SEED_SCRIPT" ] && python3 "$SEED_SCRIPT" \
      "$container/Library/Preferences/$BUNDLE_ID.plist"
    grant_tcc "$udid"
    xcrun simctl boot "$udid" 2>/dev/null || true
    xcrun simctl bootstatus "$udid" -b >/dev/null 2>&1 || true
    fix_status_bar "$udid"
    sleep 3
  fi

  local failed=0
  for pair in "${SHOTS[@]}"; do
    local num="${pair%%:*}" shot="${pair##*:}"
    local app="$OUT_DIR/apps/$shot/Runner.app"
    [ -d "$app" ] || die "ビルド済みアプリが無い: $app"

    xcrun simctl terminate "$udid" "$BUNDLE_ID" >/dev/null 2>&1 || true
    xcrun simctl install "$udid" "$app"
    xcrun simctl launch "$udid" "$BUNDLE_ID" >/dev/null 2>&1 || true
    sleep "$LAUNCH_WAIT"
    fix_status_bar "$udid"
    sleep 1

    local out="$dest/$num-$shot.png"
    xcrun simctl io "$udid" screenshot --type=png "$out" >/dev/null 2>&1 \
      || die "スクリーンショットの取得に失敗: $shot"
    finalize_png "$out" "$want_w" "$want_h" || failed=1
  done
  if [ "$failed" -ne 0 ]; then
    warn "$label: 提出できない画像がある（上の NG の行を見ること）"
    NG_SLOTS+=("$label")
  fi
}

log "撮影開始"
build_shots

CAPTURED=()
NG_SLOTS=()
for slot in "${SLOTS[@]}"; do
  IFS=':' read -r label name w h <<<"$slot"
  if [ "${#WANTED[@]}" -gt 0 ]; then
    local_match=0
    for want in "${WANTED[@]}"; do [ "$want" = "$label" ] && local_match=1; done
    [ "$local_match" = 1 ] || continue
  fi
  capture_slot "$label" "$name" "$w" "$h"
  CAPTURED+=("$label")
done

[ "${#CAPTURED[@]}" -gt 0 ] || die "撮影したスロットが無い（スロット名を確認すること）"

# 必須の枠（iPhone 中型）の寸法が conf に 1 つも無ければ知らせる。
# 大型や 6.5" の画像だけでは、中型の枠へ入れられない（2026-10-14 に踏んだ）。
has_iphone=0; has_medium=0
for slot in "${SLOTS[@]}"; do
  IFS=':' read -r _l _n sw sh <<<"$slot"
  case "${sw}x${sh}" in
    1206x2622|1179x2556|2622x1206|2556x1179) has_medium=1; has_iphone=1; continue ;;
  esac
  # 短い辺 / 長い辺。iPhone は 0.46〜0.56、iPad は 0.69〜0.77。寸法を並べず比で分ける
  if [ "$sw" -lt "$sh" ]; then short=$sw; long=$sh; else short=$sh; long=$sw; fi
  [ $((short * 100 / long)) -ge 65 ] || has_iphone=1
done
if [ "$has_iphone" = 1 ] && [ "$has_medium" = 0 ]; then
  warn "conf に必須の iPhone 中型の枠（1206x2622 か 1179x2556）が無い。iPhone 17 などで撮るスロットを足すこと"
fi

# 提出は Finder からドラッグするので、デスクトップにも複製しておく。
# build/ は flutter clean で消えるため、こちらを受け渡し場所として扱う。
if [ -n "$DESKTOP_DIR" ]; then
  log "複製 → $DESKTOP_DIR"
  mkdir -p "$DESKTOP_DIR"
  for label in "${CAPTURED[@]}"; do
    rm -rf "${DESKTOP_DIR:?}/$label"
    mkdir -p "$DESKTOP_DIR/$label"
    cp "$OUT_DIR/$label"/*.png "$DESKTOP_DIR/$label/"
  done
  find "$DESKTOP_DIR" -name '*.png' | sort | sed 's/^/    /'
fi

warn "DEBUG リボン・許可ダイアログ・空の画面が写っていないか必ず目視で確認すること。"
warn "背景色の割合では白紙判定できない（iPad は正常でも 97% が背景色になる）。"
if [ "${#NG_SLOTS[@]}" -gt 0 ]; then
  die "提出できない画像があるスロット: ${NG_SLOTS[*]}"
fi
log "完了"
