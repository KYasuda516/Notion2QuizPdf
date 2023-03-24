from mylib.io import yes_no_input
from multiprocessing import freeze_support
import notion2html
import reform_html
import html2pdf
import combine_pdfs

if __name__ == '__main__':
  # 実行の確認
  if not yes_no_input("I'll execute Step 1 to 4 all at once. Ready?"):
    exit()
  
  # マルチプロセスのバグ回避
  freeze_support()

  notion2html.main()
  reform_html.main()
  html2pdf.main()
  combine_pdfs.main()
  notion2html.NotionHtmlDownloader.recover_chrome()
