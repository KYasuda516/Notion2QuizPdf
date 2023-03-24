from mylib import logging
from mylib.io import yes_no_input
from mylib.path import TempDirPath
import mylib.subproc
import mylib.csv
import mymodule
# !conda install -c conda-forge selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# !conda install -c conda-forge python-chromedriver-binary==バージョン番号
# https://pypi.org/project/chromedriver-binary/#history
import chromedriver_binary
# !conda install -c anaconda tqdm
from tqdm import tqdm
import time
from datetime import datetime, timedelta
import shutil
import io
from collections import namedtuple

Selector = namedtuple('Selector', 'name description content')

class NotionHtmlDownloader():
  """Notion記事のHTMLのダウンローダー
  
  一時フォルダをつくり、そこへいったんダウンロード。
  そこで解凍してHTMLファイル以外削除。
  そしてHTMLファイルを指定されたダウンロード先へ移動させる。"""
  from pathlib import Path as __Path
  from typing import Any

  def __init__(self, destination_dir: __Path):
    """初期化
    
    一時フォルダを作ったり、
    ブラウザーを開いたり。
    distination_dirには保存先のディレクトリパスを指定。
    """
    
    self.dest_dir = destination_dir

    # 一時フォルダを作成
    self.__tempdir = TempDirPath()

    # 起動中のウィンドウを閉じて、ブラウザーを起動
    self.__close_working_windows()
    time.sleep(1)
    self.__browser = self.__get_browser()

  def __close_working_windows(self) -> None:
    """起動中のChormeウィンドウを閉じる"""
    csv_str = mylib.subproc.run('tasklist', '/fo', 'csv')
    csv_buf = io.StringIO()
    csv_buf.write(csv_str)
    csv_buf.seek(0)
    csv_data = mylib.csv.load_csv_data2(csv_buf)
    pid_list = [csv_data['PID'][idx] for idx, image_name in enumerate(csv_data['イメージ名']) if image_name == 'chrome.exe']
    
    # 起動中でなければ閉じる必要はないので終了
    if len(pid_list)==0: return

    time.sleep(1)
    commands = ['taskkill']
    for pid in pid_list:
      commands.append('/PID')
      commands.append(str(pid))
    stdout = mylib.subproc.run(*commands)
    
  def __get_browser(self) -> Any:
    """ブラウザを起動して返す
    
    Chromeがすでに起動していてはいけない。
    self.__tempdirがセットされている必要がある。
    """

    options = webdriver.chrome.options.Options()
    # ダウンロードファイルの保存先を変更
    options.add_experimental_option("prefs", {"download.default_directory": self.__tempdir.as_posix().replace('/', '\\') })
    # 不要な警告を非表示に
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # 起動時のウィンドウサイズを最大にする
    options.add_argument('--start-maximized')
    # Googleアカウントでログインしてスタートページを開く
    datadir = mymodule.HOMEDIR / 'AppData/Local/Google/Chrome/User Data'
    datadirstr = datadir.as_posix().replace('/', '\\')  # \を含むコードを変数展開に組み込むことは不可能なので一時変数を設ける
    options.add_argument(f"--user-data-dir={datadirstr}")
    options.add_argument("--profile-directory=Default")
    # ブラウザを起動
    return webdriver.Chrome(options=options)

  def download(self, url: str, title: str):
    """NotionページのHTMLをダウンロード
    
    5回までチャレンジするが、最後までできない可能性もある。
    """
    
    for try_count in range(5):
      # ページ遷移またはリロード
      if try_count == 0:
        self.__browser.get(url)
      else:
        self.__browser.refresh()
      time.sleep(1)

      # 一時フォルダ内のものをすべて削除
      self.__tempdir.empty()

      # ブラウザでHTMLをエクスポートする
      export_complete = False
      # セレクタのリスト
      selectors = [
        Selector('button1', '右上のメニューボタン', "#notion-app > div > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div.notion-topbar > div > div.notion-topbar-action-buttons > div:nth-child(2) > div.notion-topbar-more-button"),
        Selector('button2', 'ボタン「エクスポート」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div:nth-child(1) > div:nth-child(7) > div:nth-child(2)"),
        Selector('select1', 'ドロップダウンリスト「エクスポート形式」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div > div:nth-child(1) > div:nth-child(2)"),
        Selector('option1', '項目「HTML」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(3) > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div:nth-child(2)"),
        Selector('select2', 'ドロップダウンリスト「対象コンテンツ」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div > div:nth-child(2) > div:nth-child(2)"),
        Selector('option2', '項目「ファイルや画像以外」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(3) > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div:nth-child(2)"),
        Selector('toggle1', 'トグルボタン「サブページのフォルダーを作成」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div > div:nth-child(4) > div:nth-child(2) > input[type=checkbox]"),
        Selector('toggle2', 'トグルボタン「サブページを含める」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div > div:nth-child(3) > div.pseudoHover.pseudoActive > input[type=checkbox]"),
        Selector('submit', 'サブミットボタン「エクスポート」', "#notion-app > div > div.notion-overlay-container.notion-default-overlay-container > div:nth-child(2) > div > div:nth-child(2) > div > div:nth-child(5) > div:nth-child(2)")
        ]
      # 順々にボタンを押してゆく
      toggle2is_on = False
      export_complete = False
      for selector in selectors:
        # トグル1以外ならクリックする（かも）
        if selector.name != 'toggle1':
          # トグル2の場合に限り、クリック不要の指示があるときはクリックしない
          if selector.name == 'toggle2' and toggle2is_on == False: continue
          try:
            WebDriverWait(self.__browser, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector.content)))
          except:
            break
          else:
            time.sleep(0.3)
            self.__browser.find_element(By.CSS_SELECTOR, selector.content).click()
        # トグル1はクリックせず属性の確認だけ
        else:
          try:
            WebDriverWait(self.__browser, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector.content)))
          except:
            break
          else:
            # disabled属性が付帯しているか
            if self.__browser.find_element(By.CSS_SELECTOR, selector.content).is_enabled():
              toggle2is_on = True
      # selectorを順当に処理していけたなら（breakされなければ）エクスポート成功とみなす
      else:
        export_complete = True
      # エクスポートに成功していなければチャレンジをやり直す
      if not export_complete: continue

      # 最大20秒間ダウンロードを待つ
      try:
        self.__wait_until_completing(20)
        time.sleep(1)
      # 長すぎたり、一時フォルダ内のファイルが2個以上なら異常なので、チャレンジをやり直す
      except:
        continue

      # ZIPを解凍
      for p in self.__tempdir.iterdir():
        if p.suffix == '.zip':
          shutil.unpack_archive(p.as_posix(), self.__tempdir.as_posix())
          break
      # ZIPファイルがないなら異常なので、チャレンジをやり直す
      else:
        continue

      # HTMLファイルの名前を変更しつつ、目的のフォルダへと移動させる
      for p in self.__tempdir.iterdir():
        if p.suffix == '.html':
          shutil.move(p.as_posix(), self.dest_dir / f'{title}.html')
          break
      # HTMLファイルがないなら異常なので、チャレンジをやり直す
      else:
        continue
      
      # ログ書いて終わる
      logging.info(f'Downloaded {title}.html')
      return
    
    else:
      # 失敗のログを書いて終わる
      logging.info(f'Failed to download {title}.html')
      return

  def __wait_until_completing(self, timeout_second: float) -> None:
    """最大timeout_second秒のあいだダウンロードを待つ。
    
    このメソッドは、このメソッド実行前において一時フォルダ内が空であることが前提となっている。
    """
    started = datetime.now()
    # ファイル一覧取得
    # 現在時刻と開始時刻との差が指定時間以上になったらやめる。
    while datetime.now() - started < timedelta(seconds=timeout_second):
      # ちゃんと待つことにした（久しぶりに起動すると鈍いから）
      time.sleep(1)
      file_list = list(self.__tempdir.iterdir())
      # ファイルが1つも存在しない場合
      if len(file_list) == 0:
        # 次の回へ
        continue
      # ファイルが1つだけ存在する場合
      elif len(file_list) == 1:
        # 拡張子が '.crdownload' の場合は、続ける
        if file_list[0].suffix == ".crdownload":
          continue
        # 拡張子が '.crdownload' でない場合
        # ちょっと待ってからもう一度確認
        time.sleep(1)
        if file_list[0].suffix == ".crdownload":
          continue
        # ダウンロード完了と判断し、待機を抜け、かつ関数の処理じたいも終わる
        return
      # ファイルが2つ以上存在する場合
      else:
        # とりあえずダウンロード中のファイルがあれば待ったあと、異常だよというエラーを発出
        while any([p.suffix == ".crdownload" for p in file_list]):
          time.sleep(1)
        raise SystemError('一時フォルダ内に2個以上のファイルが存在しました。')
    # 長すぎるよというエラーを発出
    raise TimeoutError('Download will take forever!')
     
  @classmethod
  def recover_chrome(cls):
    """Chromeのダウンロード先を元に戻す"""

    # オプション変数を作成
    options = webdriver.chrome.options.Options()
    # ヘッドレスモードで開く
    options.add_argument('--headless')
    # ダウンロードファイルの保存先を変更
    dldir = mymodule.HOMEDIR / 'Downloads'
    options.add_experimental_option("prefs", {"download.default_directory": dldir.as_posix().replace('/', '\\') })
    # 不要な警告を非表示に
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # Googleアカウントでログインしてスタートページを開く
    datadir = mymodule.HOMEDIR / 'AppData/Local/Google/Chrome/User Data'
    datadirstr = datadir.as_posix().replace('/', '\\')   # \を含むコードを変数展開に組み込むことは不可能なので一時変数を設ける
    options.add_argument(f"--user-data-dir={datadirstr}")
    options.add_argument("--profile-directory=Default")
    # 一時ブラウザを起動
    browser = webdriver.Chrome(options=options)
    # 一時ブラウザを終了
    browser.quit()

    logging.info('Recovered Chrome')

  def __del__(self):
    """一時フォルダを削除し、ブラウザーを閉じる"""
    
    del self.__tempdir

    self.__browser.close()  # アクティブなタブのみ終了。
    self.__browser.quit()   # すべてのタブを閉じてブラウザを終了。（ないとダメだ！）

    logging.info('Closed browser')

def main():
  # URLの取得
  urls = { title: url for title, url in mymodule.target_pages(need_url=True) }

  # 各NotionページのHTMLをダウンロード
  EXPDIR = mymodule.APPDIR / 'html/src'
  loader = NotionHtmlDownloader(EXPDIR)
  logging.info('Browser Open')
  bar = tqdm(list(urls.items()))
  bar.set_description('Downloading Notion Article')
  try:
    for title, url in bar:
      loader.download(title=title, url=url)
  finally:
    del loader

if __name__ == '__main__':
  # 実行の確認
  print("I'll download notion documents.")
  if not yes_no_input('May I close Google Chrome windows?'):
    exit()
  
  main()
  NotionHtmlDownloader.recover_chrome()
