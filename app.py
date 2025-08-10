#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
律师办案智能助手 - 主启动程序

这是应用程序的主入口点，负责：
1. 初始化数据库
2. 启动登录窗口
3. 管理应用程序生命周期
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
from database_config import DatabaseManager
from login_window import LoginWindow

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = [
        'PyPDF2',
        'pdfplumber', 
        'fitz',  # PyMuPDF
        'PIL',   # Pillow
        'mysql.connector'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'fitz':
                import fitz
            elif package == 'PIL':
                from PIL import Image
            elif package == 'mysql.connector':
                import mysql.connector
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请使用以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    
    db_manager = DatabaseManager()
    
    # 尝试连接数据库
    if not db_manager.connect():
        print("数据库连接失败！")
        print("请确保：")
        print("1. MySQL服务已启动")
        print("2. 数据库配置正确 (database_config.py)")
        print("3. 数据库用户有足够权限")
        return False
    
    # 检查数据库表是否存在
    try:
        # 检查用户表
        result = db_manager.execute_query("SHOW TABLES LIKE 'users'")
        if not result:
            print("数据库表不存在，请先运行 database_schema.sql 创建表结构")
            return False
        
        print("数据库初始化成功！")
        return True
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return False
    
    finally:
        db_manager.disconnect()

def create_sample_data():
    """创建示例数据（可选）"""
    print("正在创建示例数据...")
    
    db_manager = DatabaseManager()
    if not db_manager.connect():
        return False
    
    try:
        from database_config import UserManager
        user_manager = UserManager(db_manager)
        
        # 检查是否已有管理员用户
        admin_check = db_manager.execute_query(
            "SELECT id FROM users WHERE username = 'admin'"
        )
        
        if not admin_check:
            # 创建默认管理员账户
            hashed_password = UserManager.hash_password('admin123')
            
            admin_id = db_manager.execute_insert(
                "INSERT INTO users (username, password, full_name, email, role) VALUES (%s, %s, %s, %s, %s)",
                ('admin', hashed_password, '系统管理员', 'admin@example.com', 'admin')
            )
            
            if admin_id > 0:
                print("已创建默认管理员账户:")
                print("  用户名: admin")
                print("  密码: admin123")
                print("  请登录后及时修改密码！")
            else:
                print("创建管理员账户失败")
        
        return True
        
    except Exception as e:
        print(f"创建示例数据失败: {e}")
        return False
    
    finally:
        db_manager.disconnect()

def main():
    """主函数"""
    print("="*50)
    print("律师办案智能助手")
    print("版本: 1.0.0")
    print("="*50)
    
    # 检查依赖
    print("\n1. 检查依赖包...")
    if not check_dependencies():
        input("\n按回车键退出...")
        return
    print("依赖检查通过！")
    
    # 初始化数据库
    print("\n2. 初始化数据库...")
    if not init_database():
        input("\n按回车键退出...")
        return
    
    # 创建示例数据
    print("\n3. 检查示例数据...")
    create_sample_data()
    
    print("\n4. 启动应用程序...")
    
    try:
        # 启动GUI应用程序
        root = tk.Tk()
        app = LoginWindow(root)
        root.mainloop()
        
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        messagebox.showerror("错误", f"应用程序启动失败: {e}")
    
    print("\n应用程序已退出")

if __name__ == "__main__":
    main()