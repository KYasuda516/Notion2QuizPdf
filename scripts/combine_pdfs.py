from mylib import logging
import mymodule
# !conda install -c conda-forge pypdf2
import PyPDF2
from tqdm import tqdm
from pathlib import Path
from dataclasses import dataclass
from multiprocessing import Pool

@dataclass
class NotionPdfFile():
  title: str
  src_q: Path
  src_a: Path
  exp: Path

def pdf2to1(npfile: NotionPdfFile):
  """問いと答えのPDFについて、2ページを見開き1ページに

  ┌----------------------------┐ --JOGE_YOHAKU
  | ┌---------┐    ┌---------┐ | --20
  | |    |    |    |         | |
  | |    |    |    |         | |
  | |<---|--->|    |         | |
  | | q  |    |    | a       | | 
  | └---------┘    └---------┘ |
  └----------------------------┘
                             | |
                        SAYU_YOHAKU 20/√2
  バカデカページに貼り付けてからA4へと縮小する。
  """
  ques_reader = PyPDF2.PdfFileReader(npfile.src_q.as_posix(), strict=False)
  ans_reader = PyPDF2.PdfFileReader(npfile.src_a.as_posix(), strict=False)
  out_writer = PyPDF2.PdfFileWriter()
  A4YOKO_WITDH = 840.95996
  JOGE_YOHAKU = 20.
  SAYU_YOHAKU = JOGE_YOHAKU / 2**(1/2)  # ルート2で割る
  for n in range(0, ques_reader.getNumPages()):
    # 繋ぎ合わせるページ（page1：左側、page2：右側）
    page1 = ques_reader.getPage(n)
    page2 = ans_reader.getPage(n)

    # 見開きにしたページサイズ
    total_width = float(page1.mediaBox.getUpperRight_x()) + float(page2.mediaBox.getUpperRight_x()) + SAYU_YOHAKU*4
    total_height = float(max([page1.mediaBox.getUpperRight_y(), page1.mediaBox.getUpperRight_y()])) + JOGE_YOHAKU*2
    # ページを貼り付ける空白ページ
    page = PyPDF2.PageObject.createBlankPage(width=total_width, height=total_height)
    # 左側のページを位置を指定して貼り付け
    page.mergeTranslatedPage(page1, tx=SAYU_YOHAKU, ty=JOGE_YOHAKU)
    page.mergeTranslatedPage(page2, tx=float(page1.mediaBox.getUpperRight_x())+SAYU_YOHAKU*3, ty=JOGE_YOHAKU)
    # 見開きにしたページを出力用オブジェクトに追加
    page_scale = A4YOKO_WITDH / total_width
    page.scale(page_scale, page_scale)
    out_writer.addPage(page)

  # ファイルに出力
  with open(npfile.exp.as_posix(), mode="wb") as f:
    out_writer.write(f)
  logging.info(f'Export {npfile.title}')

def main():
  # 対象の記事のNotionPdfFileのリストを取得
  SRCDIR = mymodule.APPDIR / 'pdf/src/'
  EXPDIR = mymodule.APPDIR / 'pdf/combined/'
  npfiles = []
  for title in mymodule.target_pages():
    src_q = SRCDIR / f'{title}{mymodule.POSTFIXES.q}.pdf'
    src_a = SRCDIR / f'{title}{mymodule.POSTFIXES.a}.pdf'
    # もととなるPDFが実際に存在していなければ、ログに書いたうえでスキップ
    if not all([src_q.exists(), src_a.exists()]):
      logging.info(f'"{src_q.name}" or "{src_a.name}" do not exist.')
      continue
    exp = EXPDIR / f'{title}.pdf'
    # リストに追加
    npfiles.append(NotionPdfFile(title, src_q, src_a, exp))

  # 2枚を見開き1ページに
  bar = tqdm(total=len(npfiles))
  bar.set_description('Exporting PDF')
  with Pool(processes=6) as pool:
    results = pool.map(pdf2to1, npfiles)
  for result in results:
    bar.update(1)

if __name__ == '__main__':
  main()