# ビルド手順

## 固定した入力

| 項目 | 固定値 |
| --- | --- |
| helium-macos | `48498ad240ecb6580c5e37059878887fdb519d42` |
| helium-chromium | `f769d14398de5fd823b5c93b545842142d23784d` |
| Chromium | `152.0.7977.82` |
| Helium Dual | `0.16.5.1`、個人用開発版 |
| Chromium lite SHA-256 | `67ac37f365dfdac763c428862e5e460e5948940b3d6f856374da2ce219981417` |
| 対象 | macOS arm64、開発用 component build |
| 実際に使用した Xcode | 26.6 / `17F113`、SDK 26.5 |
| アプリ識別子 | `local.heliumdual.browser` |

機械可読の入力・ハッシュは `source-lock.json`、再現用のビルド引数は `args.gn` にあります。完成した配布には `helium-dual-window.patch` とハッシュを封入します。`actual-build-args.gn` は実ビルドの設定の保存用で、再現コマンドが読み込むのは `args.gn` です。

## 必要な環境

Xcode 本体と Metal toolchain を使用できる Apple Silicon の Mac、大きな専用作業領域、インターネット接続が必要です。ソースアーカイブは約 1.7 GB ですが、展開したソース・依存物・生成物はさらに大きくなります。ビルド時間と必要容量はマシン・設定・進捗によって変わるため、固定の所要時間や容量は保証していません。

スクリプトはツールをグローバルにインストールしません。Python 3.13 と、`git`、GNU coreutils の `greadlink`、`quilt`、`ninja`、GNU patch / diff / sed を既に利用できる専用の `bin` ディレクトリを用意してください。`patch` と `diff` という名前でも GNU 版を呼べる PATH が必要です。今回のツール版は `source-lock.json` に記録しています。ローカルに用意したツール群自体の配布・自動導入は、このソース一式には含めていません。

Python の依存物は専用 venv に入れます。以下では既に利用できる Python 3.13 を使います。

```sh
python3.13 -m venv /path/to/helium-dual-build/.venv
/path/to/helium-dual-build/.venv/bin/python -m pip install -r /path/to/source-delivery/python-requirements.txt
```

再現スクリプトにはこの venv の Python のパスを渡します。`DEVELOPER_DIR` は既定で `/Applications/Xcode.app/Contents/Developer` に限定するため、システム全体の `xcode-select` は変更しません。別の場所の Xcode は `--developer-dir` で指定できます。

## 新しい作業ツリーを用意する

日常利用のブラウザ、進行中のビルド、既存のソースツリーとは別の場所で実行します。

```sh
git clone --no-checkout https://github.com/imputnet/helium-macos.git /path/to/helium-dual-build/helium-macos
git -C /path/to/helium-dual-build/helium-macos checkout --detach 48498ad240ecb6580c5e37059878887fdb519d42
git -C /path/to/helium-dual-build/helium-macos submodule update --init --recursive
```

`reproduce.py` は上記コミットとサブモジュールのコミットを厳密に確認します。違う版へ自動で切り替えたり、既存の変更を破棄したりしません。`prepare` は `build/src` が存在すると停止します。途中で失敗した場合もソースを削除せず残すため、同じ準備コマンドで最初から上書きすることはできません。ログから失敗段階を確認し、既存ツリーを保管したうえで別の新しいチェックアウトを使ってください。

公式 Chromium lite アーカイブを取得します。

```sh
curl --fail --location --output /path/to/helium-dual-build/chromium-152.0.7977.82-lite.tar.xz https://commondatastorage.googleapis.com/chromium-browser-official/chromium-152.0.7977.82-lite.tar.xz
```

`prepare` は同梱の固定 SHA-256 とファイルサイズを照合してから展開します。ダウンロードし直したハッシュ一覧を無条件に信用して値を更新する方式ではありません。

## 準備・構成・ビルド

```sh
cd /path/to/source-delivery
/path/to/helium-dual-build/.venv/bin/python reproduce.py verify-inputs

/path/to/helium-dual-build/.venv/bin/python reproduce.py prepare \
  --repo /path/to/helium-dual-build/helium-macos \
  --archive /path/to/helium-dual-build/chromium-152.0.7977.82-lite.tar.xz \
  --python /path/to/helium-dual-build/.venv/bin/python \
  --tools-bin /path/to/local-tools/bin

/path/to/helium-dual-build/.venv/bin/python reproduce.py configure \
  --repo /path/to/helium-dual-build/helium-macos \
  --python /path/to/helium-dual-build/.venv/bin/python \
  --tools-bin /path/to/local-tools/bin

/path/to/helium-dual-build/.venv/bin/python reproduce.py build \
  --repo /path/to/helium-dual-build/helium-macos \
  --python /path/to/helium-dual-build/.venv/bin/python \
  --tools-bin /path/to/local-tools/bin \
  --target chrome --jobs 8
```

準備処理は、固定コミットの上流スクリプトで依存物・コンパイラ・リソースを用意し、公式 Helium のパッチ群を適用します。依存物はそのコミットの `downloads.ini` / `deps.ini` の版とハッシュに従います。続いて欠落した元のテスト入力を復元し、最後に独自パッチを適用します。GN 構成と本体ビルドは別コマンドです。スクリプト自身はブラウザを起動しません。

ビルドの通常の失敗後は、原因を解決して `build` を再実行すると既存生成物を利用できます。ソースや `args.gn` を変更した場合は、この再現設定から変わったことを確認して扱ってください。スクリプトは引数ファイルの変更を検出して停止します。

## 欠落したテスト入力を先に復元する理由

この lite アーカイブでは、現在の生成処理が参照するテストデータの一部が省かれています。同梱する `fixtures/original-test-inputs.tar.gz` は Chromium の **同じタグ**から回収して照合した 1,270 ファイルです。展開後は 12,331,656 バイト、圧縮後は約 1.85 MB です。追加した検証用ターゲットが参照する WebUI テストリソースなどを含むため、同梱のビルド設定を再現する際に復元します。

各ファイルの元 URL、バイト数、SHA-256 は `fixtures/original-test-inputs.manifest.json` にあります。ネットワークから毎回 1,270 ファイルを取る代わりに、同梱した検証済みの元データを使います。復元は既存ファイルが同一なら維持し、内容が違えば書き込み前に停止します。

**独自パッチの前に復元してください。** 独自パッチには、上流 Helium の追加フィールドに合わせる WebUI テスト入力の修正も含まれます。パッチ適用後のファイルへ「元データの復元」を重ねると正しい差分を戻してしまうため、その順序はサポートしません。

## ビルド設定と確認範囲

`args.gn` は今回使用した Helium 開発設定を保存しています。エンジン・メディア・API キー等の設定をこの再現スクリプトが独自に作り替えることはありません。独自のアプリ名・保存先はパッチに含まれています。

`is_component_build=true`、`is_debug=false`、`target_cpu="arm64"` を使います。現在のコンパイラとの互換性のため `enable_precompiled_headers=false` を明示し、文字を含む作業パスでのリソース生成の修正もパッチに含めています。Sparkle と Chromium updater はそれぞれ `enable_sparkle=false`、`enable_updater=false` です。公式版へ自動更新する機構を、この開発版の更新方法として使いません。更新には差分の再適用・再ビルドが必要です。

macOS キーチェーンでは、暗号化用キーに専用の service `Helium Dual Storage Key` と account `Helium Dual` を使います。公式 Helium の `Helium Storage Key` / `Helium` とは項目名を分け、暗号化方式とキー処理は元の実装を維持しています。この変更は既存の公式 Helium のキーチェーン項目やプロファイルを編集・削除・移行する処理を追加しません。

追加確認用には同じ `build` コマンドで `--target helium_dual_state_smoke` または `--target helium_dual_session_tests` を指定できます。`helium_build_webui_test_support=false` は、このセッション試験に不要な WebUI テスト専用リソースと補助ソースへの依存を外します。本体の WebUI 機能を無効にする設定ではありません。このターゲットにはセッション4件と、暗号化キー待機中のデータベース終了順序などを確認する回帰試験3件、macOS Services メニュー通知1件、実 BrowserView のホスト接続1件、共通ホスト選択中のメニュー検証・アクティブ側タブ閉鎖1件を含み、現在の構成は合計10件です。最後の試験名は `HeliumDualBrowserHostTest.HostKeyMenuValidatesAndClosesOnlyActivePaneTab` です。試験の追加と実行成功は別であり、既存ビルドの検証範囲は `VALIDATION.md` を参照してください。試験の実行例は次のとおりです。

```sh
/path/to/helium-dual-build/helium-macos/build/src/out/Default/helium_dual_state_smoke
/path/to/helium-dual-build/helium-macos/build/src/out/Default/helium_dual_session_tests --gtest_filter='SessionServiceTest.HeliumDual*:HeliumDualWebDataShutdownTest.*:HeliumDualAppMenuControlTest.*:HeliumDualBrowserHostTest.*' --test-launcher-jobs=1
```

`out/Default/Helium Dual.app` は component build の生成物です。`.app` だけをコピーすると外部のビルド用 dylib に依存して起動できない場合があるため、そのまま移動可能な配布版とは扱えません。別途、依存ライブラリの収集・参照先の修正・コピー先での署名検査・元の生成物に依存しない実起動を確認する必要があります。アドホック署名は Developer ID 署名や notarization の完了を意味しません。

## 完成したビルドを別の場所で使うための包装

同梱の `packaging/package_component.py` は完成済みの `.app` と必要な依存ライブラリを別の場所に集め、参照先の調整とアドホック署名・検査を行います。Python 標準ライブラリと macOS の `otool` / `install_name_tool` / `codesign` / `ditto` / `xattr` を使います。コピー元のアプリ、生成物、既存のコピー先を上書きしません。

ソース一式を移動した後は、次の4つのパスをすべて指定してください。公開版では入出力パスを必須指定にしています。先に `--dry-run` を付けると依存関係の計画だけを表示します。包装するときは `--dry-run` を外して同じコマンドを実行します。

```sh
python3 packaging/package_component.py \
  --source-app '/path/to/helium-dual-build/helium-macos/build/src/out/Default/Helium Dual.app' \
  --destination '/path/to/separate-artifacts/Helium Dual.app' \
  --entitlements-dir /path/to/helium-dual-build/helium-macos/entitlements \
  --report /path/to/separate-artifacts/component-package-report.json \
  --dry-run
```

包装の成功は実機でのブラウザ操作確認とは別の結果です。
