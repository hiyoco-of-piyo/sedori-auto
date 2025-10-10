#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
森森買取 PC用システム
- Windows/Mac対応
- 素人でも簡単設定
- 完全自動化
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
import re
from urllib.parse import quote
import platform

# Google Sheets API関連
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("❌ Google Sheets APIライブラリがインストールされていません")
    print("以下のコマンドを実行してください:")
    print("pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests")

# PC用パス設定
def get_system_paths():
    """OS別のパス設定を取得"""
    system = platform.system()
    home_dir = os.path.expanduser("~")
    
    if system == "Windows":
        work_dir = os.path.join(home_dir, "Documents", "morimori_system")
    else:  # Mac/Linux
        work_dir = os.path.join(home_dir, "morimori_system")
    
    # ディレクトリ作成
    os.makedirs(work_dir, exist_ok=True)
    
    return {
        'work_dir': work_dir,
        'log_file': os.path.join(work_dir, 'morimori.log'),
        'config_file': os.path.join(work_dir, 'config.json'),
        'progress_file': os.path.join(work_dir, 'progress.json'),
        'service_account_file': os.path.join(work_dir, 'service_account.json')
    }

# パス設定
PATHS = get_system_paths()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PATHS['log_file'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MorimoriPCSystem:
    """森森買取 PC用システム"""
    
    def __init__(self):
        self.work_dir = PATHS['work_dir']
        self.config = self.load_config()
        self.base_url = "https://www.morimori-kaitori.jp"
        self.spreadsheet_id = self.config.get('spreadsheet_id', '1XHe4CrHACGnUeJx8nEm-JtI2M-G92FhbrU1H5YYUgBY')
        self.sheet_name = self.config.get('sheet_name', '森森買取')
        
        # 処理設定
        self.batch_size = self.config.get('batch_size', 20)
        self.delay_ms = self.config.get('delay_ms', 1500)
        self.max_execution_time = self.config.get('max_execution_time', 300)  # 5分
        
        # セッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Google Sheets API初期化
        self.sheets_service = None
        if GOOGLE_SHEETS_AVAILABLE:
            self.init_google_sheets()
        
        # 進捗管理
        self.load_progress()
    
    def load_config(self) -> Dict:
        """設定ファイルを読み込み"""
        default_config = {
            'spreadsheet_id': '1XHe4CrHACGnUeJx8nEm-JtI2M-G92FhbrU1H5YYUgBY',
            'sheet_name': '森森買取',
            'batch_size': 20,
            'delay_ms': 1500,
            'max_execution_time': 300
        }
        
        if os.path.exists(PATHS['config_file']):
            try:
                with open(PATHS['config_file'], 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"設定ファイル読み込みエラー: {e}")
        else:
            # 初回実行時に設定ファイルを作成
            self.save_config(default_config)
        
        return default_config
    
    def save_config(self, config: Dict):
        """設定ファイルを保存"""
        try:
            with open(PATHS['config_file'], 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {e}")
    
    def init_google_sheets(self):
        """Google Sheets API初期化"""
        try:
            if not os.path.exists(PATHS['service_account_file']):
                logger.error("❌ Google Sheets認証ファイルが見つかりません")
                logger.error(f"以下の場所に service_account.json を配置してください:")
                logger.error(f"📁 {PATHS['service_account_file']}")
                return
            
            credentials = Credentials.from_service_account_file(
                PATHS['service_account_file'],
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            logger.info("✅ Google Sheets API初期化完了")
            
        except Exception as e:
            logger.error(f"❌ Google Sheets API初期化エラー: {e}")
            self.sheets_service = None
    
    def load_progress(self):
        """進捗情報を読み込み"""
        self.progress = {
            'current_index': 0,
            'total_count': 0,
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'start_time': None,
            'last_update': None,
            'is_running': False,
            'completion_rate': 0.0
        }
        
        if os.path.exists(PATHS['progress_file']):
            try:
                with open(PATHS['progress_file'], 'r', encoding='utf-8') as f:
                    saved_progress = json.load(f)
                    self.progress.update(saved_progress)
            except Exception as e:
                logger.warning(f"進捗ファイル読み込みエラー: {e}")
    
    def save_progress(self):
        """進捗情報を保存"""
        try:
            self.progress['last_update'] = datetime.now().isoformat()
            with open(PATHS['progress_file'], 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"進捗ファイル保存エラー: {e}")
    
    def get_sheet_data(self, range_name: str) -> List[List]:
        """スプレッドシートからデータを取得"""
        if not self.sheets_service:
            logger.error("❌ Google Sheets APIが初期化されていません")
            return []
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!{range_name}"
            ).execute()
            
            return result.get('values', [])
            
        except Exception as e:
            logger.error(f"❌ スプレッドシート読み込みエラー: {e}")
            return []
    
    def update_sheet_data(self, range_name: str, values: List[List]):
        """スプレッドシートにデータを更新"""
        if not self.sheets_service:
            logger.error("❌ Google Sheets APIが初期化されていません")
            return False
        
        try:
            body = {
                'values': values
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!{range_name}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"✅ スプレッドシート更新完了: {result.get('updatedCells', 0)} セル")
            return True
            
        except Exception as e:
            logger.error(f"❌ スプレッドシート更新エラー: {e}")
            return False
    
    def search_by_jan_code(self, jan_code: str) -> Optional[Dict]:
        """JANコードで商品を検索"""
        search_url = f"{self.base_url}/search?sk={jan_code}"
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                response = self.session.get(search_url, timeout=20)
                
                if response.status_code == 200:
                    return self.parse_search_results(response.text, jan_code)
                elif response.status_code == 429:
                    wait_time = (2 ** retry) * 2
                    logger.warning(f"⚠️ レート制限検出、{wait_time}秒待機... ({retry + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code}: {search_url}")
                    return None
                    
            except Exception as error:
                if retry == max_retries - 1:
                    logger.error(f"❌ 検索エラー ({jan_code}): {error}")
                    return None
                logger.warning(f"⚠️ リトライ {retry + 1}/{max_retries}: {error}")
                time.sleep(2 * (retry + 1))
        
        return None
    
    def parse_search_results(self, html: str, jan_code: str) -> Optional[Dict]:
        """HTMLから価格情報を抽出"""
        try:
            patterns = [
                r'通常買取価格:\s*\n?\s*([0-9,]+)円',
                r'通常買取価格[^(]*?([0-9,]+)円',
                r'買取価格[：:]\s*([0-9,]+)円',
                r'価格[：:]\s*([0-9,]+)円'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match and '上限' not in match.group(0) and '～' not in match.group(0):
                    price = int(match.group(1).replace(',', ''))
                    if price > 0:
                        return {'new_price': price}
            
            return None
            
        except Exception as error:
            logger.error(f"❌ HTML解析エラー ({jan_code}): {error}")
            return None
    
    def process_single_item(self, item: Dict) -> Dict:
        """単一商品の処理"""
        try:
            price_data = self.search_by_jan_code(item['jan_code'])
            
            result = {
                'row_index': item['row_index'],
                'jan_code': item['jan_code'],
                'price': None,
                'status': 'データなし',
                'updated_at': datetime.now(),
                'detail_url': f"{self.base_url}/search?sk={item['jan_code']}"
            }
            
            if price_data and price_data.get('new_price'):
                result['price'] = price_data['new_price']
                result['status'] = '取得成功'
                logger.info(f"✅ {item['jan_code']}: ¥{result['price']:,}")
            else:
                logger.info(f"⚪ {item['jan_code']}: データなし")
            
            return result
            
        except Exception as error:
            logger.error(f"❌ 商品処理エラー ({item['jan_code']}): {error}")
            return {
                'row_index': item['row_index'],
                'jan_code': item['jan_code'],
                'price': None,
                'status': f'エラー: {error}',
                'updated_at': datetime.now(),
                'detail_url': f"{self.base_url}/search?sk={item['jan_code']}"
            }
    
    def run_update(self, max_items: int = None):
        """更新実行"""
        try:
            logger.info("🚀 森森買取 価格更新開始")
            
            # 進捗初期化
            self.progress.update({
                'current_index': 0,
                'processed_count': 0,
                'success_count': 0,
                'error_count': 0,
                'start_time': datetime.now().isoformat(),
                'is_running': True
            })
            
            # データ取得
            logger.info("📋 スプレッドシートからデータを取得中...")
            data = self.get_sheet_data("B:E")
            
            if not data or len(data) < 2:
                logger.error("❌ スプレッドシートにデータがありません")
                return False
            
            # 有効なJANコードをフィルタリング
            valid_items = []
            for i, row in enumerate(data[1:], 2):
                if len(row) > 0 and row[0] and len(str(row[0])) >= 10:
                    valid_items.append({
                        'row_index': i,
                        'jan_code': str(row[0])
                    })
            
            # 処理件数制限
            if max_items:
                valid_items = valid_items[:max_items]
            
            self.progress['total_count'] = len(valid_items)
            logger.info(f"📊 処理対象: {len(valid_items)}件")
            
            if len(valid_items) == 0:
                logger.warning("⚠️ 処理対象のJANコードがありません")
                return False
            
            # バッチ処理実行
            start_time = time.time()
            current_index = 0
            
            while current_index < len(valid_items):
                # 実行時間チェック
                elapsed = time.time() - start_time
                if elapsed > self.max_execution_time:
                    logger.warning(f"⚠️ 実行時間制限により中断: {current_index}/{len(valid_items)}")
                    break
                
                batch_end = min(current_index + self.batch_size, len(valid_items))
                batch_items = valid_items[current_index:batch_end]
                
                logger.info(f"📦 バッチ {current_index + 1}-{batch_end}/{len(valid_items)} 処理中...")
                
                # バッチ処理
                results = []
                for i, item in enumerate(batch_items):
                    remaining_time = self.max_execution_time - (time.time() - start_time)
                    logger.info(f"[{i + 1}/{len(batch_items)}] 行{item['row_index']}: {item['jan_code']} (残り{remaining_time:.1f}秒)")
                    
                    result = self.process_single_item(item)
                    results.append(result)
                    
                    # 進捗更新
                    self.progress['processed_count'] += 1
                    if result['price']:
                        self.progress['success_count'] += 1
                    else:
                        self.progress['error_count'] += 1
                    
                    # 処理間隔
                    if i < len(batch_items) - 1:
                        time.sleep(self.delay_ms / 1000.0)
                
                # スプレッドシート更新
                if results:
                    logger.info("📝 スプレッドシート更新中...")
                    for result in results:
                        row = result['row_index']
                        price_value = f"¥{result['price']:,}" if result['price'] else '-'
                        date_value = result['updated_at'].strftime('%Y/%m/%d %H:%M:%S')
                        link_formula = f'=HYPERLINK("{result["detail_url"]}", "詳細を見る")'
                        
                        range_name = f"C{row}:E{row}"
                        values = [[price_value, date_value, link_formula]]
                        self.update_sheet_data(range_name, values)
                        time.sleep(0.1)
                
                # 進捗更新
                self.progress['current_index'] = batch_end
                self.progress['completion_rate'] = (batch_end / len(valid_items)) * 100
                self.save_progress()
                
                current_index = batch_end
                
                # バッチ間の休憩
                if current_index < len(valid_items):
                    logger.info("⏳ バッチ間休憩中...")
                    time.sleep(2)
            
            # 完了処理
            self.progress.update({
                'is_running': False,
                'completion_rate': 100.0,
                'end_time': datetime.now().isoformat()
            })
            self.save_progress()
            
            logger.info("🎉 価格更新完了！")
            logger.info(f"📊 処理結果: 成功{self.progress['success_count']}件, エラー{self.progress['error_count']}件")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新エラー: {e}")
            self.progress['is_running'] = False
            self.save_progress()
            return False
    
    def get_status(self) -> Dict:
        """現在のステータスを取得"""
        return {
            'is_running': self.progress['is_running'],
            'completion_rate': self.progress['completion_rate'],
            'processed_count': self.progress['processed_count'],
            'total_count': self.progress['total_count'],
            'success_count': self.progress['success_count'],
            'error_count': self.progress['error_count'],
            'start_time': self.progress.get('start_time'),
            'last_update': self.progress.get('last_update'),
            'work_dir': self.work_dir
        }
    
    def show_status(self):
        """ステータス表示"""
        status = self.get_status()
        
        print("=" * 60)
        print("🔄 森森買取システム ステータス")
        print("=" * 60)
        
        if status['is_running']:
            print("⚡ 実行状態: 🟡 実行中")
        else:
            print("⚡ 実行状態: 🟢 待機中")
        
        print(f"📊 進捗率: {status['completion_rate']:.1f}%")
        print(f"📈 処理済み: {status['processed_count']}/{status['total_count']}件")
        print(f"✅ 成功: {status['success_count']}件")
        print(f"❌ エラー: {status['error_count']}件")
        print(f"📁 作業フォルダ: {status['work_dir']}")
        
        if status.get('start_time'):
            start_time = datetime.fromisoformat(status['start_time'])
            print(f"🕐 開始時刻: {start_time.strftime('%Y/%m/%d %H:%M:%S')}")
        
        print("=" * 60)
    
    def test_connection(self):
        """接続テスト"""
        print("🔧 接続テストを実行します...")
        
        # Google Sheets API テスト
        if self.sheets_service:
            print("✅ Google Sheets API: 接続OK")
        else:
            print("❌ Google Sheets API: 接続NG")
            print(f"📁 認証ファイルの場所: {PATHS['service_account_file']}")
            return False
        
        # 価格抽出テスト
        test_jan = "4549995649284"
        print(f"🧪 テスト検索: {test_jan}")
        result = self.search_by_jan_code(test_jan)
        if result:
            print(f"✅ テスト成功: ¥{result['new_price']:,}")
            return True
        else:
            print("❌ テスト失敗")
            return False

def show_setup_guide():
    """セットアップガイド表示"""
    print("=" * 60)
    print("🚀 森森買取システム セットアップガイド")
    print("=" * 60)
    print()
    print("📋 必要な準備:")
    print("1. Pythonライブラリのインストール")
    print("2. Google Sheets認証ファイルの配置")
    print()
    print("🔧 手順1: ライブラリインストール")
    print("以下のコマンドを実行してください:")
    print("pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests")
    print()
    print("🔑 手順2: 認証ファイル配置")
    print(f"service_account.json を以下の場所に配置してください:")
    print(f"📁 {PATHS['service_account_file']}")
    print()
    print("✅ 準備完了後、以下のコマンドでテストしてください:")
    print("python3 morimori_pc_system.py --test")
    print("=" * 60)

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='森森買取 PC用システム')
    parser.add_argument('--run', action='store_true', help='価格更新実行')
    parser.add_argument('--status', action='store_true', help='ステータス確認')
    parser.add_argument('--test', action='store_true', help='接続テスト')
    parser.add_argument('--setup', action='store_true', help='セットアップガイド表示')
    parser.add_argument('--max-items', type=int, help='最大処理件数（テスト用）')
    
    args = parser.parse_args()
    
    if args.setup:
        show_setup_guide()
        return
    
    # ライブラリチェック
    if not GOOGLE_SHEETS_AVAILABLE:
        print()
        show_setup_guide()
        return
    
    # システム初期化
    system = MorimoriPCSystem()
    
    if args.test:
        success = system.test_connection()
        if success:
            print("🎉 接続テスト成功！システムの準備ができました。")
        else:
            print("❌ 接続テストに失敗しました。セットアップを確認してください。")
    
    elif args.status:
        system.show_status()
    
    elif args.run:
        print("🚀 森森買取 価格更新を開始します...")
        success = system.run_update(max_items=args.max_items)
        if success:
            print("✅ 価格更新が正常に完了しました")
            system.show_status()
        else:
            print("❌ 価格更新でエラーが発生しました")
    
    else:
        # デフォルト: ステータス表示
        system.show_status()
        print()
        print("🎮 使用方法:")
        print("python3 morimori_pc_system.py --setup    # セットアップガイド")
        print("python3 morimori_pc_system.py --test     # 接続テスト")
        print("python3 morimori_pc_system.py --run      # 価格更新実行")
        print("python3 morimori_pc_system.py --status   # ステータス確認")

if __name__ == "__main__":
    main()
