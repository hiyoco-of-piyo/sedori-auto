#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
モバイル一番 価格更新システム セットアップスクリプト
"""

import os
import subprocess
import sys

def install_requirements():
    """必要なライブラリをインストールする"""
    print("必要なライブラリをインストール中...")
    
    requirements = [
        'requests',
        'beautifulsoup4',
        'openpyxl',
        'pandas',
        'schedule'
    ]
    
    for package in requirements:
        try:
            print(f"インストール中: {package}")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except subprocess.CalledProcessError as e:
            print(f"エラー: {package} のインストールに失敗しました: {e}")
            return False
    
    print("ライブラリのインストールが完了しました")
    return True

def create_sample_spreadsheet():
    """サンプルスプレッドシートを作成する"""
    print("サンプルスプレッドシートを作成中...")
    
    try:
        subprocess.check_call([sys.executable, 'create_jan_sample_sheet.py'])
        print("サンプルスプレッドシートが作成されました")
        return True
    except subprocess.CalledProcessError as e:
        print(f"エラー: サンプルスプレッドシートの作成に失敗しました: {e}")
        return False

def set_permissions():
    """実行権限を設定する"""
    print("実行権限を設定中...")
    
    scripts = [
        'mobile_ichiban_scraper.py',
        'update_prices.py',
        'scheduler.py',
        'config.py',
        'create_jan_sample_sheet.py'
    ]
    
    for script in scripts:
        if os.path.exists(script):
            os.chmod(script, 0o755)
            print(f"実行権限を設定: {script}")
    
    print("実行権限の設定が完了しました")

def verify_setup():
    """セットアップの確認"""
    print("セットアップの確認中...")
    
    try:
        # 設定確認
        subprocess.check_call([sys.executable, 'config.py'])
        print("設定確認: OK")
        
        # 必要なファイルの確認
        required_files = [
            'mobile_ichiban_scraper.py',
            'update_prices.py',
            'scheduler.py',
            'config.py',
            'JANコード価格更新用.xlsx'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print("エラー: 以下のファイルが見つかりません:")
            for file in missing_files:
                print(f"  - {file}")
            return False
        
        print("ファイル確認: OK")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"エラー: セットアップの確認に失敗しました: {e}")
        return False

def main():
    """メインセットアップ処理"""
    print("=" * 60)
    print("モバイル一番 価格更新システム セットアップ")
    print("=" * 60)
    
    # 現在のディレクトリを確認
    current_dir = os.getcwd()
    print(f"作業ディレクトリ: {current_dir}")
    
    # セットアップ手順
    steps = [
        ("ライブラリのインストール", install_requirements),
        ("サンプルスプレッドシートの作成", create_sample_spreadsheet),
        ("実行権限の設定", set_permissions),
        ("セットアップの確認", verify_setup)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"エラー: {step_name}に失敗しました")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("セットアップが完了しました！")
    print("=" * 60)
    
    print("\n使用方法:")
    print("1. 手動で価格更新:")
    print("   python3 update_prices.py")
    print("\n2. 定期実行の開始:")
    print("   python3 scheduler.py")
    print("\n3. 詳細な使用方法:")
    print("   README.md をご確認ください")
    
    print("\n注意事項:")
    print("- JANコード価格更新用.xlsx のH列にJANコードを入力してください")
    print("- 初回実行前にファイルのバックアップを取ることをお勧めします")

if __name__ == "__main__":
    main()
