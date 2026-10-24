# 新しい Helium へ移す手順

Dual は、特定の版の Helium に対する変更の集まりです。Helium が新しい版を出したら、変更を新しい版に載せ替えてビルドし直します。
ここでは、その手順と、`tools/` にある道具の使い方を書きます。Dual 6.3.0 を Helium 0.17.2.2 から 0.18.3.1 へ、Dual 6.4.0 を 0.18.3.1 から 0.20.1.1 へ移したときに、この手順を使いました。

## 用語

- **準備済みソース**：Helium 自身の手順（`prepare_sources`）で用意した Chromium のソース。Dual のパッチを当てる前の状態です。
- **ステージ**：Dual が追加・変更する全ファイルの「Dual 版」を、ソースツリーと同じ配置で集めたフォルダ。`helium-dual-window.patch` は、ステージと準備済みソースの差分です。

## 自動でできること、できないこと

次の部分は道具だけで進みます。

- 新しい版が出ているかの確認（`tools/check_upstream.py`）。
- 変更の載せ替え（`tools/port_patch.py`）。ファイルごとに「古い Helium」「Dual 版」「新しい Helium」の3つを比べてマージします。Helium が触っていないファイルと、別の場所だけが変わったファイルは、そのまま通ります。
- ツリーへの反映、名称とロゴの置き換え、ビルド。

次の部分は、人が見て決める必要があります。

- **衝突**：Helium と Dual が同じ行を変えたファイル。0.17.2.2 → 0.18.3.1 では99ファイル中9ファイル、0.18.3.1 → 0.20.1.1 では14ファイルでした（このほか、Helium が Dual の変更箇所を別のファイルへ移していたものが2件）。
- **マージは通るが意味が変わった箇所**：コンパイルエラーになるものと、動かして初めてわかるものがあります。同じ移行では次の2つがありました。
  - Chromium 154 で、画面の部品が `Browser` を直接渡さなくなった。Dual が `Browser` に持たせていた状態を、ウィンドウに付ける付帯データ（`HeliumDualPaneState`）へ移した。コンパイルエラーで気づく種類のものです。
  - Helium がツールバーの配置を作り直した。Dual 側の調整（`toolbar_view.cc`）は衝突したので一度外し、動かしてみたところ、固定した拡張機能のボタンがペインの幅では隠れることがわかったため、新しい方式に合わせて入れ直した。動かして初めてわかる種類のものです。
- **動作の確認**と**公開**。

## 手順

以下、`OLD` は現在の準備済みソース（パッチを当てていないもの）、`NEW` は新しい版の準備済みソースです。

1. 新しい版があるか確かめる。

   ```sh
   python3 tools/check_upstream.py
   ```

2. 新しい版のソースを準備する（[BUILDING.md](BUILDING.md) の手順 1 と同じ。タグだけ新しい版にする）。準備が終わったら、パッチを当てる前に、手つかずの写しを取っておく。これが `NEW` です。

   ```sh
   cp -cR helium-macos/build/src /path/to/NEW
   ```

3. 現在のステージを用意する。手元になければ、公開しているパッチから作れます。

   ```sh
   python3 tools/stage_from_patch.py /path/to/OLD helium-dual-window.patch stage
   ```

4. 載せ替える。

   ```sh
   python3 tools/port_patch.py --old-helium /path/to/OLD --new-helium /path/to/NEW \
     --stage stage --out stage-new
   ```

   衝突したファイルは、衝突の印（`<<<<<<< Dual` … `>>>>>>> new Helium`）が入った状態で `stage-new` に書き出され、一覧が表示されます。`stage-new-report.json` に全ファイルの結果が残ります。

5. 衝突を解く。`stage-new` の該当ファイルを直接直します。同じ移行をやり直せるように、どう解いたかをスクリプトに残しておくと確実です（例：[tools/resolve_0.18.3.1.py](tools/resolve_0.18.3.1.py)、[tools/resolve_0.20.1.1.py](tools/resolve_0.20.1.1.py)。後者は Chromium 156 で名前の変わった関数への追従も含みます）。

6. ツリーに入れて、名称とロゴを置き換え、ビルドする（[BUILDING.md](BUILDING.md) の手順 2〜3）。

   ```sh
   python3 tools/apply_stage.py stage-new helium-macos/build/src
   python3 dual_rebrand.py helium-macos/build/src --branding branding
   ```

   コンパイルエラーが出たら、ツリーを直して、直したファイルを `stage-new` に写します。次のコマンドは、ツリーが「手つかずの Helium ＋ステージ＋名称とロゴの置き換え」と一致しているかを調べ、`--fix-stage` を付けるとツリーの変更をステージに写します（ステージにないファイルを新しく変えた場合は、一覧に出るので手で加えます）。

   ```sh
   python3 tools/check_tree.py /path/to/NEW stage-new helium-macos/build/src --fix-stage
   ```

7. 動作を確かめる（[VALIDATION.md](VALIDATION.md) の項目）。

8. パッチを作り直す。

   ```sh
   python3 tools/make_patch.py /path/to/NEW stage-new helium-dual-window.patch
   ```

   `source-lock.json` の版・コミット・ハッシュ、`modifications.json`、各文書の版の表記も更新します。

## 載せ替えを楽に保つための決まり

- Dual の処理は、できるだけ Dual 自身のファイル（`helium_dual_*`）に書く。Helium・Chromium のファイルには、そこを呼び出す数行だけを足す。
- 既存の行の整形や並べ替えをしない。変えた行が少ないほど、衝突も減ります。
- 効果のなくなった変更は外す。6.3.0 では、何もしていなかった `window_feature_controller.*` の変更を外しました。
- 変更・追加したファイルの先頭に、変更した日と内容を書く（GPL-3.0 第5節）。
