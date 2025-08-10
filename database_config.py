import mysql.connector
import hashlib
import datetime
from typing import Optional, List, Dict, Any, Tuple

class DatabaseConfig:
    """数据库连接配置类"""
    
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'legal_assistant',
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            connection = mysql.connector.connect(**self.config)
            return connection
        except mysql.connector.Error as e:
            print(f"数据库连接错误: {e}")
            return None
    
    def close_connection(self, connection):
        """关闭数据库连接"""
        if connection and connection.is_connected():
            connection.close()

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.db_config = DatabaseConfig()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        connection = self.db_config.get_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except mysql.connector.Error as e:
            print(f"查询执行错误: {e}")
            return []
        finally:
            self.db_config.close_connection(connection)
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """执行更新操作"""
        connection = self.db_config.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            print(f"更新执行错误: {e}")
            connection.rollback()
            return False
        finally:
            self.db_config.close_connection(connection)
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[int]:
        """执行插入操作并返回插入的ID"""
        connection = self.db_config.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            insert_id = cursor.lastrowid
            cursor.close()
            return insert_id
        except mysql.connector.Error as e:
            print(f"插入执行错误: {e}")
            connection.rollback()
            return None
        finally:
            self.db_config.close_connection(connection)

class UserManager:
    """用户管理类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        hashed_password = self.hash_password(password)
        query = "SELECT * FROM users WHERE username = %s AND password = %s AND is_active = 1"
        users = self.db_manager.execute_query(query, (username, hashed_password))
        
        if users:
            user = users[0]
            # 更新最后登录时间
            self.update_last_login(user['id'])
            return user
        return None
    
    def update_last_login(self, user_id: int) -> bool:
        """更新最后登录时间"""
        query = "UPDATE users SET last_login = %s WHERE id = %s"
        return self.db_manager.execute_update(query, (datetime.datetime.now(), user_id))
    
    def create_session(self, user_id: int, session_token: str) -> bool:
        """创建用户会话"""
        query = "INSERT INTO user_sessions (user_id, session_token, created_at) VALUES (%s, %s, %s)"
        return self.db_manager.execute_insert(query, (user_id, session_token, datetime.datetime.now())) is not None
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """验证用户会话"""
        query = """
        SELECT u.* FROM users u 
        JOIN user_sessions s ON u.id = s.user_id 
        WHERE s.session_token = %s AND u.is_active = 1
        """
        users = self.db_manager.execute_query(query, (session_token,))
        return users[0] if users else None

class CaseManager:
    """卷宗管理类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def create_case(self, case_name: str, case_number: str, client_name: str, 
                   case_type: str, description: str, user_id: int) -> Optional[int]:
        """创建新卷宗"""
        query = """
        INSERT INTO cases (case_name, case_number, client_name, case_type, 
                          description, user_id, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        now = datetime.datetime.now()
        return self.db_manager.execute_insert(
            query, (case_name, case_number, client_name, case_type, description, user_id, now, now)
        )
    
    def get_cases_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有卷宗"""
        query = "SELECT * FROM cases WHERE user_id = %s AND is_deleted = 0 ORDER BY updated_at DESC"
        return self.db_manager.execute_query(query, (user_id,))
    
    def get_case_by_id(self, case_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取卷宗"""
        query = "SELECT * FROM cases WHERE id = %s AND is_deleted = 0"
        cases = self.db_manager.execute_query(query, (case_id,))
        return cases[0] if cases else None
    
    def update_case(self, case_id: int, **kwargs) -> bool:
        """更新卷宗信息"""
        if not kwargs:
            return False
        
        # 构建更新字段
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['case_name', 'case_number', 'client_name', 'case_type', 'description', 'status']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        # 添加更新时间
        set_clauses.append("updated_at = %s")
        params.append(datetime.datetime.now())
        params.append(case_id)
        
        query = f"UPDATE cases SET {', '.join(set_clauses)} WHERE id = %s"
        return self.db_manager.execute_update(query, tuple(params))
    
    def delete_case(self, case_id: int) -> bool:
        """软删除卷宗"""
        query = "UPDATE cases SET is_deleted = 1, updated_at = %s WHERE id = %s"
        return self.db_manager.execute_update(query, (datetime.datetime.now(), case_id))

class DirectoryManager:
    """目录管理类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def add_directory_item(self, case_id: int, file_path: str, file_name: str, 
                          file_type: str, page_number: int = None) -> Optional[int]:
        """添加目录项"""
        query = """
        INSERT INTO case_directories (case_id, file_path, file_name, file_type, 
                                    page_number, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.db_manager.execute_insert(
            query, (case_id, file_path, file_name, file_type, page_number, datetime.datetime.now())
        )
    
    def get_directory_by_case(self, case_id: int) -> List[Dict[str, Any]]:
        """获取卷宗的目录"""
        query = "SELECT * FROM case_directories WHERE case_id = %s ORDER BY created_at ASC"
        return self.db_manager.execute_query(query, (case_id,))
    
    def update_directory_item(self, item_id: int, **kwargs) -> bool:
        """更新目录项"""
        if not kwargs:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['file_path', 'file_name', 'file_type', 'page_number']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(item_id)
        query = f"UPDATE case_directories SET {', '.join(set_clauses)} WHERE id = %s"
        return self.db_manager.execute_update(query, tuple(params))
    
    def delete_directory_item(self, item_id: int) -> bool:
        """删除目录项"""
        query = "DELETE FROM case_directories WHERE id = %s"
        return self.db_manager.execute_update(query, (item_id,))
    
    def clear_case_directory(self, case_id: int) -> bool:
        """清空卷宗目录"""
        query = "DELETE FROM case_directories WHERE case_id = %s"
        return self.db_manager.execute_update(query, (case_id,))
    
    def batch_add_directory_items(self, items: List[Tuple]) -> bool:
        """批量添加目录项"""
        if not items:
            return True
        
        connection = self.db_manager.db_config.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            query = """
            INSERT INTO case_directories (case_id, file_path, file_name, file_type, 
                                        page_number, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(query, items)
            connection.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            print(f"批量插入错误: {e}")
            connection.rollback()
            return False
        finally:
            self.db_manager.db_config.close_connection(connection)