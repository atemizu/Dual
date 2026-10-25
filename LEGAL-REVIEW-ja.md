# 規約・公開条件の確認メモ

確認日：2026-09-09、再確認 2026-09-29（Dual 6.2.2 のソースとアプリ配布）、2026-10-04（Dual 6.2.3）、2026-10-05（Dual 6.2.4、同日 Dual 6.3.0）、2026-10-06（Dual 6.3.0 の内容追加と Helium 0.18.3.1 への移行）、2026-10-10（Dual 6.3.0）、2026-10-25（Dual 6.4.0：Helium 0.20.1.1 への移行とページ翻訳。同日、Dual 6.4.0 for Linux のプレビュー版）。以下は公開準備に用いた文書の読み取りと対応内容であり、個別事情を含む法的適合性の保証ではありません。

| 一次資料 | 確認した点 | 公開一式の対応 |
| --- | --- | --- |
| [Helium Terms of Use](https://helium.computer/terms)（2026-07-08改訂） | GPL-3.0と取り込み部分のBSD-3-Clauseによる利用を案内 | 元のライセンスを保持し、非公式派生版と明記 |
| [Helium README](https://github.com/imputnet/helium#license) | Helium固有部分はGPL-3.0、取り込み部分は元のライセンスを維持 | GPL全文・元の通知・帰属資料を同梱 |
| [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) 第4・5節 | ソースや改変差分の提供、通知・ライセンスの保持、改変と日付の表示 | LICENSE、README、NOTICE、MODIFICATIONS、パッチ内コメント |
| [Helium Brand Kit](https://helium.computer/brand) | 公式ロゴで提携・承認を示唆しない | リポジトリには提供された独自画像を使用 |

GNU HTMLページは取得タイムアウトしたため、GNU公式の[プレーンテキスト全文](https://www.gnu.org/licenses/gpl-3.0.txt)を直接取得し、第4・5・6・7節を確認しました。その全文を変更せずLICENSEに置いています。

GPLv3第5節は改変差分をソース形式で提供する形を明示的に扱うため、今回は固定した上流＋パッチ＋準備・ビルドスクリプトという構成です。上流の固定URLが将来取得できなくなった場合には、取得可能性を再確認する必要があります。

今回の公開対象はソースのみです。将来完成アプリを配布する場合には、第6節に沿う対応ソースの提供方法、同梱依存物、ライセンス表示、アプリ内の表示とブランド、署名・更新方法を、その配布内容に合わせて別途確認してください。今回のソース準備からバイナリ配布の適合性は推定しません。

GUI内のcreditsなど元からある法的表示を削除する変更は含めていません。名称やロゴについて、コードのGPLだけから商標の利用権を推定していません。

## 公式のヘッダー指針と上流投稿規則

[CONTRIBUTING.mdのCode style](https://github.com/imputnet/helium/blob/main/CONTRIBUTING.md#code-style)は、新規ファイルに既存Heliumパッチで用いられる著作権ヘッダーを入れるよう案内しています。新規ローカルファイルはそのGPLの文章形式に合わせ、独自改変の著作権者名を明示しました。元から存在するChromium/Helium等の通知を維持しています。

同文書および上流AGENTS.mdには上流へのAI生成の投稿を制限する規則があります。本公開は利用者の独立したリポジトリでの非公式派生版の公開であり、上流への寄稿・PRではありません。これらの投稿規則をGPLの再配布許諾の撤回と解釈してはいません。上流が本プロジェクトを受け入れ、承認、支援することを示すものでもありません。

## 2026-09-29 再確認（Dual 6.2.2）

| 一次資料 | 確認した点 | 対応 |
| --- | --- | --- |
| [Helium Terms of Use](https://helium.computer/terms) | 引き続き GPL-3.0 と BSD-3-Clause による利用を案内。商標・派生版・サービス利用についての条項はない | 元のライセンスを保持し、非公式派生版と明記 |
| [Helium Privacy Policy](https://helium.computer/privacy) | 「非公式ビルドや派生版には適用されない」と明記 | README に、Helium のサービスを使っても同ポリシーは Dual に適用されない旨を記載 |
| [Helium Brand Kit](https://helium.computer/brand) | 許可なくロゴで提携・承認を示唆しない、ロゴを改変しない | アプリのアイコンは独自画像。アプリ内に残る Helium の名称・ロゴ表示は README で明示し、次回の更新で Dual 独自の表示へ置き換える予定 |
| [helium-services](https://github.com/imputnet/helium-services) | ホスト版サービスの第三者利用についての記載はない | 上記 README の記載で対応 |

今回はアプリ（DMG）も配布します。GPLv3 第6節の対応ソースとして、このリポジトリのパッチ・固定した上流（`source-lock.json`）・ビルド手順（`BUILDING.md`）・配布用スクリプト（`packaging/package_release.py`）を公開しています。

## 2026-10-04 対応（Dual 6.2.3）

2026-09-29 の確認で「次回の更新で Dual 独自の表示へ置き換える予定」としていた点に対応しました。

- アプリ内でブラウザ自身を指す名称を「Dual」に、製品ロゴ（About ページ、メニュー、アドレスバー、通知、初回セットアップ画面など）を Dual 独自の画像に置き換えた（`dual_rebrand.py`、`branding/`）。アプリ内で Helium のロゴは使っていない。
- Helium 自身を指す表記（Helium のオンラインサービス、パートナープログラム、著作権者「The Helium Authors」）は Helium の名称のまま残した。
- About ページに「Dual は Helium の非公式な派生版」であることと「Helium 0.17.2.2 ベース（非公式ビルド）」を表示し、元の著作権・ライセンス表示（helium://credits を含む）は削除していない。
- 内部の URL（`helium://`）や保存先の識別子は互換性のため変更していない。

## 2026-10-04 再確認（Dual 6.2.3）

| 一次資料 | 確認した点 | 対応 |
| --- | --- | --- |
| [Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂） | GPL-3.0 と BSD-3-Clause による利用を案内。商標・派生版についての条項はない | 元のライセンスを保持し、非公式派生版と明記 |
| [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂） | 非公式ビルド・派生版には適用されない。利用者が同意した場合、クラッシュレポートは Helium がホストするサービスへ送られる | README に、Dual ではクラッシュレポートをオンにしないよう記載。次回の更新で Dual から送信しないよう変更する予定 |
| [Helium Brand Kit](https://helium.computer/brand) | 許可なくロゴで提携・承認を示唆しない、ロゴを改変しない | 6.2.3 でアプリ内の Helium のロゴをすべて除去（上記） |

## 2026-10-05 対応（Dual 6.2.4）

2026-10-04 の確認で「次回の更新で Dual から送信しないよう変更する予定」としていたクラッシュレポートに対応しました。

- Dual 6.2.4 はクラッシュレポートを送信しない。クラッシュ処理に送信先 URL を渡さず、Helium の「ポリシーで送信禁止」と同じ経路を使って、クラッシュ後の送信確認を出さず、保留中のレポートは削除し、設定は「無効」で固定する。
- 6.2.3 以前の初期設定は「クラッシュ後に確認する」で、利用者が同意した場合（または自動送信を選んだ場合）に Helium のクラッシュレポートサービスへ送られる。README に、6.2.3 以前では「無効」にするよう記載した。

## 2026-10-05 再確認（Dual 6.2.4）

| 一次資料 | 確認した点 | 対応 |
| --- | --- | --- |
| [Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂、変更なし） | GPL-3.0 と BSD-3-Clause による利用を案内。商標・派生版についての条項はない | 元のライセンスを保持し、非公式派生版と明記 |
| [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂、変更なし） | 非公式ビルド・派生版には適用されない。利用者が同意した場合、クラッシュレポートは Helium がホストするサービスへ送られる | 6.2.4 で Dual からは送信しないようにした（上記） |
| [Helium Brand Kit](https://helium.computer/brand) | 許可なくロゴで提携・承認を示唆しない、ロゴを改変しない | アプリ内で Helium のロゴは使っていない（6.2.3 から） |

## 2026-10-05 再確認（Dual 6.3.0）

Dual 6.3.0 は、不具合修正（シークレットウィンドウを閉じたときの異常終了）と、同梱の拡張機能「Dual 不具合報告」の追加です。名称・ロゴ・配布方法は 6.2.4 から変えていません。公開前に次の3点を読み直し、6.2.4 の確認時から変更がないことを確かめました。

| 一次資料 | 確認した点 |
| --- | --- |
| [Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂、変更なし） | 商標・派生版についての条項はなく、GPL-3.0 と BSD-3-Clause による利用を案内 |
| [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂、変更なし） | 非公式ビルド・派生版には適用されない |
| [Helium Brand Kit](https://helium.computer/brand) | 許可なくロゴで提携・承認を示唆しない、ロゴを改変しない |

同梱の拡張機能について確認した点：

- 自分からは通信しない。利用者が「GitHub で報告する」を押したときに、件名と本文を入れた GitHub の Issue 作成画面（このリポジトリ）を開くだけで、投稿は利用者が GitHub 上で自分のアカウントで行う。Dual の側に報告を受け取るサーバーはない。
- 報告に含める環境の情報（Dual・Chromium・macOS のバージョン、ディスプレイとブラウザ画面の大きさ、表示言語）は、送る前に画面に表示し、利用者が外せる。投稿が公開されることと、個人情報を書かないよう求める注意を画面に表示する。
- 拡張機能のコードとアイコンは Dual の作者によるもので、第三者の素材は含まない（GPL-3.0-only）。
- 利用者は拡張機能の一覧からオフにも削除もでき、削除したものは再び入らない。

## 2026-10-06 再確認（Dual 6.3.0：内容の追加と Helium 0.18.3.1 への移行）

2026-10-05 の確認のあと、公開前の Dual 6.3.0 に次を加えました：分割バーの動作の変更、同梱の拡張機能「Dual タブ自動削除」、土台を Helium 0.18.3.1（Chromium 154.0.8037.97）へ移行。名称・ロゴ・配布方法は変えていません。次の3点を読み直し、変更がないことを確かめました。

| 一次資料 | 確認した点 |
| --- | --- |
| [Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂、変更なし） | 商標・派生版についての条項はなく、GPL-3.0 と BSD-3-Clause による利用を案内 |
| [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂、変更なし） | 非公式ビルド・派生版には適用されない |
| [Helium Brand Kit](https://helium.computer/brand) | 許可なくロゴで提携・承認を示唆しない、ロゴを改変しない |

土台の移行について確認した点：

- helium-macos 0.18.3.1 の `LICENSE` と `LICENSE.ungoogled_chromium`、準備済みソースの Chromium の `LICENSE` は、`licenses/` に置いている写しとバイト単位で同じ。
- Helium のソースを取得・準備する手順は Helium 自身のもの（`prepare_sources`）で、Chromium のアーカイブは Helium のスクリプトがハッシュを照合する。

追加した拡張機能「Dual タブ自動削除」について確認した点：

- 通信しない。権限は、タブの一覧と操作（tabs）、定期実行（alarms）、設定と一覧の保存（storage）の3つ。
- 閉じたタブのタイトルとアドレス、開いているタブのアドレスと最後に使った時刻を、その Mac のプロファイル内（拡張機能の保存領域）に置く。閉じたタブの一覧は14日・200件まで。利用者は一覧を消せる。シークレットウィンドウでは動かない。
- 初期状態でオン。入れた直後は、その時点から数え直すので、最初の1日は何も閉じない。ツールバーのボタンから、オフにも時間の変更もできる。拡張機能の一覧から削除もできる。
- コードとアイコンは Dual の作者によるもので、第三者の素材は含まない（GPL-3.0-only）。アイコンは作者自作のドット絵（`extensions/art/`）。不具合報告のアイコンも、同じ作者の新しいドット絵に差し替えた。

## 2026-10-10 再確認（Dual 6.3.0：公開前の内容の入れ替え）

2026-10-06 の確認のあと、公開前の Dual 6.3.0 の内容を次のように変えました。名称・ロゴ・配布方法、土台（Helium 0.18.3.1）は変えていません。

- 同梱の拡張機能「Dual タブ自動削除」を外し、同じ働きをブラウザ本体の設定（設定画面の「パフォーマンス」）にした。初期状態はオフ。
- 同梱の拡張機能「Dual サイト時間制限」を加えた。
- 固定タブの復元、隠したペインのタブバー、「×」ボタンの修正。
- フレームレス モードで、使っていない側のペインへのクリックが外れる問題と、ツールバーが出たままになる問題の修正。

[Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂）と [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂）を 2026-10-10 に読み直し、どちらも改訂されていないことを確かめました。

使っていないタブを閉じる設定について確認した点：

- コードは Dual の作者によるもので、第三者のコードは含まない（GPL-3.0-only、パッチの一部）。
- 通信しない。設定はプロファイルに保存する。閉じたタブは Chromium 標準の「最近閉じたタブ」に入るだけで、別の一覧は持たない。
- 初期状態はオフで、利用者がオンにするまで何も閉じない。

追加した拡張機能「Dual サイト時間制限」について確認した点：

- 通信しない。権限は、タブのアドレスの読み取りと操作（tabs）、定期実行（alarms）、操作の有無の確認（idle）、保存（storage）の4つ。ページの中身を読み書きする権限は持たない。
- 制限を付けたサイトのホスト名、制限の長さ、いまの回に見た時間を、その Mac のプロファイル内（拡張機能の保存領域）に置く。休憩ページのアドレスには、戻り先のページのアドレスが入る（タブの履歴に残る）。シークレットウィンドウでは動かない。
- 何も設定しないかぎり、何もしない。制限はポップアップからいつでも変更・削除でき、拡張機能の一覧からオフにも削除もできる。
- コードとアイコンは Dual の作者によるもので、第三者の素材は含まない（GPL-3.0-only）。アイコンは作者自作のドット絵（`extensions/art/hourglass-pixel.png`）。「Dual タブ自動削除」のアイコンだったドット絵は、リポジトリから外した。

## 2026-10-25 再確認（Dual 6.4.0：Helium 0.20.1.1 への移行とページ翻訳）

Dual 6.3.0 は公開しませんでした。6.4.0 は、6.3.0 の内容に次を加えたものです：土台を Helium 0.20.1.1（Chromium 156.0.8078.47）へ移行、同梱の拡張機能「Dual ページ翻訳」とその翻訳プログラム、Linux への移植（コードのみ。Linux 版は配布しない）。名称・ロゴ・配布方法は変えていません。

[Helium Terms of Use](https://helium.computer/terms)（2026-07-08 改訂）と [Helium Privacy Policy](https://helium.computer/privacy)（2026-07-16 改訂）を 2026-10-25 に読み直し、どちらも改訂されていないことを確かめました。[Helium Brand Kit](https://helium.computer/brand) の「ロゴを改変しない、許可なく提携を示唆しない」も変わっておらず、アプリは引き続き Helium のロゴを使っていません。

土台の移行について確認した点：

- Helium 0.20.1.1 から、Chromium のソースは imput が準備したアーカイブ（共通部分と macOS arm64 部分の2つ）で取得する。2つの SHA-256 は imput が GitHub で公開しているハッシュと一致し、`source-lock.json` に記録した。
- Helium 0.20 の構成手順は PGO のプロファイル（Chromium 由来）を使う。ビルド手順の記述をこれに合わせた。
- helium-macos 0.20.1.1 の `LICENSE` と `LICENSE.ungoogled_chromium`、helium-chromium の `LICENSE`（GPL-3.0）、準備済みソースの Chromium の `LICENSE` は、`licenses/` に置いている写しとバイト単位で同じ。

ページ翻訳について確認した点：

- 翻訳プログラム `dual-translate-host` のコードは Dual の作者によるもの（GPL-3.0-only、`translate-host/`）。静的にリンクする llama.cpp・ggml（MIT License）と JSON for Modern C++（MIT License）の著作権表示と許諾文は、アプリの中の翻訳プログラムの隣（`dual-translate-host-licenses/`）と `translate-host/licenses/` に置いた。MIT License の条件（著作権表示と許諾文の同梱）を満たし、GPL-3.0 とも両立する。
- 翻訳モデル（Gemma 4 E4B、Unsloth による 4ビット版）は Dual にもこのリポジトリにも含めず、再配布しない。利用者が選んだときに、翻訳プログラムが Hugging Face の固定した版をダウンロードする。モデルの許諾は Apache License 2.0（[Gemma 4 の許諾の説明](https://ai.google.dev/gemma/docs/gemma_4_license)、配布元のリポジトリ `unsloth/gemma-4-E4B-it-GGUF` の表示とも一致、利用の申請は不要）。README にモデル名・作成者・許諾を書いた。
- 通信するのはモデルのダウンロードの1回だけで、利用者がボタンを押したときだけ。そのとき Hugging Face は通常のダウンロードと同じく利用者の IP アドレスなどを受け取る。ページの文章・アドレスは送らない。
- 拡張機能の権限は、ボタン・メニュー・ショートカットを使ったタブにだけ入る activeTab と scripting、右クリックのメニュー（contextMenus）、翻訳プログラムとの通信（nativeMessaging）。保存するデータはない（モデルのファイルを除く）。
- ブラウザ本体の変更は、同梱のプログラムをアプリの中から探す1か所だけで、そのプログラムを起動できるのは翻訳の拡張機能だけ（マニフェストの `allowed_origins`）。
- アイコンは Dual の協力者による仮のドット絵（第三者の素材なし）。

## 2026-10-25 再確認（Dual 6.4.0 for Linux、プレビュー版）

Linux 版（x86_64・arm64 の tar.xz）を、リリース `v6.4.0-linux-preview` として配布します。macOS 版 6.4.0 と同じ変更を、Helium の Linux 版（helium-linux 0.20.1.1）に当てたものです。

- GPLv3 第6節の対応ソース：配布物と同じタグのこのリポジトリに、Linux 用のパッチ（`linux/dual-0.20.1.1-linux.patch`、`linux/linux-identity.patch`）、固定した上流（`source-lock.json` の `linux`）、ビルド手順（`BUILDING-linux.md`）、arm64 の機械でビルドの道具を用意するスクリプト（`linux/toolchain-arm64.sh`）、パッチを当てるスクリプト（`linux/apply.sh`）、配布物を作るスクリプト（`linux/package.sh`）、名称とロゴの置き換え（`dual_rebrand.py`、`branding/`）、同梱の拡張機能と翻訳プログラムのソースを置いた。配布物の `README.txt` に、ソースの場所（そのタグ）とライセンスを書いた。
- 配布物には GPL-3.0 の全文（`LICENSE`）を入れ、アプリ内の helium://credits（上流の帰属とライセンスの表示）は元のまま残している。翻訳プログラムが静的にリンクする llama.cpp・ggml と JSON for Modern C++ の MIT License の表示は、プログラムの隣（`dual-native-hosts/dual-translate-host-licenses/`）に入れた。ダウンロードに使う libcurl は、利用者のシステムのものを実行時に読み込み、配布物には含めない。
- helium-linux 0.20.1.1 の `LICENSE`（GPL-3.0）と `LICENSE.ungoogled_chromium`（BSD-3-Clause）を、`licenses/helium-linux-LICENSE.txt`、`licenses/helium-linux-LICENSE.ungoogled_chromium.txt` に変更せずに写した。
- `linux/fix-compiling-on-arm64.patch` は helium-linux 0.18.3.1（コミット 0e4e30b0）のものを変更せずに写した。arm64 の機械でビルドするための、ビルドの道具だけの変更で、プログラムには入らない。出所と許諾を `NOTICE.md` に書いた。
- 名称・ロゴ：アプリ内の名称とロゴは macOS 版と同じく Dual のもの（Helium のロゴは使っていない）。アプリケーション メニューの名前は「Dual」、アイコンは Dual の画像、設定フォルダ・デスクトップ エントリ・アイコン名は `dual-browser` で、Helium のもの（`net.imput.helium`、`helium.desktop`）と分けた。利用者が Helium と取り違えないため、また同じ機械の Helium の設定を変えないため。
- ビルド設定は helium-linux の構成手順のもの（`flags.gn` と `flags.linux.gn`）をそのまま使い、Dual では変えていない（PGO だけは使っていない）。
- Helium のプライバシーポリシーが Dual に適用されないことは README に、Dual が imput LLC・Helium の公式のものではないことは README と配布物の `README.txt` に書いた。

