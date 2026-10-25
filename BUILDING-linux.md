# ビルド手順（Dual 6.4.0 for Linux、プレビュー版）

Dual for Linux は、Helium 0.20.1.1 の Linux 版（helium-linux）を helium-linux 自身の手順で準備したソースに、
`linux/dual-0.20.1.1-linux.patch` と `linux/linux-identity.patch` を当て、`dual_rebrand.py` でアプリ内の名称とロゴを Dual のものにしてからビルドしています。
`linux/dual-0.20.1.1-linux.patch` は macOS 版と同じ変更（`helium-dual-window.patch`）から、macOS だけが使う部分を除いたものです。
同梱の拡張機能「Dual ページ翻訳」が使う翻訳プログラム `dual-translate-host` は、`translate-host/` と llama.cpp から別にビルドします。

配布している arm64 版と x86_64 版は、どちらも arm64 の Linux 機（Mac の上の仮想マシン）で作りました。x86_64 版はそこからのクロスビルドです。

## 固定した入力

| 項目 | 固定値 |
| --- | --- |
| helium-linux | タグ `0.20.1.1`、`473c0f72d7db2e8492f0fa975b8544bc719bb027` |
| helium-chromium | `f29a25968e483f8bb85e47829ccd487bbe229199`（macOS 版と同じ） |
| Chromium | `156.0.8078.47`（imput の準備済みアーカイブ。`chromium-156.0.8078.47-base.tar.zst` SHA-256 `d086d3b8c01b6d192bb54383459979641d2fa57e7c2599b9cb1f70b96c6a10be`、`chromium-156.0.8078.47-linux-x64.tar.zst` SHA-256 `7a4026f47b473314709d1289759af5ba9c13745ae0b72650727b47429d780c0a`） |
| ビルド設定 | helium-linux の `write_gn_args`（`flags.gn` と `flags.linux.gn`、`is_official_build=true`、`use_sysroot=true`）に `target_cpu` を足したもの。PGO なし（`chrome_pgo_phase=0`。Helium 公式の x86_64 版は PGO あり）。実際の値は `linux/args-arm64.gn`、`linux/args-x64.gn` |
| llama.cpp（翻訳プログラム） | リリース `b11846`、`1a24df163920a4744a95373d178d790b72a9bb2f` |
| ビルド機 | Debian 13（trixie）arm64、12 コア、メモリ 32 GB |
| 対象 | Linux arm64、x86_64 |

機械可読の値は `source-lock.json` の `linux` にあります。

## 必要な環境

arm64 の Linux 機（以下の手順は Debian 13 で確かめたもの）、インターネット接続、150 GB 程度の空き領域（ソースと両方のビルド結果で約 100 GB でした）。
使った Debian のパッケージのうち、ビルドの道具は次のとおりです。

```sh
sudo apt-get install bison clang clang-format cmake curl flex git gperf lld mold ninja-build \
  nodejs npm pkg-config python-is-python3 python3 python3-httplib2 python3-jinja2 python3-pil \
  python3-pyparsing python3-requests python3-setuptools python3-six python3-xcbgen rsync unzip xz-utils zstd
```

ビルドは Chromium の Debian bullseye の sysroot を使うので、ライブラリの開発用パッケージは要らないはずですが、
ビルド機には Chromium の `install-build-deps` が入れるもの（`libgtk-3-dev`、`libnss3-dev` など）も入っていました。それらなしでは試していません。

x86-64 の Linux 機なら、helium-linux のソースに付いてくる道具がそのまま使えるので手順 2 は要らないはずですが、試していません。

## 1. Helium Linux のソースを準備する

```sh
git clone --branch 0.20.1.1 --recurse-submodules https://github.com/imputnet/helium-linux.git
cd helium-linux
```

helium-linux の `scripts/build.sh` のうち、ソースの準備の部分だけを行います。
Chromium のソース取得、不要バイナリの削除、Helium のパッチ適用、ドメイン名・製品名の置換、翻訳の適用、Helium のリソース差し替えまでです。

```sh
. scripts/shared.sh
setup_environment
fetch_sources false false
apply_patches
apply_domsub
helium_substitution
helium_apply_translations
helium_version
helium_resources
```

## 2. arm64 の機械では、ビルドの道具を arm64 用にする

準備したソースには x86-64 用のビルドの道具が入っています。arm64 の機械では、これを arm64 用に置き換えます。

```sh
/path/to/Dual/linux/toolchain-arm64.sh /path/to/helium-linux
```

clang・Rust・bindgen・crubit をソースからビルドし、gn・siso・esbuild は CIPD から、DEPS が指定する版の linux-arm64 用を取ってきます。
TypeScript のコンパイラ（tsgo 7.0.2）は npm の `@typescript/typescript-linux-arm64`、Node.js は 24.12.0（nodejs.org、`/opt/node24.12` に置くので sudo を使います）、
python3・ninja・gperf・clang-format・mold は Debian のものを使います。
途中で helium-linux 0.18.3.1 にあった arm64 用の修正 `linux/fix-compiling-on-arm64.patch`（helium-linux 0.20.1.1 からは外れています）を当て、
最後に V8 の metagen が使う共有ライブラリの libclang を、位置独立コードでビルドし直します。
clang と Rust のビルドに数時間かかります。

このスクリプトは、ビルド機で実際に行った手順を順番どおりにまとめたものです。手順は何回かに分けて実行しており、このスクリプトを通しで実行してはいません。

## 3. Dual の変更を当てる

```sh
/path/to/Dual/linux/apply.sh /path/to/helium-linux
```

次の3つを行います。

- `linux/dual-0.20.1.1-linux.patch`：Dual の変更（2画面、同梱の拡張機能、翻訳プログラムの置き場など）。
  `linux/make_linux_patch.py` で、`helium-dual-window.patch` を当てたファイル一式と準備済みの Helium Linux のソースとの差分から作ったもので、
  macOS だけがビルドするファイル（`.mm`、`_mac.h`）と、ビルドファイルの macOS 用の行は含みません。
- `linux/linux-identity.patch`：Dual for Linux が Helium と別の設定フォルダ（`~/.config/dual-browser`）、デスクトップ エントリ（`dual-browser.desktop`）、アイコン名（`dual-browser`）を使うようにする変更。Helium と同じ機械に入れても混ざりません。
- `dual_rebrand.py`：アプリ内の Helium の名称とロゴを Dual のものに置き換えます（macOS 版と同じスクリプト）。

## 4. 構成・ビルド

arm64 版：

```sh
. scripts/shared.sh
ARCH=arm64 setup_environment
write_gn_args
gn_gen
cd build/src
SISO_PATH=$PWD/third_party/siso/cipd/siso python3 third_party/depot_tools/autoninja.py -C out/Default chrome
```

`out/Default/args.gn` が `linux/args-arm64.gn` と同じになることを確認してください。

x86_64 版（同じ arm64 の機械でのクロスビルド）：

```sh
mkdir -p out/x64
sed -e 's/^target_cpu = .*/target_cpu = "x64"/' -e 's/^v8_target_cpu = .*/v8_target_cpu = "x64"/' \
  out/Default/args.gn > out/x64/args.gn
./buildtools/linux64/gn gen out/x64 --fail-on-unused-args
SISO_PATH=$PWD/third_party/siso/cipd/siso python3 third_party/depot_tools/autoninja.py -C out/x64 chrome
```

最初からのビルドに、ビルド機で arm64 版は2時間ほど、x86_64 版は3時間ほどかかりました。2つを同時にビルドすると失敗したので、順番に行っています。

## 5. 翻訳プログラム

CMake 3.20 以降と、手順 2 までで揃う Chromium の clang、sysroot を使います。

```sh
git clone --branch b11846 --depth 1 https://github.com/ggml-org/llama.cpp.git
/path/to/Dual/translate-host/build_linux.sh llama.cpp /path/to/hosts-arm64 arm64 /path/to/helium-linux/build/src
/path/to/Dual/translate-host/build_linux.sh llama.cpp /path/to/hosts-x64 x64 /path/to/helium-linux/build/src
```

それぞれのフォルダに `dual-translate-host`（CPU で動きます）と、同梱するライセンス文書のフォルダ `dual-translate-host-licenses` ができます。
翻訳モデル（Gemma 4 E4B）は配布物に含めません。利用者が初めて使うときに、翻訳プログラムが Hugging Face からダウンロードします。

## 6. 配布用の tar.xz

```sh
/path/to/Dual/linux/package.sh /path/to/helium-linux Default 6.4.0-linux-preview /path/to/hosts-arm64 /path/to/release
/path/to/Dual/linux/package.sh /path/to/helium-linux x64 6.4.0-linux-preview /path/to/hosts-x64 /path/to/release
```

`dual-browser-6.4.0-linux-preview-arm64.tar.xz` と `…-x86_64.tar.xz` ができます。
中身は、ビルドしたプログラムと必要なファイル、起動用の `dual-browser`、デスクトップ エントリ `dual-browser.desktop`、
アプリケーション メニューに加える `install-for-me.sh`、AppArmor のプロファイルのひな形 `apparmor.cfg`、`README.txt`、`LICENSE`、
`dual-extensions/`（同梱の拡張機能。`linux/bundle_extensions_linux.py` が `extensions/` からコピー）と
`dual-native-hosts/`（翻訳プログラムと、翻訳の拡張機能だけが起動できるようにしたマニフェスト）です。ELF ファイルは llvm-strip で小さくしています。
