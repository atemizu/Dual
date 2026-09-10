<p align="center"><img src="assets/logo.jpg" alt="Dual unofficial project logo" width="200"></p>




# Dual — 非公式派生版 / Unofficial derivative

**Heliumを改変した非公式派生版です。この改変部分はGPL-3.0で公開しています。imput LLC / Helium projectとは無関係の非公式プロジェクトであり、公式の製品・配布物・サポート窓口ではありません。**

macOS Apple Silicon向けに、左右それぞれ独立したBrowser・タブ一覧・アドレスバーを同じ外枠に収める変更です。左右はプロファイルを共有します。

<img width="2048" height="1597" alt="9a0d9fa4-64a4-49e1-a8d7-3c5a716ef3da" src="https://github.com/user-attachments/assets/d1a2b1b9-ded8-40ed-8b53-3f15ac118ce9" />

以前の開発名はHelium Dualです。既存のビルド手順・内部識別子・保存先には互換性のため旧名称が残ります。今回の公開プロジェクト名はDualです。

Dual is an unofficial modified version of Helium. The modifications are released under GNU GPL version 3 (GPL-3.0-only). This independent project is not affiliated with, sponsored by, or endorsed by imput LLC or the Helium project.

- 機能改変日：**2026年9月8日**
- 公開用のライセンス・改変表示・ドキュメント整備日：**2026年9月9日**
- 対応元：Helium 0.16.5.1 / Chromium 152.0.7977.82
- 改変箇所：[MODIFICATIONS.md](MODIFICATIONS.md)、[70ファイルの一覧](modifications.json)

## このリポジトリの公開範囲

**ソース差分と再現に必要な入力・スクリプトを公開するリポジトリです。完成アプリ・実行バイナリ・インストーラーの配布は含みません。** Chromium全体のミラーではなく、固定した上流コミットへ適用するパッチ方式です。GNU GPLv3第5節は、元のプログラムから改変版を作るための改変をソース形式で提供する場合も扱っています。

`helium-dual-window.patch` が変更の正本です。元のソースは `source-lock.json` のURL・固定コミット・ハッシュから取得します。元の著作権表示、ライセンス、第三者通知、creditsを維持してください。

[ビルド手順](BUILDING.md) · [検証範囲](VALIDATION.md) · [ライセンスと帰属](NOTICE.md) · [規約確認メモ](LEGAL-REVIEW-ja.md)

## ライセンス

独自コード・改変部分は **GNU General Public License version 3（GPL-3.0-only）** です。全文をルートの[LICENSE](LICENSE)に収録しています。GPLの条件に従って利用・改変・再配布できます。無保証です。

Helium固有のコード・改変部分には上流のGPL-3.0が適用されます。Chromium、ungoogled-chromium、その他の取り込み部分はそれぞれの元のライセンスと通知を保持します。ルートのGPL表示で、取り込み部分の著作権者・ライセンスを書き換えるものではありません。[licenses/](licenses/)と各ファイルの表示を参照してください。

## ロゴ

READMEのロゴは自作した独自画像です。

上流への謝意：[Helium](https://github.com/imputnet/helium)、[Helium macOS](https://github.com/imputnet/helium-macos)、[ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium)、[Chromium](https://www.chromium.org/)。本プロジェクト固有の問題を上流の公式サポートへ転送しないでください。

新規ファイルのヘッダーは[公式のCONTRIBUTING.md](https://github.com/imputnet/helium/blob/main/CONTRIBUTING.md#code-style)が案内する既存Heliumパッチの形式に合わせています。独自改変の著作権表示は既存のHelium Dual contributorsとし、元からある上流表示を保持しています。
