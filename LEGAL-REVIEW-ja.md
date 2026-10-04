# 規約・公開条件の確認メモ

確認日：2026-09-09、再確認 2026-09-29（Dual 6.2.2 のソースとアプリ配布）。以下は公開準備に用いた文書の読み取りと対応内容であり、個別事情を含む法的適合性の保証ではありません。

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
