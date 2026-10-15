# ビルドと使い方

## セットアップ

リポジトリのルートで実行する。Python 3.10以上を使い、コンパイラとPlatformIOを同じ仮想環境へインストールする。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . -r requirements-build.txt
```

Windows PowerShellでは有効化に`.venv\Scripts\Activate.ps1`を使う。

## HTML/CSSからの変換

```sh
esp-html-ui compile examples/counter/ui.html --output build/generated --name counter --width 320 --height 170
```

`counter.h`、`counter.cpp`、`counter.json`を出力する。JSONには入力のハッシュ、コンパイラ・解析ライブラリの版、ID、部品数、フォント一覧を記録する。

`--name`はC++名前空間になる。小文字の英字で始まり、英数字・アンダースコアからなる識別子を使う。予約語・二重アンダースコア・LVGLの`lv_`接頭辞は使えない。

文法・対応範囲の検証が失敗した場合はC++を生成しない。既存の生成ファイルは保持し、コマンドは非ゼロで終了する。外部CSSは`link`、埋め込みCSSは`style`から読み込む。

## T-Display S3向けビルド

```sh
python -m platformio run -d examples/counter
```

ビルド前フックが毎回HTML/CSSを検証し、`examples/counter/generated/t-display-s3/counter/`に生成する。内容が変わらないファイルは更新しない。変換が失敗するとファームウェアのビルドも失敗する。

SSD1306向けサンプル、解像度の設定、別ディスプレイへの移植は[ディスプレイへの組み込み](displays.md)を参照する。

固定した主要依存:

| 項目 | バージョン |
| --- | --- |
| PlatformIO Core | 6.1.18 |
| espressif32プラットフォーム | 6.9.0 |
| LVGL | 9.4.0 |
| TFT_eSPI | 2.5.43 |
| html5lib / tinycss2 / cssselect2 | 1.1 / 1.4.0 / 0.8.0 |
| six / webencodings | 1.17.0 / 0.5.1 |

ビルドツールの間接依存まで完全に固定した配布用ロックは今後の作業。同じ環境・入力からのコード生成は再現性テストで確認している。

### 書き込み

標準のT-Display S3をUSB接続して実行する。

```sh
python -m platformio run -d examples/counter -t upload
python -m platformio device monitor -d examples/counter
```

必要に応じて`--upload-port`でポートを指定する。サンプルは横向き320×170で表示する。GPIO 0でボタンのフォーカスを進め、GPIO 14で選択中のボタンを押す。長押しで起動時のブート設定に入らないよう、通常操作は起動後に行う。

液晶電源はGPIO 15、バックライトはGPIO 38。ピン配置はTFT_eSPIのT-Display S3設定に従う。AMOLED版など別モデルには適用しない。

## C++ API

生成した型は`esphtml::generated::counter::Ui`。

```cpp
esphtml::generated::counter::Ui ui;

// lv_init()と表示の初期化後に呼ぶ。
ui.create(lv_screen_active());
ui.setText("value", "42");
ui.setDisabled("reset", true);
ui.setHidden("reset", false);
ui.focus("increment");
ui.onClick("increment", callback, userData);
```

| API | 契約 |
| --- | --- |
| `create(parent)` | 既存の画面を破棄して再作成。親の内容領域内に作る。LVGLと表示の初期化が必要 |
| `root()` / `find(id)` | LVGLオブジェクト参照。存在しなければ`nullptr` |
| `setText(id, text)` | ラベルまたはボタンの文字を更新。LVGLがコピーする。対象なし・不適合・null入力は`false` |
| `setHidden(id, bool)` | 非表示フラグを変更。CSSの初期状態も上書きできる |
| `setDisabled(id, bool)` | 無効状態を変更。現段階ではCSS状態スタイルの再計算はしない |
| `focus(id)` | フォーカス対象の要素へ移動。非表示・無効・対象外なら`false` |
| `onClick(id, callback, userData)` | クリック可能な要素にLVGLのコールバックを追加。繰り返すと追加登録になる |
| `group()` | ボタン等の入力グループ。キー入力デバイスに接続する |
| `clear()` | LVGLの部品とグループを破棄。繰り返し呼べる |

APIは`lv_timer_handler()`と同じタスクから使う。別のタスクのセンサー値はアプリ側のキューなどで引き渡す。

親の削除、IDを持つ部品の削除は自動で参照を無効にする。`find`で取得した生ポインターは削除後に再利用しない。ボタン内部のラベルを直接削除・再配置する操作はサポートしない。作成した画面を外部の親へ移し替えない。

画面の再作成・破棄で入力グループも変わるため、`group()`を接続した入力デバイスはアプリ側で付け替え・解除する。LVGL自体を終了する前に画面を破棄する。クリックコールバック中に画面を破棄した場合、そのコールバックで古い部品を以後使わない。

## ホスト上での検証

```sh
python -m unittest discover -s tests -v
python scripts/test_native.py --lvgl examples/counter/.pio/libdeps/t-display-s3/lvgl
```

後者はGCC/G++または互換のClangと`ar`があるホスト向け。LVGL 9.4.0の実際のソースをビルドし、生成UIの配置・描画・値更新・クリック・フォーカス・削除後の参照と、100回の作成／破棄でLVGLの空きメモリが戻ることを検証する。

描画結果は`.build/native/counter/counter.ppm`。これはホスト上の描画であり、液晶ドライバや物理ボタンの実機検証を代替しない。
