# Copyright (c) 2023 Kanta Yasuda (GitHub: @kyasuda516)
# This software is released under the MIT License, see LICENSE.

from pathlib import Path as __Path
from collections import namedtuple as __namedtuple
import re
from typing import Union as __Union
from typing import Tuple as __Tuple
import ast as __ast
from mylib.csv import load_csv_data as __load_csv_data

HOMEDIR = __Path.home()
APPDIR = __Path(__file__).parent.parent

POSTFIXES = __namedtuple('__PostFixes', 'q a')('_q', '_a')

def __modify_title(title: str):
  """不適切なタイトル（ページネーム）を修正する"""

  # パスに使えない文字はアンダーバーに変更
  title = re.sub(r'[\\/:\*\?"<>\|]', '_', title)
  # 連続する半角スペースはHTMLにおいて1スペースに圧縮されてしまい、
  # PDFダウンロード時に整合性がとれなくなるので、もとから名前を変えておく。
  title = re.sub(r'  +', ' ', title)
  return title

def target_pages(need_url=False) -> __Union[str, __Tuple[str]]:
  """対象のページのタイトル（必要に応じてURLも）のリストを返す
  
  デフォルトでは title のリストが返る。
  need_url=True にすると、(title, url) のリストが返る。
  """

  l = [
    ((__modify_title(row[0]), row[1]) if need_url else __modify_title(row[0]))
    for row in __load_csv_data(APPDIR / 'setting.csv')
    if __ast.literal_eval(row[2])   # 文字列がTrueに評価できれば
  ]
  return l
