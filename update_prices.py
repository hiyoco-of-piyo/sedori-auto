#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging
from mobile_ichiban_scraper import update_spreadsheet_with_jan_codes

def main():
    """価格更新のメイン処理"""
    
    # デフォルトのExcelファイルパス
    default_excel_file = "/home/ubuntu/JANコード価格更新用.xlsx"
    
    # コマンドライン引数からファイルパスを取得
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = default_excel_file
    
    # ファイルの存在確認
    if not os.path.exists(excel_file):
        print(f"エラー: ファイル '{excel_file}' が見つかりません")
        print(f"使用方法: python3 {sys.argv[0]} [Excelファイルパス]")
        sys.exit(1)
    
    print(f"価格更新を開始します: {excel_file}")
    print("=" * 50)
    
    try:
        # スプレッドシートの価格を更新
        update_spreadsheet_with_jan_codes(
            excel_file_path=excel_file,
            jan_column='H',    # JANコード列
            price_column='G',  # 買取価格列
            date_column='I'    # 更新日列
        )
        
        print("=" * 50)
        print("価格更新が完了しました！")
        print(f"更新されたファイル: {excel_file}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        logging.error(f"価格更新エラー: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
