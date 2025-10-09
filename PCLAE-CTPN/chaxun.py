import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM audio_results ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()

#下面为清空数据库代码
# import sqlite3
# import os

# def clear_database():
#     # 获取数据库路径
#     db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
    
#     # 连接数据库
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()
    
#     try:
#         # 清空audio_results表中的所有记录
#         cursor.execute("DELETE FROM audio_results")
#         # 提交事务自增ID计数器（可选，根据需求决定是否添加）
#         # cursor.execute("DELETE FROM sqlite_sequence WHERE name='audio_results'")
#         conn.commit()
#         print("数据库表audio_results中的所有记录已成功清空")
#     except Exception as e:
#         conn.rollback()
#         print(f"清空数据库失败: {str(e)}")
#     finally:
#         # 关闭连接
#         conn.close()

# if __name__ == "__main__":
#     clear_database()
    