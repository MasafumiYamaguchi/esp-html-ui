# 依存候補とライセンス管理

状態: 採用前の候補一覧。ライブラリのコードはこのリポジトリに同梱していない。

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

LVGL v9.4.0のライセンス確認は、実装バージョンを決定したことを意味しない。液晶ドライバも、ビルド互換性とライセンスを確認したうえで選定する。

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
