#!/usr/bin/env python3
"""
森森買取サイトから買取価格を抽出してGoogle Spreadsheetsに記録するスクリプト（改善版）
"""

import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import re

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('morimori_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


class MorimoriPriceScraperV2:
    """森森買取サイトの価格抽出クラス（改善版）"""
    
    def __init__(self, credentials_path, spreadsheet_url, sheet_name):
        """初期化"""
        self.spreadsheet_url = spreadsheet_url
        self.sheet_name = sheet_name
        self.base_url = "https://www.morimori-kaitori.jp"
        self.search_url = f"{self.base_url}/search"
        
        # Google Sheets認証
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        self.client = gspread.authorize(creds)
        
        # スプレッドシートを開く
        self.spreadsheet = self.client.open_by_url(spreadsheet_url)
        self.worksheet = self.spreadsheet.worksheet(sheet_name)
        
        logging.info(f"スプレッドシート '{sheet_name}' に接続しました")
    
    def get_jan_codes(self):
        """B列からJANコードを取得"""
        jan_codes_column = self.worksheet.col_values(2)
        
        jan_codes = []
        for i, jan_code in enumerate(jan_codes_column[1:], start=2):
            if jan_code and jan_code.strip():
                jan_codes.append((i, jan_code.strip()))
        
        logging.info(f"{len(jan_codes)}件のJANコードを取得しました")
        return jan_codes
    
    def make_request(self, url, retries=3):
        """HTTPリクエストを実行（リトライ付き）"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                logging.warning(f"リクエスト失敗 (試行 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logging.error(f"リクエスト失敗: {url}")
                    return None
    
    def extract_price_from_text(self, text):
        """テキストから価格を抽出"""
        match = re.search(r'([\d,]+)\s*円', text)
        if match:
            return match.group(1).replace(',', '')
        
        match = re.search(r'¥\s*([\d,]+)', text)
        if match:
            return match.group(1).replace(',', '')
        
        match = re.search(r'\b(\d{3,})\b', text)
        if match:
            return match.group(1)
        
        return None
    
    def find_product_links(self, soup):
        """検索結果ページから商品ページのリンクを抽出"""
        product_links = []
        
        for link in soup.find_all('a', href=re.compile(r'/product/\d+')):
            href = link.get('href')
            if href:
                full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                if full_url not in product_links:
                    product_links.append(full_url)
        
        return product_links
    
    def extract_price_from_page(self, soup):
        """ページから価格を抽出（複数のパターンを試行）"""
        selectors = [
            {'class_': re.compile(r'price', re.I)},
            {'class_': re.compile(r'amount', re.I)},
            {'class_': re.compile(r'kaitori', re.I)},
            {'id': re.compile(r'price', re.I)},
        ]
        
        for selector in selectors:
            elements = soup.find_all(['div', 'span', 'p', 'strong'], **selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                price = self.extract_price_from_text(text)
                if price and len(price) >= 3:
                    return price
        
        all_text = soup.get_text()
        match = re.search(r'買取(?:価格|金額)[:\s]*([¥\d,]+)', all_text)
        if match:
            price = self.extract_price_from_text(match.group(1))
            if price:
                return price
        
        return None
    
    def scrape_price(self, jan_code):
        """指定したJANコードの買取価格をスクレイピング"""
        search_url = f"{self.search_url}?sk={jan_code}"
        logging.info(f"検索URL: {search_url}")
        
        # 検索結果ページを取得
        soup = self.make_request(search_url)
        if not soup:
            return None
        
        # 検索結果ページから直接価格を探す
        price = self.extract_price_from_page(soup)
        if price:
            return {
                'price': price,
                'url': search_url,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 商品ページのリンクを探す
        product_links = self.find_product_links(soup)
        if not product_links:
            logging.warning(f"JANコード {jan_code}: 商品ページが見つかりませんでした")
            return None
        
        # 最初の商品ページから価格を取得
        logging.info(f"商品ページを確認: {product_links[0]}")
        product_soup = self.make_request(product_links[0])
        if not product_soup:
            return None
        
        price = self.extract_price_from_page(product_soup)
        if price:
            return {
                'price': price,
                'url': product_links[0],
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        logging.warning(f"JANコード {jan_code}: 価格が見つかりませんでした")
        return None
    
    def update_spreadsheet(self, row, price, update_time, url):
        """スプレッドシートを更新"""
        try:
            # バッチ更新で効率化
            cell_list = [
                gspread.Cell(row, 3, price),
                gspread.Cell(row, 4, update_time),
                gspread.Cell(row, 5, url)
            ]
            self.worksheet.update_cells(cell_list)
            logging.info(f"行 {row} を更新: 価格={price}")
        except Exception as e:
            logging.error(f"行 {row} の更新エラー: {e}")
    
    def run(self):
        """メイン処理を実行"""
        logging.info("=" * 70)
        logging.info("価格抽出処理を開始")
        logging.info("=" * 70)
        
        jan_codes = self.get_jan_codes()
        if not jan_codes:
            logging.warning("JANコードが見つかりません")
            return
        
        success_count = 0
        fail_count = 0
        
        for row, jan_code in jan_codes:
            logging.info(f"\n処理中: 行{row} - JANコード {jan_code}")
            
            result = self.scrape_price(jan_code)
            
            if result:
                self.update_spreadsheet(
                    row,
                    result['price'],
                    result['update_time'],
                    result['url']
                )
                success_count += 1
            else:
                # 取得失敗時もURLと日時は記録
                self.update_spreadsheet(
                    row,
                    "取得失敗",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    f"{self.search_url}?sk={jan_code}"
                )
                fail_count += 1
            
            # サーバーへの負荷を避けるため待機
            time.sleep(3)
        
        logging.info("=" * 70)
        logging.info(f"処理完了: 成功={success_count}, 失敗={fail_count}")
        logging.info("=" * 70)


def main():
    """メイン関数"""
    CREDENTIALS_PATH = "morimori-bot-475909-f42c08f4758f.json"
    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1XHe4CrHACGnUeJx8nEm-JtI2M-G92FhbrU1H5YYUgBY/edit?gid=830970368#gid=830970368"
    SHEET_NAME = "森森買取"
    
    try:
        scraper = MorimoriPriceScraperV2(CREDENTIALS_PATH, SPREADSHEET_URL, SHEET_NAME)
        scraper.run()
    except Exception as e:
        logging.error(f"実行エラー: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
