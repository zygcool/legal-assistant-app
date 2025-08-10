import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import time
from database_config import UserManager, CaseManager, DirectoryManager
import PyPDF2
import requests
import json
from PIL import Image, ImageTk
import sqlite3
from datetime import datetime

class PDFChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("律师办案智能助手")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 数据库管理器
        self.user_manager = UserManager()
        self.case_manager = CaseManager()
        self.directory_manager = DirectoryManager()
        
        # 当前用户和卷宗
        self.current_user = None
        self.current_case = None
        self.current_page = "阅卷"  # 当前页面
        
        # PDF相关
        self.pdf_files = []
        self.current_pdf_content = ""
        
        # 创建主界面
        self.create_main_interface()
        
        # 初始化数据库
        self.init_database()
        
        # 加载测试数据
        self.load_test_data()
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect('legal_assistant.db')
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    full_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # 创建卷宗表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_name TEXT NOT NULL,
                    case_number TEXT UNIQUE,
                    client_name TEXT,
                    case_type TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    user_id INTEGER,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建目录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS case_directories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    file_path TEXT,
                    file_name TEXT,
                    file_type TEXT,
                    page_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            print("数据库初始化成功")
            
        except Exception as e:
            print(f"数据库初始化错误: {e}")
    
    def load_test_data(self):
        """加载测试数据"""
        try:
            conn = sqlite3.connect('legal_assistant.db')
            cursor = conn.cursor()
            
            # 检查是否已有测试用户
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                # 创建测试用户
                import hashlib
                password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO users (username, password, email, full_name) 
                    VALUES ('admin', ?, 'admin@example.com', '管理员')
                """, (password_hash,))
                
                user_id = cursor.lastrowid
                
                # 创建测试卷宗
                test_cases = [
                    ('张三诉李四合同纠纷案', 'CASE2024001', '张三', '合同纠纷', '关于房屋买卖合同的纠纷案件'),
                    ('王五交通事故赔偿案', 'CASE2024002', '王五', '交通事故', '交通事故人身损害赔偿纠纷'),
                    ('赵六劳动争议案', 'CASE2024003', '赵六', '劳动争议', '关于工资支付的劳动争议案件'),
                    ('钱七离婚财产分割案', 'CASE2024004', '钱七', '婚姻家庭', '离婚后财产分割纠纷案件'),
                    ('孙八知识产权侵权案', 'CASE2024005', '孙八', '知识产权', '商标侵权纠纷案件')
                ]
                
                for case_data in test_cases:
                    cursor.execute("""
                        INSERT INTO cases (case_name, case_number, client_name, case_type, description, user_id) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (*case_data, user_id))
                
                conn.commit()
                print("测试数据加载成功")
            
            # 设置当前用户
            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            user_data = cursor.fetchone()
            if user_data:
                self.current_user = {
                    'id': user_data[0],
                    'username': user_data[1],
                    'email': user_data[3],
                    'full_name': user_data[4]
                }
            
            conn.close()
            
        except Exception as e:
            print(f"测试数据加载错误: {e}")
    
    def create_main_interface(self):
        """创建主界面"""
        # 创建主框架
        self.main_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建导航栏
        self.create_navigation_panel()
        
        # 创建内容区域
        self.content_frame = tk.Frame(self.main_frame, bg='white', relief=tk.RAISED, bd=1)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 默认显示阅卷页面
        self.show_case_list()
    
    def create_navigation_panel(self):
        """创建导航面板"""
        # 导航面板
        self.nav_frame = tk.Frame(self.main_frame, bg='#2c3e50', width=200)
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.nav_frame.pack_propagate(False)
        
        # 标题
        title_label = tk.Label(self.nav_frame, text="律师办案助手", 
                              font=('Microsoft YaHei', 16, 'bold'), 
                              fg='white', bg='#2c3e50')
        title_label.pack(pady=20)
        
        # 导航按钮
        nav_buttons = ["📋 阅卷", "📁 添加卷宗"]
        
        self.nav_buttons = []
        for i, button_text in enumerate(nav_buttons):
            btn = tk.Button(self.nav_frame, text=button_text, 
                           font=('Microsoft YaHei', 12), 
                           bg='#34495e', fg='white', 
                           relief=tk.FLAT, pady=10,
                           cursor='hand2')
            btn.pack(fill=tk.X, padx=10, pady=5)
            self.nav_buttons.append(btn)
            
            # 绑定点击事件
            if i == 0:  # 阅卷
                btn.configure(command=self.show_case_list)
            elif i == 1:  # 添加卷宗
                btn.configure(command=self.show_add_case)
        
        # 更新按钮样式
        self.update_nav_buttons_style()
        
        # 用户信息
        user_frame = tk.Frame(self.nav_frame, bg='#2c3e50')
        user_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        user_label = tk.Label(user_frame, text="👤 当前用户", 
                             font=('Microsoft YaHei', 10), 
                             fg='#bdc3c7', bg='#2c3e50')
        user_label.pack()
        
        username_label = tk.Label(user_frame, text="管理员", 
                                 font=('Microsoft YaHei', 12, 'bold'), 
                                 fg='white', bg='#2c3e50')
        username_label.pack()
    
    def update_nav_buttons_style(self):
        """更新导航按钮样式"""
        for i, btn in enumerate(self.nav_buttons):
            if (i == 0 and self.current_page == "阅卷") or (i == 1 and self.current_page == "添加案件"):
                btn.configure(bg='#3498db', fg='white')
            else:
                btn.configure(bg='#34495e', fg='white')
            
            # 绑定鼠标悬停事件
            def on_enter(event, button=btn, index=i):
                if not ((index == 0 and self.current_page == "阅卷") or (index == 1 and self.current_page == "添加案件")):
                    button.configure(bg='#4a6741')
            
            def on_leave(event, button=btn, index=i):
                if not ((index == 0 and self.current_page == "阅卷") or (index == 1 and self.current_page == "添加案件")):
                    button.configure(bg='#34495e')
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
    
    def show_case_list(self):
        """显示卷宗列表"""
        self.current_page = "阅卷"
        self.update_nav_buttons_style()
        
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 创建卷宗列表内容
        self.create_case_list_content()
    
    def show_add_case(self):
        """显示添加卷宗页面"""
        self.current_page = "添加案件"
        self.update_nav_buttons_style()
        
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 创建添加卷宗内容
        self.create_add_case_content()
    
    def create_case_list_content(self):
        """创建卷宗列表内容"""
        # 标题
        title_frame = tk.Frame(self.content_frame, bg='white')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        title_label = tk.Label(title_frame, text="📋 卷宗管理", 
                              font=('Microsoft YaHei', 18, 'bold'), 
                              fg='#2c3e50', bg='white')
        title_label.pack(side=tk.LEFT)
        
        # 搜索框
        search_frame = tk.Frame(title_frame, bg='white')
        search_frame.pack(side=tk.RIGHT)
        
        tk.Label(search_frame, text="搜索:", font=('Microsoft YaHei', 10), 
                bg='white', fg='#7f8c8d').pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, 
                               font=('Microsoft YaHei', 10), width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        search_btn = tk.Button(search_frame, text="🔍", 
                              font=('Microsoft YaHei', 10), 
                              bg='#3498db', fg='white', 
                              relief=tk.FLAT, cursor='hand2')
        search_btn.pack(side=tk.LEFT)
        
        # 卷宗列表
        list_frame = tk.Frame(self.content_frame, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 创建滚动框架
        canvas = tk.Canvas(list_frame, bg='white')
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 加载卷宗数据
        self.load_case_list()
    
    def create_add_case_content(self):
        """创建添加卷宗内容"""
        # 标题
        title_frame = tk.Frame(self.content_frame, bg='white')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        title_label = tk.Label(title_frame, text="📁 添加新卷宗", 
                              font=('Microsoft YaHei', 18, 'bold'), 
                              fg='#2c3e50', bg='white')
        title_label.pack(side=tk.LEFT)
        
        # 表单区域
        form_frame = tk.Frame(self.content_frame, bg='white')
        form_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)
        
        # 卷宗名称
        tk.Label(form_frame, text="卷宗名称:", font=('Microsoft YaHei', 12), 
                bg='white', fg='#2c3e50').grid(row=0, column=0, sticky='w', pady=10)
        self.case_name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.case_name_var, 
                font=('Microsoft YaHei', 12), width=40).grid(row=0, column=1, sticky='w', padx=10)
        
        # 案件编号
        tk.Label(form_frame, text="案件编号:", font=('Microsoft YaHei', 12), 
                bg='white', fg='#2c3e50').grid(row=1, column=0, sticky='w', pady=10)
        self.case_number_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.case_number_var, 
                font=('Microsoft YaHei', 12), width=40).grid(row=1, column=1, sticky='w', padx=10)
        
        # 当事人姓名
        tk.Label(form_frame, text="当事人姓名:", font=('Microsoft YaHei', 12), 
                bg='white', fg='#2c3e50').grid(row=2, column=0, sticky='w', pady=10)
        self.client_name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.client_name_var, 
                font=('Microsoft YaHei', 12), width=40).grid(row=2, column=1, sticky='w', padx=10)
        
        # 案件类型
        tk.Label(form_frame, text="案件类型:", font=('Microsoft YaHei', 12), 
                bg='white', fg='#2c3e50').grid(row=3, column=0, sticky='w', pady=10)
        self.case_type_var = tk.StringVar()
        case_type_combo = ttk.Combobox(form_frame, textvariable=self.case_type_var, 
                                      font=('Microsoft YaHei', 12), width=37,
                                      values=['合同纠纷', '交通事故', '劳动争议', '婚姻家庭', '知识产权', '其他'])
        case_type_combo.grid(row=3, column=1, sticky='w', padx=10)
        
        # 案件描述
        tk.Label(form_frame, text="案件描述:", font=('Microsoft YaHei', 12), 
                bg='white', fg='#2c3e50').grid(row=4, column=0, sticky='nw', pady=10)
        self.description_text = tk.Text(form_frame, font=('Microsoft YaHei', 10), 
                                       width=50, height=6)
        self.description_text.grid(row=4, column=1, sticky='w', padx=10)
        
        # 按钮区域
        button_frame = tk.Frame(form_frame, bg='white')
        button_frame.grid(row=5, column=1, sticky='w', padx=10, pady=20)
        
        save_btn = tk.Button(button_frame, text="💾 保存卷宗", 
                            font=('Microsoft YaHei', 12), 
                            bg='#27ae60', fg='white', 
                            relief=tk.FLAT, cursor='hand2',
                            command=self.save_new_case)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(button_frame, text="❌ 取消", 
                              font=('Microsoft YaHei', 12), 
                              bg='#e74c3c', fg='white', 
                              relief=tk.FLAT, cursor='hand2',
                              command=self.show_case_list)
        cancel_btn.pack(side=tk.LEFT)
    
    def load_case_list(self):
        """加载卷宗列表"""
        try:
            conn = sqlite3.connect('legal_assistant.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, case_name, case_number, client_name, case_type, 
                       created_at, updated_at 
                FROM cases 
                WHERE is_deleted = 0 
                ORDER BY updated_at DESC
            """)
            
            cases = cursor.fetchall()
            conn.close()
            
            # 清空现有列表
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            if not cases:
                no_data_label = tk.Label(self.scrollable_frame, 
                                        text="暂无卷宗数据", 
                                        font=('Microsoft YaHei', 14), 
                                        fg='#7f8c8d', bg='white')
                no_data_label.pack(pady=50)
                return
            
            # 创建卷宗行
            for i, case in enumerate(cases):
                self.create_case_row(case, i)
                
        except Exception as e:
            print(f"加载卷宗列表错误: {e}")
            messagebox.showerror("错误", f"加载卷宗列表失败: {e}")
    
    def create_case_row(self, case, index):
        """创建卷宗行"""
        case_id, case_name, case_number, client_name, case_type, created_at, updated_at = case
        
        # 行框架
        row_frame = tk.Frame(self.scrollable_frame, bg='#f8f9fa', relief=tk.RAISED, bd=1)
        row_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 左侧信息
        info_frame = tk.Frame(row_frame, bg='#f8f9fa')
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 卷宗名称
        name_label = tk.Label(info_frame, text=case_name, 
                             font=('Microsoft YaHei', 14, 'bold'), 
                             fg='#2c3e50', bg='#f8f9fa')
        name_label.pack(anchor='w')
        
        # 详细信息
        details_frame = tk.Frame(info_frame, bg='#f8f9fa')
        details_frame.pack(anchor='w', pady=(5, 0))
        
        tk.Label(details_frame, text=f"案件编号: {case_number or 'N/A'}", 
                font=('Microsoft YaHei', 10), fg='#7f8c8d', bg='#f8f9fa').pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(details_frame, text=f"当事人: {client_name or 'N/A'}", 
                font=('Microsoft YaHei', 10), fg='#7f8c8d', bg='#f8f9fa').pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(details_frame, text=f"类型: {case_type or 'N/A'}", 
                font=('Microsoft YaHei', 10), fg='#7f8c8d', bg='#f8f9fa').pack(side=tk.LEFT)
        
        # 时间信息
        time_label = tk.Label(info_frame, text=f"创建时间: {created_at}", 
                             font=('Microsoft YaHei', 9), fg='#95a5a6', bg='#f8f9fa')
        time_label.pack(anchor='w', pady=(2, 0))
        
        # 右侧按钮
        button_frame = tk.Frame(row_frame, bg='#f8f9fa')
        button_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        open_btn = tk.Button(button_frame, text="📖 打开", 
                            font=('Microsoft YaHei', 10), 
                            bg='#3498db', fg='white', 
                            relief=tk.FLAT, cursor='hand2',
                            command=lambda: self.open_case(case_id))
        open_btn.pack(side=tk.TOP, pady=(0, 5))
        
        edit_btn = tk.Button(button_frame, text="✏️ 编辑", 
                            font=('Microsoft YaHei', 10), 
                            bg='#f39c12', fg='white', 
                            relief=tk.FLAT, cursor='hand2',
                            command=lambda: self.edit_case(case_id))
        edit_btn.pack(side=tk.TOP)
        
        print(f"创建卷宗行: {case_name}")
    
    def save_new_case(self):
        """保存新卷宗"""
        try:
            case_name = self.case_name_var.get().strip()
            case_number = self.case_number_var.get().strip()
            client_name = self.client_name_var.get().strip()
            case_type = self.case_type_var.get().strip()
            description = self.description_text.get("1.0", tk.END).strip()
            
            if not case_name:
                messagebox.showerror("错误", "请输入卷宗名称")
                return
            
            conn = sqlite3.connect('legal_assistant.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cases (case_name, case_number, client_name, case_type, description, user_id) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (case_name, case_number, client_name, case_type, description, 1))  # 假设用户ID为1
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("成功", "卷宗保存成功！")
            self.show_case_list()  # 返回卷宗列表
            
        except Exception as e:
            print(f"保存卷宗错误: {e}")
            messagebox.showerror("错误", f"保存卷宗失败: {e}")
    
    def open_case(self, case_id):
        """打开卷宗"""
        messagebox.showinfo("提示", f"打开卷宗 ID: {case_id}")
    
    def edit_case(self, case_id):
        """编辑卷宗"""
        messagebox.showinfo("提示", f"编辑卷宗 ID: {case_id}")

def main():
    root = tk.Tk()
    app = PDFChatApp(root)
    print("主应用程序启动成功")
    root.mainloop()

if __name__ == "__main__":
    main()