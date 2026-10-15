# 依存候補とライセンス管理

状態: 0.1で採用した構成と、今後の候補を管理する。依存ライブラリ本体はpip / PlatformIOで取得し、必要な通知は[third_party](../third_party/dependencies.json)に保存している。

## 0.1で採用した構成

- ホスト: html5lib 1.1、tinycss2 1.4.0、cssselect2 0.8.0と、six 1.17.0、webencodings 0.5.1。
- 描画: LVGL 9.4.0。内包するTLSF、printf、Montserrat、Font Awesomeの通知も保存。
- 液晶ドライバ: TFT_eSPI 2.5.43。オプションのフォントパックは使わない。
- 基板のフレームワーク: Arduino-ESP32 2.0.17（PlatformIOパッケージ3.20017.241212+sha.dcc1105b）、espressif32 6.9.0。

Arduino APIにはLGPL-2.1-or-laterの部分がある。LVGLやコンパイラ依存のMIT/BSDとは別の条件として扱う。ファームウェアを配布する前に、Arduino・SDK・プリコンパイル済みライブラリ・C/C++ランタイムを含むリンク済み構成を棚卸しし、ソース提供・再リンクなど適用される条件を確認する。

現在は開発用ソースを公開しており、ファームウェアバイナリのリリースは行っていない。採用したGUI依存の通知を揃えたことと、ファームウェア全体の配布監査が完了したことは区別する。

通知の再収集は、依存をインストールした環境で実行する。

```sh
python scripts/collect_notices.py \
  --lvgl examples/counter/.pio/libdeps/t-display-s3/lvgl \
  --tft examples/counter/.pio/libdeps/t-display-s3/TFT_eSPI \
  --webencodings-license third_party/notices/webencodings.txt
```

webencodings 0.5.1のPyPI wheel / sdistにはLICENSEが欠けているため、上流のv0.5.1のコミットから取得して保存した。元の参照先と通知のハッシュは依存一覧に記録している。

## 候補

2026-10-15に下記の公式ライセンスファイルを確認した。main/masterへの参照は予備調査であり、実際に採用する版の監査結果ではない。

| 用途 | 候補 | 確認したライセンス | 公式ファイル |
| --- | --- | --- | --- |
| HTML解析 | html5lib | MIT | [LICENSE](https://github.com/html5lib/html5lib-python/blob/master/LICENSE) |
| CSS解析 | tinycss2 | BSD-3-Clause | [LICENSE](https://github.com/Kozea/tinycss2/blob/main/LICENSE) |
| セレクター照合 | cssselect2 | BSD-3-Clause | [LICENSE](https://github.com/Kozea/cssselect2/blob/main/LICENSE) |
| GUI | LVGL | MIT | [v9.4.0 LICENCE.txt](https://github.com/lvgl/lvgl/blob/v9.4.0/LICENCE.txt) |
| フォント変換 | lv_font_conv | MIT | [LICENSE](https://github.com/lvgl/lv_font_conv/blob/master/LICENSE) |
| 液晶ドライバ | TFT_eSPI | 独自部分はFreeBSD。MIT/BSD由来の部分やフォントに別の通知がある | [license.txt](https://github.com/Bodmer/TFT_eSPI/blob/master/license.txt) |

上記の候補調査からLVGL 9.4.0とTFT_eSPI 2.5.43を選び、基板向けビルドを確認した。lv_font_convはアセット変換を実装する際の候補であり、現在の依存には含めていない。

## 採用・配布時のルール

1. バージョンまたはコミットと取得元を固定する。
2. 固定した版のライセンスと、間接依存・同梱物のライセンスを確認する。
3. ビルドツールとしてPCだけで使う依存と、ファームウェアに入る依存を区別する。
4. 元の著作権表示、ライセンス本文、必要なNOTICEを保持する。
5. ソース配布・バイナリ配布それぞれに必要な通知を揃える。
6. サブセット化・変換後のフォントや画像にも、素材自体の条件を適用する。変換ツールのライセンスだけで判断しない。
7. GPL/LGPL等、追加の配布条件がある依存は、用途・リンク方法・配布物への影響を評価してから採用を決める。
8. 配布時に`THIRD_PARTY_NOTICES`と依存一覧を生成する。

## 生成コード・アセット

- 生成器からコピーされるテンプレート部分のライセンスを明記する。
- HTML/CSSの入力者が持つ権利と、生成器・依存ライブラリの権利を区別する。
- 日本語フォントやアイコンは、再配布・改変・サブセット化の可否と、名称に関する条件を確認する。
- 出所と利用条件が確認できない素材をサンプルに含めない。

## プロジェクト本体

本体のライセンスは未決定。選定後にルートの`LICENSE`へ明記する。
