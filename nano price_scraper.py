#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import re

def search_and_get_price(driver, jan_code):
    """JANコードで検索して買取価格を取得"""
    try:
        driver.get('https://www.mobile-ichiban.com/Prod/1')
        time.sleep(5)
        
        # 検索窓を探す
        search_box = None
        
        try:
            search_box = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'JAN')]")
        except:
            pass
        
        if not search_box:
            try:
                search_boxes = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                for box in search_boxes:
                    if box.is_displayed() and box.is_enabled():
                        search_box = box
                        break
            except:
                pass
        
        if not search_box:
            return "検索窓なし"
        
        # 検索窓にJANコードを入力
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys(jan_code)
        time.sleep(1)
        
        # 検索実行
        try:
            search_button = None
            try:
                search_button = driver.find_element(By.XPATH, "//button[contains(text(), '検索')]")
            except:
                pass
            
            if not search_button:
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                except:
                    pass
            
            if search_button:
                search_button.click()
            else:
                search_box.send_keys(Keys.RETURN)
        except:
            search_box.send_keys(Keys.RETURN)
        
        # 検索結果待機
        time.sleep(8)
        
        # ページソース取得
        page_source = driver.page_source
        
        # 商品が見つからない場合
        if "見つかりません" in page_source or "該当する商品はありません" in page_source or "該当商品なし" in page_source:
            return "商品なし"
        
        # 価格を抽出
        price_pattern = r'(\d{1,3}(?:,\d{3})+)\s*円'
        all_matches = re.findall(price_pattern, page_source)
        
        if all_matches:
            valid_prices = []
            for match in all_matches:
                price_value = int(match.replace(',', ''))
                if 10000 <= price_value <= 5000000:
                    valid_prices.append(price_value)
            
            if valid_prices:
                max_price = max(valid_prices)
                return f"¥{max_price:,}"
        
        # パターン2: ¥マーク
        price_pattern2 = r'¥\s*(\d{1,3}(?:,\d{3})+)'
        matches2 = re.findall(price_pattern2, page_source)
        if matches2:
            valid_prices2 = []
            for match in matches2:
                price_value = int(match.replace(',', ''))
                if 10000 <= price_value <= 5000000:
                    valid_prices2.append(price_value)
            
            if valid_prices2:
                max_price = max(valid_prices2)
                return f"¥{max_price:,}"
        
        return "価格なし"
        
    except Exception as e:
        print(f"  エラー: {str(e)}")
        return "取得エラー"

def update_spreadsheet():
    """スプレッドシートを更新"""
    driver = None
    
    try:
        print("\nGoogle Sheets APIに接続中...")
        
        # Google Sheets APIの認証
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            'credentials.json', scope)
        gc = gspread.authorize(credentials)
        
        print("✓ 認証成功！")
        
        # スプレッドシートを開く
        spreadsheet_key = '1XHe4CrHACGnUeJx8nEm-JtI2M-G92FhbrU1H5YYUgBY'
        workbook = gc.open_by_key(spreadsheet_key)
        worksheet = workbook.worksheet('モバイル一番')
        
        print(f"✓ シート「モバイル一番」を開きました\n")
        
        # Chromeブラウザの設定
        print("ブラウザを起動中...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # バックグラウンド実行
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ ブラウザ起動完了\n")
        
        print("="*60)
        print("全件処理を開始します")
        print("="*60 + "\n")
        
        # すべてのデータを取得
        all_values = worksheet.get_all_values()
        
        # JANコードがある行数をカウント
        total_jan_count = 0
        for row_index in range(1, len(all_values)):
            row_data = all_values[row_index]
            if len(row_data) > 1:
                jan_code = row_data[1].strip()
                if jan_code and jan_code != "JANコード" and jan_code.isdigit():
                    total_jan_count += 1
        
        print(f"処理対象: {total_jan_count}件のJANコード")
        print(f"予想処理時間: 約{total_jan_count * 13 / 60:.0f}分")
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 現在の日時
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 処理カウンター
        processed_count = 0
        success_count = 0
        error_count = 0
        
        # ヘッダー行をスキップして処理
        for row_index in range(1, len(all_values)):
            row_number = row_index + 1
            row_data = all_values[row_index]
            
            # B列のJANコードを取得
            if len(row_data) > 1:
                jan_code = row_data[1].strip()
            else:
                jan_code = ""
            
            # JANコードのチェック
            if not jan_code or jan_code == "JANコード" or not jan_code.isdigit():
                continue
            
            processed_count += 1
            
            # 進捗表示
            progress = (processed_count / total_jan_count) * 100
            print(f"[{processed_count}/{total_jan_count}] ({progress:.1f}%) 行{row_number} JANコード: {jan_code}", end=" ")
            
            # 買取価格を取得
            price = search_and_get_price(driver, jan_code)
            print(f"→ {price}")
            
            # 結果カウント
            if price.startswith("¥"):
                success_count += 1
            elif "エラー" in price:
                error_count += 1
            
            # スプレッドシートに書き込み
            try:
                worksheet.update_cell(row_number, 3, price)
                worksheet.update_cell(row_number, 4, current_time)
            except Exception as e:
                print(f"  ⚠ 書き込みエラー: {str(e)}")
                time.sleep(60)  # API制限の場合は1分待機
                worksheet.update_cell(row_number, 3, price)
                worksheet.update_cell(row_number, 4, current_time)
            
            # 待機
            time.sleep(3)
            
            # 100件ごとに進捗サマリー表示
            if processed_count % 100 == 0:
                print(f"\n--- 中間報告 ({processed_count}件処理完了) ---")
                print(f"成功: {success_count}件 / エラー: {error_count}件")
                print(f"成功率: {(success_count/processed_count)*100:.1f}%\n")
        
        print(f"\n{'='*60}")
        print(f"全件処理完了！")
        print(f"{'='*60}")
        print(f"処理件数: {processed_count}件")
        print(f"成功: {success_count}件")
        print(f"エラー: {error_count}件")
        print(f"成功率: {(success_count/processed_count)*100:.1f}%")
        print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\nエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print("=" * 60)
    print("買取価格抽出プログラム（全件処理版）")
    print("=" * 60)
    update_spreadsheet()
    print("\n" + "=" * 60)
    print("プログラム終了")
    print("=" * 60)
