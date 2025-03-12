from datetime import datetime
from mysql.connector import Error
import json
from models import Database, Config
from search_engine import create_search_processor

class SearchRequest:
    """
    处理和存储用户的检索请求
    """
    def __init__(self):
        self.config = Config()
        print(self.config)
        self.db = Database(self.config.db_config())
        # print(self.db)
    def store_search_request(self, email, categories, query_content, push_time):
        """
        将用户的检索请求存储到数据库中
        
        参数:
        - email: 用户邮箱地址
        - categories: 需要检索的文章类型（列表或字典）
        - query_content: 检索请求内容
        - push_time: 期待的推送时间（datetime.time对象）
        
        返回:
        - request_id: 新创建的检索请求ID
        """
        insert_query = """
        INSERT INTO search_requests 
        (email, categories, query_content, push_time)
        VALUES (%s, %s, %s, %s)
        """
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 确保categories是JSON字符串
            if isinstance(categories, (dict, list)):
                categories = json.dumps(categories)
            
            # 确保push_time是time类型
            if isinstance(push_time, str):
                push_time = datetime.strptime(push_time, '%H:%M').time()
            
            cursor.execute(insert_query, (
                email,
                categories,
                query_content,
                push_time
            ))
            
            request_id = cursor.lastrowid
            conn.commit()
            return request_id
            
        except Error as e:
            print(f"存储检索请求时出错: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()
    
    def store_search_results(self, request_id, results):
        """
        存储检索结果
        
        参数:
        - request_id: 检索请求ID
        - results: 列表，每项包含 (entry_id, ranking, relevance_score)
        """
        insert_query = """
        INSERT INTO search_results 
        (request_id, entry_id, ranking, relevance_score)
        VALUES (%s, %s, %s, %s)
        """
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.executemany(insert_query, [
                (request_id, result[0], result[1], result[2])
                for result in results
            ])
            
            # 更新search_requests表中的result_count
            update_query = """
            UPDATE search_requests 
            SET result_count = %s 
            WHERE request_id = %s
            """
            cursor.execute(update_query, (len(results), request_id))
            
            conn.commit()
            
        except Error as e:
            print(f"存储检索结果时出错: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
