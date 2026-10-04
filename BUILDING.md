# ビルド手順（Dual 6.2.3）

Dual 6.2.3 は、Helium 0.17.2.2 を Helium 自身のリリース手順で準備したソースに、
`helium-dual-window.patch` を当て、`dual_rebrand.py` でアプリ内の名称とロゴを Dual のものにしてからビルドしています。

## 固定した入力

| 項目 | 固定値 |
| --- | --- |
| helium-macos | タグ `0.17.2.2`、`359e3c5711a7c727499948bc9413aedabe3295ae` |
| helium-chromium | `2e0bc29d8236f3921aecbf391d4f6bb3bf77086e` |
| Chromium | `153.0.8010.52`（lite アーカイブ SHA-256 `ed6fcbf913f12f97c619616b35fa8b56f6e61c53bdbf00cbb0e7ef839a39844a`） |
| ビルド設定 | Helium のリリース用 `configure_build`（`is_official_build=true`、arm64、PGO なし）。実際の値は `args.gn` |
| 使用した Xcode | 26.6 / `17F113` |
| 対象 | macOS arm64（Apple Silicon） |

機械可読の値は `source-lock.json` にあります。

## 必要な環境

Xcode 本体と Metal toolchain を使える Apple Silicon の Mac、インターネット接続、
数十 GB 以上の作業領域が必要です。作業領域のパスは英数字だけにしてください
（DevTools の生成に使う rollup が、英数字以外を含む絶対パスを受け付けません）。

## 1. Helium のソースを準備する

```sh
git clone --branch 0.17.2.2 --recurse-submodules https://github.com/imputnet/helium-macos.git
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

続けて、アプリ内の Helium の名称とロゴを Dual のものに置き換えます（Python 3 のみで動き、追加のライブラリは不要です）。

```sh
python3 /path/to/Dual/dual_rebrand.py build/src --branding /path/to/Dual/branding
```

画面の文字列（`.grd`・`.grdp` と翻訳の `.xtb`）で、ブラウザ自身を指す「Helium」を「Dual」にし、
`branding/` のロゴを Helium の準備手順がロゴを置く場所へコピーします。
Helium のオンラインサービス、Helium のパートナープログラム、著作権表示など、Helium 自身を指す表記は変えません。
`branding/` の画像は `branding/make_branding.py`（Pillow が必要）で、Dual のアイコン画像から作り直せます。

## 3. 構成・ビルド

```sh
source devutils/shared.sh
configure_build arm64 false false
helium_build
```

`out/Default/args.gn` がこのリポジトリの `args.gn` と同じになることを確認してください。

## 4. 配布用アプリと DMG

```sh
python3 /path/to/Dual/packaging/package_release.py \
  --built "build/src/out/Default/Helium Dual.app" \
  --icon /path/to/Dual/Dual-6.icns --version 6.2.3 --out /path/to/release
```

アプリ名を `Dual 6.2.3`、バンドル ID を Dual 5 と同じ `local.heliumdual.browser` にして
（既存のプロファイルを引き継ぐため）、アイコンを差し替え、アドホック署名して DMG を作ります。
Apple Developer ID での署名・公証はしていません。
