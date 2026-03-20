"""清理向量数据库中的游离数据"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cleanup_orphan_vectors():
    """清理向量数据库中不属于任何文件的向量数据"""
    from app.services.document_processing.embedding.vector_store import get_vector_store
    from app.models.file import db

    print('正在检查向量数据库和文件数据库的一致性...\n')

    # 获取所有向量数据中的 doc_id
    vector_store = get_vector_store()
    all_data = vector_store.collection.get()

    vector_doc_ids = set()
    for meta in all_data.get('metadatas', []):
        if meta and 'doc_id' in meta:
            vector_doc_ids.add(meta['doc_id'])

    # 获取所有数据库中的文件ID
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM files')
    db_files = {row[0]: row[1] for row in cursor.fetchall()}
    db_file_ids = set(db_files.keys())
    conn.close()

    # 找出差异
    only_in_vector = vector_doc_ids - db_file_ids

    print(f'向量库中的唯一doc_id数量: {len(vector_doc_ids)}')
    print(f'数据库中的唯一file_id数量: {len(db_file_ids)}')
    print(f'只在向量库中存在（游离数据）: {len(only_in_vector)} 个\n')

    if only_in_vector:
        print('将删除以下游离向量数据:')
        for doc_id in list(only_in_vector):
            print(f'  - {doc_id}')

        # 确认删除
        confirm = input('\n确认删除这些游离数据? (yes/no): ')
        if confirm.lower() in ['yes', 'y']:
            deleted_count = 0
            for doc_id in only_in_vector:
                count = vector_store.delete_by_doc_id(doc_id)
                deleted_count += count
                print(f'已删除 doc_id={doc_id} 的 {count} 个向量')

            print(f'\n清理完成! 共删除 {deleted_count} 个向量数据')
        else:
            print('已取消清理操作')
    else:
        print('没有发现游离数据，向量数据库与文件数据库一致')

if __name__ == '__main__':
    cleanup_orphan_vectors()
