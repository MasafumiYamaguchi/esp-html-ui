# 他のUI開発ツールとの比較

[日本語](comparison.md) | [English](comparison.en.md)

esp-html-uiは、HTML/CSSからESP32のディスプレイ向けのLVGL用C++を生成するツールである。
画面の構造とスタイルをテキストで編集し、操作時の処理をC++で書く用途に向いている。
比較では、入力する形式、生成するコード、実機上で動かすものを分けて考える。

以下は2026年10月15日時点の公式文書と、このリポジトリの実装に基づく整理である。
他ツールを同じ実機で動かす比較試験は行っていない。
用途の提案は、確認した開発方式からの判断である。

## 記述形式と実行方式

| 選択肢 | UIの入力 | 生成または実行の方式 | 選ぶ理由となる用途 |
| --- | --- | --- | --- |
| **esp-html-ui 0.1** | 対応範囲を定めたHTML/CSS | ビルド時にC++へ変換。実機では生成コード、本体のC++ランタイム、LVGL、液晶ドライバを動かす | HTML/CSSでラベルとボタンの画面を編集し、ESP32のC++アプリへ組み込む |
| [LVGLのC API](https://lvgl.io/docs/open/9.4/details/widgets/index.html) | C/C++でウィジェットとスタイルを定義 | アプリからLVGLを直接呼び出す | LVGLの部品やスタイルを直接扱う |
| [SquareLine Studio](https://docs.squareline.io/docs/introduction/typical_dev/) | GUIでウィジェット、スタイル、イベントを設定 | 画面、画像、フォントなどのCファイルを出力し、アプリへ組み込む | 画面を見ながら配置とイベントを編集する |
| [EEZ Studio](https://www.envox.eu/studio/studio-introduction/) | ビジュアルエディター。LVGLとLVGL＋Flowの構成がある | LVGL向けの画面を作成。EEZ Flowを使うと処理もビジュアルに記述できる | 画面と処理の流れをエディター内で編集する |
| [LVGL Pro](https://lvgl.io/docs/pro/integration/using-exported-c-code) | XMLをエディターやCLIで扱う | XMLからCを生成して組み込む方式がある | XMLでコンポーネントを定義し、LVGL向けコードを生成する |
| [lvgljs](https://github.com/lvgl/lv_binding_js) | JavaScriptとReactの仮想DOMの考え方による記述 | txiki.jsとQuickJSを含むJavaScript実行環境からLVGLを操作する | JavaScriptで画面と振る舞いを記述する |
| [Evue](https://github.com/scriptiot/evue) | HTML/CSSを基にしたevue形式 | PythonまたはJavaScriptへ変換する構成を説明している | HTML/CSSを基に、スクリプト言語や複数のUIエンジンを使う |

## esp-html-uiで短くできる作業

HTML/CSSで色や余白、配置を変えたら、同じPlatformIOのビルドコマンドを再実行できる。
[ビルド前フック](../scripts/platformio_codegen.py)が対応範囲を検証し、生成コードをコンパイル対象へ追加する。
標準のT-Display S3向けに、液晶、バックライト、電源、物理ボタンの設定を含む[サンプル](../examples/counter)を用意している。

アプリの動作はC++側で管理できる。
HTMLのIDを使う[参照と更新のAPI](getting-started.md#c-api)で、表示文字列やクリック通知、フォーカスを扱う。
[表示確認サンプル](../examples/layout-check)はカウンターと同じC++実装を共有し、HTML/CSSを差し替えている。

確認の手順もリポジトリ内で共有できる。
[実機試験ツール](hardware-testing.md)には、入力注入、画面作成と破棄、液晶メモリの読み戻し、描画データの回収をまとめている。
これは本プロジェクトに用意した試験手段であり、他ツールと比べた性能の優位性を示すものではない。

ESP32＋SSD1306の128×64向けにも、白黒OLED用の[サンプルと移植手順](displays.md)を用意している。
SSD1306はビルドとホスト描画を検証済みであり、OLED実機での表示は未確認である。

## 共通する機能と異なる入力

コード生成とビルドの自動化には、複数の選択肢がある。
[SquareLine StudioのCLI](https://docs.squareline.io/docs/commandline/)は、プロジェクトからのエクスポートを自動化できる。
[LVGL Proのコード生成](https://lvgl.io/docs/pro/integration/using-exported-c-code)は、エディターとCLIの両方に対応し、生成したCを使う場合には実機にXMLファイルを残す必要もない。
esp-html-uiの違いは、HTML/CSSの解析とCSSの解決をPC上で行い、生成したC++をESP32向けのビルドへつなぐ点にある。

HTML/CSSをUIの入力に使う取り組みも、esp-html-uiに限られない。
[Evueの公式README](https://github.com/scriptiot/evue)は、HTML/CSSを基にした記述からPythonやJavaScriptへ変換する構成を説明している。
esp-html-uiはC++への変換を実装し、対応するHTML/CSSと、カラー液晶や白黒OLEDへの組み込み手順を定めている。

## 現在の選択範囲

HTML/CSSに慣れていて、ESP32のディスプレイに値の表示やボタン操作を加えたい場合は、esp-html-uiのサンプルから試せる。
UIの編集、C++からの更新、書き込み、実機での確認を一通り行える。
現在の対応は[タグとCSSの一覧](support.md)、確認済みの動作は[実機試験結果](hardware-results-2026-10-15.md)を参照する。

テキスト入力やスライダー、画像、日本語フォント、Grid、CSSの動的状態などは、esp-html-ui 0.1では未実装である。
GUIでの画面編集、Flowでの処理の記述、JavaScriptでのアプリ開発などが必要なら、上表の対応するツールを検討できる。
LVGLの機能を直接使いたい場合は、C APIも選択肢になる。

## 比較に使用した公式資料

- [LVGL 9.4のウィジェットAPI](https://lvgl.io/docs/open/9.4/details/widgets/index.html)
- [SquareLine Studioの開発手順](https://docs.squareline.io/docs/introduction/typical_dev/)と[コマンドライン出力](https://docs.squareline.io/docs/commandline/)
- [EEZ Studioの紹介とプロジェクト構成](https://www.envox.eu/studio/studio-introduction/)
- [LVGL Proの生成Cコードの組み込み](https://lvgl.io/docs/pro/integration/using-exported-c-code)
- [lvgljs公式リポジトリ](https://github.com/lvgl/lv_binding_js)
- [Evue公式リポジトリ](https://github.com/scriptiot/evue)
