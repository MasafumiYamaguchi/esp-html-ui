# 現在の対応状況

対象: 0.1のコンパイラ基礎実装。全体の完成範囲は[仕様書](spec.md)を参照。

コンパイラとC++ランタイムはLVGL経由でディスプレイへ接続する。
T-Display S3のカラー液晶とESP32＋SSD1306の白黒OLED向けサンプルを用意している。
基板ごとの設定と実機確認の範囲は[ディスプレイへの組み込み](displays.md)を参照。

機械可読の一覧は`esp-html-ui support`、元データは[src/esp_html_ui/capabilities.json](../src/esp_html_ui/capabilities.json)。未対応のタグ、属性、プロパティ、使用する値は診断する。

## 実装済みタグ

| タグ | 変換・制約 |
| --- | --- |
| `html`, `head`, `title` | 文書構造・メタデータ。`html`の`lang`を受け付ける。HTMLの省略可能な要素はhtml5libが補う |
| `meta` | `charset="utf-8"`のみ |
| `link` | `rel="stylesheet" href="ui.css"`。HTMLからの相対パスでローカルCSSを読む。`type="text/css"`は省略可 |
| `style` | 埋め込みCSS。外部CSSと文書順に適用。`type="text/css"`は省略可 |
| `body` | 生成画面のルート。指定した親オブジェクトの内容領域いっぱいに作る |
| `div`, `main`, `section`, `article`, `header`, `footer`, `nav`, `aside` | `lv_obj`。既定は幅100%、高さ内容依存、縦方向Flex。直下の文章はテキスト要素で囲む |
| `h1`–`h6`, `p`, `span`, `label`, `output` | `lv_label`。現在は文字だけを含められる。見出しの既定サイズはh1=32、h2=24、h3=20、h4–h6=16px |
| `button` | `lv_button`＋内部ラベル。`type="button"`のみ。文字だけを含められる |

共通属性: `id`, `class`, `style`, `hidden`, `tabindex`。

- IDは空・空白文字・重複を許可しない。
- `class`はビルド時の照合に使う。実行中のクラス切替は未対応。
- `hidden`はHTMLの真偽属性。`hidden="false"`でも初期状態は非表示。
- `tabindex="0"`でフォーカス対象、`-1`で対象外。既定でボタンをフォーカス対象にする。正の順序指定は未対応。
- ボタンは`disabled`を受け付ける。フォーカス順はHTMLの順番。
- `label`の`for`やフォームの振る舞いは未対応。現在の`label`はテキスト表示のみ。
- 画面あたり最大128個の描画要素。内部のボタンラベルはこの個数に含めない。
- 日本語・画像・リッチテキスト用アセット処理は未対応。現在の文章は印字可能ASCIIと改行・タブに限定し、足りない文字は変換時に診断する。

## 実装済みCSS

| プロパティ | 値・意味 | LVGLへの対応 |
| --- | --- | --- |
| `display` | `flex`, `none` | コンテナーのFlex配置／非表示フラグ |
| `width`, `height` | 整数`px`、整数`%`の0–100、`auto`、単位なしの`0` | 幅・高さ、`lv_pct`、`LV_SIZE_CONTENT` |
| `box-sizing` | `border-box`のみ | 枠・余白を含むLVGLの寸法指定 |
| `padding`、各辺 | 0–32767の整数`px`か単位なし`0`。短縮形は1–4値 | `pad_top/right/bottom/left` |
| `gap` | 1–2値の整数`px`か`0`。1つ目が行、2つ目が列 | `pad_row`, `pad_column` |
| `row-gap`, `column-gap` | 同上 | 行・列間隔 |
| `flex-direction` | `row`, `column`, `row-reverse`, `column-reverse` | `lv_obj_set_flex_flow` |
| `flex-wrap` | `nowrap`, `wrap` | LVGLの行折り返し。`wrap-reverse`は未対応 |
| `flex-grow` | 0–255の整数 | LVGLの主軸の空き領域配分 |
| `justify-content` | `flex-start`, `center`, `flex-end`, `space-between`, `space-around`, `space-evenly` | 主軸配置 |
| `align-items` | `flex-start`, `center`, `flex-end` | 交差軸配置。`stretch`は未対応 |
| `align-content` | `justify-content`と同じ値 | 折り返したトラックの交差軸配置 |
| `color` | CSS Color 3の色名、16進数、`rgb/rgba/hsl/hsla`、`transparent` | 文字色と文字不透明度 |
| `background-color` | 同上 | 背景色と背景不透明度 |
| `border-color` | 同上 | 枠色と枠不透明度 |
| `border-width` | 整数`px`か`0` | 全辺の実線の枠幅 |
| `border-radius` | 整数`px`か`0`の1値 | 全角共通の半径 |
| `opacity` | 0–1の数値、0–100% | LVGLの不透明度。8bitに量子化 |
| `font-size` | 14、16、20、24、32px | 同梱Montserratフォント |
| `text-align` | `left`, `center`, `right` | ラベル内の文字揃え |
| `white-space` | `normal`, `nowrap`, `pre` | 空白の正規化とラベルの改行・クリップ設定 |
| `text-overflow` | `clip`, `ellipsis` | 通常表示／`LV_LABEL_LONG_DOT`。省略には幅の制約が必要 |
| `overflow` | `hidden`, `auto`, `scroll` | コンテナー・ボタンのスクロール設定。ラベル自体は長文表示設定で処理する |

`currentColor`、小数ピクセル、長さの負値、`calc()`、相対単位、複合短縮形は未対応。CSS配置の詳細な振る舞いはLVGLに従う。

### カスケード・セレクター

- タグ、ID、クラス、属性、複合、子孫・子・隣接・後続、グループ、構造擬似クラスはcssselect2で照合する。
- 詳細度、ソース順、インラインスタイル、`!important`を解決してから長辺ごとのスタイルを生成する。
- `color`, `font-size`, `text-align`, `white-space`を継承する。見出しのサイズは既定スタイルで上書きする。
- 通常のプロパティは`inherit`, `initial`, `unset`を受け付ける。
- `--name`カスタムプロパティ、継承、`var()`とフォールバックに対応。未使用の無効な変数は無視し、使用時に有効な値を得られなければ診断する。
- `:active`, `:focus`, `:checked`, `:disabled`などの動的擬似クラス、擬似要素、CSS at-ruleは今後の実装。
- `html`の`lang`は静的なセレクター照合に使える。描画時の言語別処理を実装したことは意味しない。

### ブラウザとの主な違い

- コンテナーは既定で縦方向Flex。文章はラベルになり、CSSの通常フロー・インラインボックスモデルは再現しない。
- 余白・枠・スクロールを除去した部品に、生成したスタイルを適用する。ブラウザの既定マージンはない。
- サイズの`auto`は内容依存。Flexの自動縮小や`flex-basis`はまだない。
- 文字要素の入れ子と文章とブロックの混在は未対応。別々の要素として明示する。
- ラベル・ボタン内の文字はLVGLのラベルで描画する。配置プロパティはコンテナーの子要素配置に適用する。
- `setText`などC++からの更新時にはCSSを再解析しない。

## 診断

HTML修復エラーは元HTMLの行・列、CSSはCSS内の行・列を表示する。HTMLの意味上のエラーにはファイル名とタグ・IDを表示する。埋め込みCSS／style属性の位置は、そのブロック／属性内の位置であり元HTML全体の位置ではない。

## 今後の対応

| 分類 | 状態・方針 |
| --- | --- |
| 入力部品 | 未実装。テキスト入力、選択、スライダー、チェック、フォームをLVGL部品へ対応付ける |
| その他のタグ | 未実装。リスト・画像・表・開閉要素・カスタム部品を順次追加 |
| Grid・配置拡張 | 未実装。トラック指定、配置・重なり、サイズ制約、marginなどの意味を定義 |
| 動的なCSS | 未実装。LVGLのstate/part、クラス切替を生成済みデータで処理する |
| 画像・日本語 | 未実装。既存コンバーターを活用し、フォントと画像をビルド時に変換 |
| アニメーション | 未実装。transition・keyframesとLVGLの補間・タイマーを対応付ける |
| ライセンス配布処理 | 選択したGUI依存の通知を保存済み。ファームウェア全体の監査・配布パッケージ作成は未完了 |

この一覧を埋めていくことが全体の目標。0.1は変換・描画・基板ビルドまでの土台。
