#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
モバイル一番 価格更新システム 設定ファイル
"""

import os

# ファイルパス設定
BASE_DIR = "/home/ubuntu"
EXCEL_FILE_PATH = os.path.join(BASE_DIR, "JANコード価格更新用.xlsx")
LOG_FILE_PATH = os.path.join(BASE_DIR, "mobile_ichiban_scraper.log")
SCHEDULER_LOG_PATH = os.path.join(BASE_DIR, "scheduler.log")

# スプレッドシート列設定
SPREADSHEET_COLUMNS = {
    'jan_code': 'H',      # JANコード列
    'price': 'G',         # 買取価格列
    'update_date': 'I'    # 更新日列
}

# スクレイピング設定
SCRAPING_CONFIG = {
    'base_url': 'https://www.mobile-ichiban.com',
    'request_delay': 2,   # リクエスト間隔（秒）
    'timeout': 30,        # タイムアウト（秒）
    'retry_count': 3,     # リトライ回数
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# スケジュール設定
SCHEDULE_CONFIG = {
    'daily_time': '09:00',        # 毎日の実行時刻
    'weekly_day': 'monday',       # 週次実行の曜日
    'weekly_time': '09:00',       # 週次実行の時刻
    'check_interval': 60          # スケジュールチェック間隔（秒）
}

# ログ設定
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'encoding': 'utf-8'
}

# 商品検索設定
SEARCH_CONFIG = {
    'price_patterns': [
        r'(\d{1,3}(?:,\d{3})*)\s*円',
        r'¥\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*yen'
    ],
    'product_keywords': [
        'iPhone', 'iPad', 'Google', 'Galaxy', 'Pixel', 'Redmi', 
        'Xperia', 'AQUOS', 'arrows', 'OPPO', 'Xiaomi'
    ],
    'condition_keywords': [
        '新品', '中古', '未開封', '開封', 'A級', 'B級', 'C級'
    ]
}

def get_config():
    """設定情報を取得する"""
    return {
        'files': {
            'excel_file': EXCEL_FILE_PATH,
            'log_file': LOG_FILE_PATH,
            'scheduler_log': SCHEDULER_LOG_PATH
        },
        'columns': SPREADSHEET_COLUMNS,
        'scraping': SCRAPING_CONFIG,
        'schedule': SCHEDULE_CONFIG,
        'logging': LOGGING_CONFIG,
        'search': SEARCH_CONFIG
    }

def validate_config():
    """設定の妥当性をチェックする"""
    errors = []
    
    # ディレクトリの存在確認
    if not os.path.exists(BASE_DIR):
        errors.append(f"ベースディレクトリが存在しません: {BASE_DIR}")
    
    # 必要なファイルの確認
    required_files = [
        "/home/ubuntu/mobile_ichiban_scraper.py",
        "/home/ubuntu/update_prices.py",
        "/home/ubuntu/scheduler.py"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            errors.append(f"必要なファイルが存在しません: {file_path}")
    
    return errors

if __name__ == "__main__":
    # 設定確認
    print("モバイル一番 価格更新システム 設定確認")
    print("=" * 50)
    
    config = get_config()
    
    print("ファイル設定:")
    for key, value in config['files'].items():
        print(f"  {key}: {value}")
    
    print("\n列設定:")
    for key, value in config['columns'].items():
        print(f"  {key}: {value}列")
    
    print("\nスケジュール設定:")
    for key, value in config['schedule'].items():
        print(f"  {key}: {value}")
    
    print("\n設定妥当性チェック:")
    errors = validate_config()
    if errors:
        print("エラーが見つかりました:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("設定に問題はありません")
