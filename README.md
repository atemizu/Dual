<img width="2048" height="1597" alt="9a0d9fa4-64a4-49e1-a8d7-3c5a716ef3da" src="https://github.com/user-attachments/assets/a2d0ef63-2179-4c06-90b6-490c9ea6e2e2" />

# Dual 5 — Helium Browser非公式派生

一つのウィンドウ内に二つの独立したタブバーとブラウザ領域を持つことです。一般的なSplit Viewが二つのタブを並べるのに対し、本プロジェクトでは左右それぞれで複数のタブを独立して管理できます。  
同じことは二つのウィンドウを並べても実現できますが、本プロジェクトではその操作を一つのウィンドウ内に統合します。境界をドラッグすると左右の領域が連動してリサイズされるため、ウィンドウの配置やサイズを個別に調整する必要がありません。

## ダウンロード / Download

[Dual-5-macOS-arm64.dmgをダウンロード](https://github.com/atemizu/Dual/releases/download/v5.0.0/Dual-5-macOS-arm64.dmg) 

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
