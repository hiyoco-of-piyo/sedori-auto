#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedule
import time
import subprocess
import logging
import os
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class PriceUpdateScheduler:
    def __init__(self, excel_file_path=None):
        self.excel_file_path = excel_file_path or "/home/ubuntu/JANコード価格更新用.xlsx"
        self.update_script_path = "/home/ubuntu/update_prices.py"
    
    def run_price_update(self):
        """価格更新を実行する"""
        try:
            logging.info("定期価格更新を開始します")
            
            # ファイルの存在確認
            if not os.path.exists(self.excel_file_path):
                logging.error(f"Excelファイルが見つかりません: {self.excel_file_path}")
                return
            
            if not os.path.exists(self.update_script_path):
                logging.error(f"更新スクリプトが見つかりません: {self.update_script_path}")
                return
            
            # 価格更新スクリプトを実行
            cmd = ['python3', self.update_script_path, self.excel_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                logging.info("価格更新が正常に完了しました")
                logging.info(f"出力: {result.stdout}")
            else:
                logging.error(f"価格更新でエラーが発生しました: {result.stderr}")
                
        except Exception as e:
            logging.error(f"定期実行中にエラーが発生しました: {str(e)}")
    
    def start_scheduler(self):
        """スケジューラーを開始する"""
        logging.info("価格更新スケジューラーを開始します")
        logging.info(f"対象ファイル: {self.excel_file_path}")
        
        # スケジュール設定
        # 毎日午前9時に実行
        schedule.every().day.at("09:00").do(self.run_price_update)
        
        # 毎週月曜日の午前9時に実行（追加）
        schedule.every().monday.at("09:00").do(self.run_price_update)
        
        # テスト用: 毎分実行（コメントアウト）
        # schedule.every().minute.do(self.run_price_update)
        
        logging.info("スケジュール設定:")
        logging.info("- 毎日午前9時に価格更新")
        logging.info("- 毎週月曜日午前9時に価格更新")
        
        # 初回実行（オプション）
        logging.info("初回価格更新を実行します")
        self.run_price_update()
        
        # スケジューラーのメインループ
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
                
        except KeyboardInterrupt:
            logging.info("スケジューラーを停止します")
        except Exception as e:
            logging.error(f"スケジューラーでエラーが発生しました: {str(e)}")

def main():
    """メイン処理"""
    import sys
    
    # コマンドライン引数からExcelファイルパスを取得
    excel_file = None
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    # スケジューラーを作成・開始
    scheduler = PriceUpdateScheduler(excel_file)
    
    print("=" * 60)
    print("モバイル一番 価格更新スケジューラー")
    print("=" * 60)
    print(f"対象ファイル: {scheduler.excel_file_path}")
    print("スケジュール: 毎日午前9時、毎週月曜日午前9時")
    print("停止するには Ctrl+C を押してください")
    print("=" * 60)
    
    scheduler.start_scheduler()

if __name__ == "__main__":
    main()
