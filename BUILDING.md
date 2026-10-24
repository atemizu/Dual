# ビルド手順（Dual 6.4.0）

Dual 6.4.0 は、Helium 0.20.1.1 を Helium 自身のリリース手順で準備したソースに、
`helium-dual-window.patch` を当て、`dual_rebrand.py` でアプリ内の名称とロゴを Dual のものにしてからビルドしています。
同梱の拡張機能「Dual ページ翻訳」が使う翻訳プログラム `dual-translate-host` は、`translate-host/` と llama.cpp から別にビルドします。

## 固定した入力

| 項目 | 固定値 |
| --- | --- |
| helium-macos | タグ `0.20.1.1`、`9aa975a56de8c2376d7c22f71da564b9426cda5f` |
| helium-chromium | `f29a25968e483f8bb85e47829ccd487bbe229199` |
| Chromium | `156.0.8078.47`（imput の準備済みアーカイブ。`chromium-156.0.8078.47-base.tar.zst` SHA-256 `d086d3b8c01b6d192bb54383459979641d2fa57e7c2599b9cb1f70b96c6a10be`、`chromium-156.0.8078.47-mac-arm64.tar.zst` SHA-256 `22c35bf5057593e945a9beaaaadb6f5bef00d5535e5d4df5dc3d532b2d6ce08c`） |
| ビルド設定 | Helium のリリース用 `configure_build`（`is_official_build=true`、arm64、Helium 0.20 の構成手順どおり PGO あり＝`chrome_pgo_phase=2`）。実際の値は `args.gn` |
| llama.cpp（翻訳プログラム） | リリース `b11846`、`1a24df163920a4744a95373d178d790b72a9bb2f` |
| 使用した Xcode | 26.6 / `17F113` |
| 対象 | macOS arm64（Apple Silicon） |

機械可読の値は `source-lock.json` にあります。

## 必要な環境

Xcode 本体と Metal toolchain を使える Apple Silicon の Mac、インターネット接続、
数十 GB 以上の作業領域が必要です。作業領域のパスは英数字だけにしてください
（DevTools の生成に使う rollup が、英数字以外を含む絶対パスを受け付けません）。

## 1. Helium のソースを準備する

```sh
git clone --branch 0.20.1.1 --recurse-submodules https://github.com/imputnet/helium-macos.git
cd helium-macos
```

`devutils/shared.sh` の `prepare_sources` と同じ手順でソースを準備します。
Chromium のソース取得、同梱リソースの展開、不要バイナリの削除、ツールチェーンの取得、
Helium のパッチ適用、ドメイン名・製品名の置換、翻訳の適用、Helium のリソース差し替えまでです。

```sh
source devutils/shared.sh
prepare_sources arm64 true
```

## 2. Dual のパッチを当てる

```sh
patch -p1 --forward -d build/src < /path/to/Dual/helium-dual-window.patch
```

パッチは上の準備を終えたソースに対して作っており、失敗なく適用できることを確認しています。
別の版の Helium に当てる場合は、[UPDATING.md](UPDATING.md) の手順を使ってください。

続けて、アプリ内の Helium の名称とロゴを Dual のものに置き換えます（Python 3 のみで動き、追加のライブラリは不要です）。

```sh
python3 /path/to/Dual/dual_rebrand.py build/src --branding /path/to/Dual/branding
```

画面の文字列（`.grd`・`.grdp` と翻訳の `.xtb`）で、ブラウザ自身を指す「Helium」を「Dual」にし、
`branding/` のロゴを Helium の準備手順がロゴを置く場所へコピーします。パッチが追加する Dual 固有の文言の日本語訳も、ここで入れます。
Helium のオンラインサービス、Helium のパートナープログラム、著作権表示など、Helium 自身を指す表記は変えません。
`branding/` の画像は `branding/make_branding.py`（Pillow が必要）で、Dual のアイコン画像から作り直せます。

## 3. 構成・ビルド

```sh
source devutils/shared.sh
configure_build arm64 false false
helium_build
```

`out/Default/args.gn` がこのリポジトリの `args.gn` と同じになることを確認してください。

## 4. 翻訳プログラム

Dual ページ翻訳の翻訳プログラム `dual-translate-host` を、llama.cpp を静的にリンクしてビルドします。
CMake 3.20 以降と Xcode のコマンドラインツールが必要です。

```sh
git clone --branch b11846 --depth 1 https://github.com/ggml-org/llama.cpp.git
/path/to/Dual/translate-host/build_mac.sh llama.cpp /path/to/hosts
```

`/path/to/hosts` に、`dual-translate-host`（arm64、Metal、macOS 13 以降）と、
同梱するライセンス文書のフォルダ `dual-translate-host-licenses` ができます。
翻訳モデル（Gemma 4 E4B）はアプリに含めません。利用者が初めて使うときに、翻訳プログラムが Hugging Face からダウンロードします。

## 5. 配布用アプリと DMG

```sh
python3 /path/to/Dual/packaging/package_release.py \
  --built "build/src/out/Default/Helium Dual.app" \
  --icon /path/to/Dual/Dual-6.icns --version 6.4.0 --out /path/to/release \
  --hosts /path/to/hosts
```

アプリ名を `Dual 6.4.0`、バンドル ID を Dual 5 と同じ `local.heliumdual.browser` にして
（既存のプロファイルを引き継ぐため）、アイコンを差し替え、`extensions/` の拡張機能を
`Contents/Resources/Dual Extensions/` に、翻訳プログラムとその設定ファイル（ネイティブ メッセージングのマニフェスト）を
`Contents/Resources/Dual Native Hosts/` にコピーし、アドホック署名して DMG を作ります。
Apple Developer ID での署名・公証はしていません。
