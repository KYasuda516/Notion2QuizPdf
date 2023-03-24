from mylib import logging
from mylib.io import yes_no_input
from mylib.path import TempDirPath
# !conda install -c conda-forge selenium
from selenium import webdriver
# !conda install -c conda-forge python-chromedriver-binary==バージョン番号
# https://pypi.org/project/chromedriver-binary/#history
import chromedriver_binary   # chromedriver-binaryを使う
import time
import mymodule
# !conda install -c anaconda tqdm
from tqdm import tqdm
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from tqdm import tqdm
import warnings
warnings.simplefilter('ignore')

class Printer():
  from pathlib import Path as __Path
  from typing import Any

  def __init__(self, destination_dir: __Path):
    """初期化
    
    ブラウザーを開いたり。
    distination_dirには保存先のディレクトリパスを指定。
    なお、Chromeがすでに起動していても問題ない。
    """

    self.dest_dir = destination_dir
    self.__browser = self.__get_browser()

  def __get_browser(self) -> Any:
    """ブラウザを起動して返す
    
    Chromeがすでに起動していてもいい。
    なお、ヘッドレスモードじゃ無理！！！
    """

    # オプション設定
    options = webdriver.chrome.options.Options()
    # 不要な警告を非表示に
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # 最大化された画面に
    options.add_argument('--start-maximized')
    # 印刷をPDFで(https://degitalization.hatenablog.jp/entry/2021/03/13/102805)
    appState = {
      "recentDestinations": [
        {
          "id": "Save as PDF",
          "origin": "local",
          "account": "",
        }
      ],
      "selectedDestinationId": "Save as PDF",
      "version": 2,
      "pageSize": 'A4',
      "scalingType": 3, #倍率 0：デフォルト 1：ページに合わせる 2：用紙に合わせる 3：カスタム
      "scaling": "112", # 倍率カスタムの場合の数値
      "isHeaderFooterEnabled": False,
      "marginsType": 2,  #余白タイプ #0:デフォルト 1:余白なし 2:最小
    }
    options.add_experimental_option("prefs", {
      "savefile.default_directory": self.dest_dir.as_posix().replace('/', '\\'),   # download.default_directoryではない！
      "printing.print_preview_sticky_settings.appState": json.dumps(appState),
    })
    options.add_argument('--kiosk-printing')

    # ドライバ起動
    return webdriver.Chrome(options=options)

  def print(self, html_path: __Path):
    self.__browser.implicitly_wait(10)
    self.__browser.get(html_path.as_posix())
    # ページ上のすべての要素が読み込まれるまで待機
    WebDriverWait(self.__browser, 5).until(EC.presence_of_all_elements_located)
    # PDFとして印刷
    self.__browser.execute_script('window.print();')
    # 待機
    time.sleep(3)   # 2秒だとけっこうギリギリ
    logging.info(f'Downloaded {html_path.name}')

  def __del__(self):
    """ブラウザーを閉じる"""
    
    self.__browser.close()  # アクティブなタブのみ終了。
    self.__browser.quit()   # すべてのタブを閉じてブラウザを終了。（ないとダメだ！）
    logging.info('Closed browser')

def main():
  # 対象のHTMLファイルのパスのリスト
  HTMLDIR  = mymodule.APPDIR / 'html/reformed/'
  srcs = []
  for title in mymodule.target_pages():
    src_q = HTMLDIR / f'{title}{mymodule.POSTFIXES.q}.html'
    src_a = HTMLDIR / f'{title}{mymodule.POSTFIXES.a}.html'
    # もととなるHTMLファイルが実際に存在していなければ、ログに書いたうえでスキップ
    if not all([src_q.exists(), src_a.exists()]):
      logging.info(f'Missed the file "{src_q.name}" or "{src_a.name}"')
      continue
    srcs.append(src_q)
    srcs.append(src_a)

  # 仮の保存先（新しいフォルダに保存しないと名前が変えられてしまうので）
  tempdir = TempDirPath()
  # 本当の保存先
  PDFDIR = mymodule.APPDIR / 'pdf/src/'

  printer = Printer(tempdir)
  bar = tqdm(srcs)
  bar.set_description('Printing PDF')
  # HTMLファイルを順々に処理
  try:
    for src in bar:
      printer.print(src)
    # 一時フォルダ内のファイルをすべてPDFDIRに移動。
    tempdir.move_contents(PDFDIR)   # すでにファイルが存在していても上書きする。
  finally:
    del tempdir
    del printer

if __name__ == '__main__':
  # 実行の確認
  if not yes_no_input("I'll convert HTML into PDF. Ready?"):
    exit()
  
  main()
