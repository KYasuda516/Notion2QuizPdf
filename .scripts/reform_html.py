# Copyright (c) 2023 Kanta Yasuda (GitHub: @kyasuda516)
# This software is released under the MIT License, see LICENSE.

# from mylib import logging
from bs4 import BeautifulSoup
import mymodule
from pathlib import Path
import re
from fractions import Fraction
import unicodedata
from tqdm import tqdm
from queue import LifoQueue
from dataclasses import dataclass

def lenz(s: str):
  """全角を1として、だいたいの文字列の長さを返す
  
  zは全角のz。
  """
  PATTERNS = {
    ",:;": "2/9",
    "'‘`": "3/13",
    "I!": "2/7",
    "ijl.|": "1/4",
    "_/\\": "2/5",
    "frtJ \"()[]{}": "1/3",
    "*-": "3/7",
    "?": "4/9",
    "EFLSTY$": "1/2",
    "#": "3/5",
    "~<=>^": "2/3",
    "DGHNOQ+": "3/4",
    "%&": "7/8",
    "mw": "5/6",
    "MW@": "1",
  }
  length = 0.
  for c in s:
    for pat, length_str in PATTERNS.items():
      if c in pat:
        length += Fraction(length_str)
        break
    else:
      if re.match('[0-9a-zｱ-ﾝ]', c):
        length += Fraction('1/2')
      elif re.match('[A-Z]', c):
        length += Fraction('3/5')
      # 厳重なチェックのためにやはりunicodedataは取り入れる。
      elif unicodedata.east_asian_width(c) in 'FW':
        length += 1.
      elif unicodedata.east_asian_width(c) in 'HNa':
        length += Fraction('1/2')
      else:   # ほかは間をとって3/4。
        length += Fraction('3/4')
  return float(length)

@dataclass
class NotionHtmlFile():
  title: str
  src: Path
  exp_q: Path
  exp_a: Path

class NotionHtmlEditer():
  """HTMLファイルの編集屋"""
  
  def __init__(self, nhfile: NotionHtmlFile):
    """ベースとなる体裁の整えられたHTMLをつくる"""
    self.nhfile = nhfile

    # BeautifulSoupへ読み込み
    with open(self.nhfile.src, encoding="utf-8") as f:
      soup = BeautifulSoup(f, 'html.parser')
    
    # ハイパーリンクタグ削除（タグの中身は残す）
    tags = soup.select("a")
    for tag in tags:
      tag.unwrap()

    # summaryの中身をなくす
    tags = soup.select("div.page-body div.indented details")  # > はつけられなかった。これはHTMLファイルじたいの問題。
    for tag in tags:
      del tag.attrs['open']
      for ctag in reversed(tag.contents):
        if ctag.name != 'summary':
          ctag.extract()
    
    # スタイルの差し替え
    linktag = soup.new_tag('link')
    linktag.attrs['rel'] = 'stylesheet'
    linktag.attrs['href'] = 'css/styles.css'
    soup.select('head style')[0].replace_with(linktag)

    # ヘッダとボディをわけて管理
    head = str(soup.head)
    body = str(soup.body)

    # タイトルを変更
    title = self.__replace_entities(self.nhfile.exp_a.stem)
    head = re.sub(r'<title>[^<>]*?</title>', f'<title>{title}</title>', head)

    # 改行文字を統一
    head = re.sub(r'(\r?\n)|(\r\n?)', '\n', head)
    body = re.sub(r'(\r?\n)|(\r\n?)', '\n', body)
    
    # 文中コードの不格好を解消
    body = body.replace('</code><code>', '')
    body = body.replace('</code><strong><code>', '<strong>')
    body = body.replace('</code><em><code>', '<em>')

    self.__basichead = head
    self.__basicbody = body
    self.basic_html = f'<html>{self.__basichead}{self.__basicbody}</html>'
  
  @property
  def problem_html(self):
    """虫食いになったHTML"""

    # 簡単のために短い変数に入れ直し
    body = self.__basicbody
    head = self.__basichead

    # タイトルを変更
    title = self.__replace_entities(self.nhfile.exp_q.stem)
    head = re.sub(r'<title>[^<>]*?</title>', f'<title>{title}</title>', head)

    # 解答欄をつくる
    summary_list = list(re.finditer(r"<summary>(.|\n)*?</summary>", body))
    WIDTHZ = 40   # 全角を1としたときのページ幅
    invalid_summs = LifoQueue()
    for summ in reversed(summary_list):
      if re.compile(r'(<[^<>]*?>)*[☆※](.|\n)*').fullmatch(summ.group(0)): continue
      if re.compile(r'<summary><del>(.|\n)*?</del></summary>').fullmatch(summ.group(0)): continue
      match_list = list(re.finditer(r"(<summary>|\n)(([^\n]*?)(　+|[　 ]{2,}))[^　 \n]", summ.group(0)))
      if len(match_list)==0: 
        invalid_summs.put(summ)
        continue
      ques_and_blank = re.sub(r"<[^<>]*?>", "", match_list[0].group(2))
      ques_and_blank_lenz = lenz(ques_and_blank)
      ans_lenz = WIDTHZ - int(ques_and_blank_lenz)
      for idx, m in enumerate(list(reversed(match_list))):
        repl = f'<mark class="highlight-yellow_background">{"　"*(ans_lenz-3)}\t\t\t\t\t\t</mark>'   # さすがに答え部分は全角文字3つ以上あるだろうという前提
        start = summ.start() + m.end() - 1
        # summary中に改行がある場合に、虫食い部分が共通の長さにならない現象を解消する
        # idxが最後じゃないなら（すなわち、改行から始まるなら）
        if idx < len(match_list)-1:
          # 既定の「問題+空白」分の長さ（ques_and_blank_lenz）になるか
          # 答えの文字が登場するまで、startを1ずつ先へ動かす。
          startroot = summ.start() + m.start() + 2
          start = startroot + 1
          while True:
            # タグを削除。左側の山ガッコのみの場合もあるので、注意している。
            temp_ques_and_blank = re.sub(r"<[^<>]*>", "", body[startroot:start])
            if lenz(temp_ques_and_blank) > ques_and_blank_lenz \
              or re.compile(r'.*(　+|[　 ]{2,})[^　 \n]').fullmatch(temp_ques_and_blank):
              start -= 1
              break
            start += 1
        stop = start + re.search(r'</summary>|\n', body[start:]).start()
        body = f'{body[:start]}{repl}{body[stop:] if stop<len(body) else ""}'
    
    for n in range(invalid_summs.qsize()):
      summ = invalid_summs.get()
      # logging.warning(f'{self.nhfile.title} にて不適切なトグル: {summ.group(0)}')

    return f'<html>{head}{body}</html>'

  def __replace_entities(self, text: str):
    text = text.replace('&', '&amp;')
    # 次の命令をしてしまうと、「\xc2\xa0問題」によってPDFダウンロード時の名前がCSVと相違することになる。
    # text = text.replace(' ', '&nbsp;')
    return text

def main():
  # 対象のHTMLファイルのパスのリスト
  SRCDIR = mymodule.APPDIR / 'html/src/'
  EXPDIR = mymodule.APPDIR / 'html/reformed/'
  nhfiles = []
  for title in mymodule.target_pages():
    src = SRCDIR / f'{title}.html'
    # もととなるHTMLファイルが実際に存在していなければ、ログに書いたうえでスキップ
    if not src.exists():
      # logging.info(f'Missed the file "{src.name}"')
      continue
    exp_q = EXPDIR / f'{title}{mymodule.POSTFIXES.q}.html'
    exp_a = EXPDIR / f'{title}{mymodule.POSTFIXES.a}.html'
    nhfiles.append(NotionHtmlFile(title, src, exp_q, exp_a))
  bar = tqdm(total=len(nhfiles)*2)
  bar.set_description('Exporting HTML')
  for nhfile in nhfiles:
    editer = NotionHtmlEditer(nhfile)
    # 問いとなるHTMLを作成
    with open(nhfile.exp_q, 'w', encoding='utf-8') as f:
      f.write(editer.problem_html)
    # logging.info(f'Exported {nhfile.exp_q.stem}')
    bar.update(1)
    # 答えとなるHTMLを作成
    with open(nhfile.exp_a, 'w', encoding='utf-8') as f:
      f.write(editer.basic_html)
    # logging.info(f'Exported {nhfile.exp_a.stem}')
    bar.update(1)

if __name__ == '__main__':
  main()
