<p align="center"><img src="assets/logo.jpg" alt="Dual unofficial project logo" width="200"></p>

# Dual 5 — 左右独立ブラウザ / Independent dual-pane browser

Dual 5は、HeliumをベースにしたmacOS Apple Silicon向けの非公式派生ブラウザです。一般的なSplit Viewのように1つのタブバーを分けるのではなく、左右それぞれが独立したブラウザペインとして動作します。

Dual 5 is an unofficial Helium derivative for Apple Silicon macOS. Each side is an independent browser pane rather than a single tab strip split into two.

## できること / What it does

- 左右それぞれに独立したタブ一覧、アドレスバー、戻る・進む・再読み込みを表示
- 中央の分割バーをドラッグして、ドラッグ中も左右のページ幅をリアルタイムに追従
- 分割バーをつかむと手のカーソルを表示し、操作中もカーソル表示を維持
- 右ペインの幅が狭いときはアドレスバーを縮め、ツールバーの主要アイコンを残す
- ブラウザプロファイルは左右で共有

## ダウンロード / Download

[Dual-5-macOS-arm64.dmgをダウンロード](https://github.com/atemizu/Dual/releases/download/v5.0.0/Dual-5-macOS-arm64.dmg) · [すべてのリリース](https://github.com/atemizu/Dual/releases)

DMGを開き、Dual 5.appをApplicationsへコピーして起動してください。Apple Silicon搭載Mac向けです。配布物はアドホック署名で、Apple Developer ID署名・公証は完了していません。

## プロジェクトについて / Project status

以前の開発名はHelium Dualです。アプリ内部の互換性を保つため、保存先や一部の内部識別子には旧名称が残っています。Dualはimput LLC / Helium projectとは無関係の非公式プロジェクトです。

- 対応元：Helium 0.16.5.1 / Chromium 152.0.7977.82
- 対象：macOS arm64（Apple Silicon）
- 改変箇所：[MODIFICATIONS.md](MODIFICATIONS.md)、[modifications.json](modifications.json)
- ビルド手順：[BUILDING.md](BUILDING.md)
- 検証範囲：[VALIDATION.md](VALIDATION.md)

## ソースとライセンス / Source and license

変更の正本は[helium-dual-window.patch](helium-dual-window.patch)です。固定した上流コミットとハッシュは[source-lock.json](source-lock.json)に記録しています。

独自コードと改変部分はGNU General Public License version 3（GPL-3.0-only）です。[LICENSE](LICENSE)と[licenses/](licenses/)にライセンスおよび第三者通知を収録しています。

Dual is an unofficial modified version of Helium. It is not affiliated with, sponsored by, or endorsed by imput LLC or the Helium project. The modifications are released under GPL-3.0-only.
