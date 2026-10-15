# T-Display S3の実機試験

`tests/hardware`は、標準カウンターのC++ソースと本体のランタイムを使う診断用ファームウェアである。
GPIOの記録、入力注入、液晶メモリの読み戻し、描画データの回収を追加する。
通常のサンプルへ試験用コマンドを組み込まないため、試験終了後は標準サンプルを書き戻す。
[2026年10月15日の実施結果](hardware-results-2026-10-15.md)に、確認できた範囲と未確認の項目を記録している。

## ビルドと書き込み

リポジトリのルートで、[セットアップ](getting-started.md)を済ませて実行する。
以降のコマンド例は仮想環境を有効にした状態を想定する。

```sh
python -m platformio run -d tests/hardware
python -m platformio run -d tests/hardware -t upload --upload-port /dev/cu.usbmodem2101
```

ポート名は環境に合わせて変更する。
初回の書き込み前には、必要に応じて既存のフラッシュ全体を退避する。
退避したバイナリには機器固有の設定も含まれるため、Gitへ追加しない。
長い読み出しでUSB通信が途切れる場合は、esptoolの`--no-stub`と小さい読み出し範囲を試す。

## 自動診断

```sh
python scripts/test_hardware.py test --port /dev/cu.usbmodem2101
python scripts/test_hardware.py soak --port /dev/cu.usbmodem2101 --seconds 120
python scripts/test_hardware.py reboot --port /dev/cu.usbmodem2101 --reboots 3
python scripts/test_hardware.py frame --port /dev/cu.usbmodem2101
```

出力先は`.build/hardware/`配下の日時別ディレクトリである。
`--output`で未作成のディレクトリを指定することもできる。
既存の結果は上書きしない。
各回の`serial.log`に受信ログ、`result.json`に合否と測定値を残す。
描画回収時は`frame.png`と`frame.rgb565`も保存する。
`frame.png`は実機の描画データであり、液晶を撮影した写真ではない。

終了コードは合格が0、失敗が1、手押し試験の確認不足が2である。
応答が途絶えた場合や、必要な診断項目が欠けた場合も失敗として扱う。
シリアルモニターなど、同じポートを開く他のプログラムは閉じて実行する。
`soak`は初期値0で加算ボタンが選択された状態から始める。
各キー入力後の値と選択状態を照合し、終了時のメモリ回収と途中の再起動も調べる。

| 試験 | 確認内容 |
| --- | --- |
| `test` | 26項目。部品の配置、キー入力、長押し、状態変更、1万回の更新、1000回の画面作成と破棄、液晶6点の読み戻し |
| `soak` | 加算、選択移動、リセット、選択移動を指定時間繰り返し、各操作の結果と空きメモリを確認 |
| `reboot` | ソフトウェア再起動のたびに初期状態と全画面描画を確認 |
| `frame` | 実機のRGB565描画データを回収し、PNGへ変換 |

入力注入はLVGLの入力デバイスを通すが、GPIOの電圧変化やデバウンスは通らない。
これらは次の手押し試験で確認する。
電源の抜き差しとバッテリー給電は、自動再起動試験に含まれない。

## 実ボタンと目視の確認

```sh
python scripts/test_hardware.py manual --port /dev/cu.usbmodem2101 --seconds 120
```

`MANUAL_READY`が出たら、GPIO14の決定ボタン、GPIO0の選択ボタン、GPIO14の決定ボタンの順に押す。
各操作の間隔は1秒程度とし、押すたびに離す。
画面が「0から1」「Resetを選択」「1から0」の順に変わることを確認する。
記録したGPIOの押下と解放、値と選択状態の推移がそろうと、JSONの`physical_sequence_passed`が真になる。

目視では横向き320×170の配置、文字欠け、色、選択の枠、押している間の色を確認する。
初期状態の加算ボタンの色と枠だけで、押下の反応を判断しない。
人が正常表示を確認済みの場合に限り、`--optical confirmed`を付けて手押し試験を実行する。
表示に問題があると確認した場合は`--optical failed`を使う。
指定がなければ目視は未確認となり、実ボタンの試験に通っても全体の合格にはしない。
ボタン操作がない場合も、未確認として記録する。

## 別のHTML/CSSで表示を確認する

`examples/layout-check`は、固定幅での長文の折り返しとRGBの文字色を確認するサンプルである。
カウンターと同じIDと操作を維持し、HTML/CSSだけを差し替える。

macOSとLinuxでは、次のように入力HTMLを指定して診断ファームウェアをビルドする。

```sh
ESPHTML_TEST_UI=examples/layout-check/ui.html python -m platformio run -d tests/hardware
ESPHTML_TEST_UI=examples/layout-check/ui.html python -m platformio run -d tests/hardware -t upload --upload-port /dev/cu.usbmodem2101
python scripts/test_hardware.py frame --port /dev/cu.usbmodem2101
python scripts/test_hardware.py test --port /dev/cu.usbmodem2101 --layout-check
```

PowerShellでは`$env:ESPHTML_TEST_UI = "examples/layout-check/ui.html"`で設定する。
相対パスはリポジトリのルートを基準に解決する。
HTML/CSSを編集したら再ビルドし、値の更新と配置の変化を実機で確認する。
日本語や画像など、[現在の対応範囲](support.md)外の入力はコンパイラが診断する。
`--layout-check`では、文章の折り返しと配置、液晶メモリ内のRGBの各文字色を追加の5項目として要求する。

表示確認後、診断用コマンドを含まないサンプルとして使うこともできる。

```sh
python -m platformio run -d examples/layout-check -t upload --upload-port /dev/cu.usbmodem2101
```

診断は320×170、`value`、`increment`、`reset`、ボタンの高さ36px、背景色`#0f172a`を前提とする。
これらを変える場合は、診断側の期待値も変更する。
各画面の作成と破棄で入力グループが変わるため、診断では入力デバイスを切り離してから破棄し、再作成後に接続し直す。

## 試験終了後の標準サンプル

```sh
python -m platformio run -d examples/counter -t upload --upload-port /dev/cu.usbmodem2101
```

これで診断用コマンドを含まない標準カウンターに戻る。
このファームウェアには試験スクリプトの`STATUS`への応答がないため、試験スクリプトが接続できないのは想定どおりである。

## 液晶読み戻しの形式

TFT_eSPI 2.5.43の`readPixel()`は、このパラレルST7789構成では2バイトの読み出し分岐に入る。
診断ではRAMRD（0x2E）のダミー読み出し後にRGBの3バイトを読み、RGB565へ変換して照合する。
これは診断のための読み出しであり、標準サンプルの描画処理を変更しない。
PSRAM容量は、管理領域を除いたヒープAPI値と公称8 MBの差も考慮する。
