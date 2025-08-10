#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试主应用程序启动脚本
绕过登录窗口直接启动主程序
"""

import tkinter as tk
from database_config import DatabaseManager
from main import PDFChatApp

def main():
    """启动主应用程序"""
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager()
        
        # 连接数据库
        if not db_manager.connect():
            print("❌ 数据库连接失败")
            return
        
        print("✅ 数据库连接成功")
        
        # 创建测试用户信息
        test_user = {
            'id': 1,
            'username': 'test_user',
            'full_name': '测试用户',
            'email': 'test@example.com'
        }
        
        test_session_token = 'test_session_123'
        
        print("🚀 启动主应用程序...")
        
        # 创建主窗口
        root = tk.Tk()
        
        # 强制窗口显示设置
        root.withdraw()  # 先隐藏窗口
        root.update_idletasks()  # 更新窗口
        
        # 设置窗口属性
        width = 1200
        height = 800
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 确保窗口状态正常
        root.state('normal')  # 确保窗口不是最小化状态
        root.deiconify()  # 显示窗口
        
        # 强制置于前台
        root.lift()
        root.attributes('-topmost', True)
        root.focus_force()  # 强制获取焦点
        root.after(100, lambda: root.attributes('-topmost', False))  # 100ms后取消置顶
        
        # 创建应用程序实例
        app = PDFChatApp(root, test_user, test_session_token, db_manager)
        
        print("✅ 主应用程序启动成功")
        
        # 运行主循环
        root.mainloop()
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()