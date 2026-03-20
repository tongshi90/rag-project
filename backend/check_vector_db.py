"""检查向量数据库和文件数据库的一致性"""
from app.services.document_processing.embedding.vector_store import get_vector_store
from app.models.file import db

# 获取所有向量数据中的 doc_id
vector_store = get_vector_store()
try:
    # 获取所有数据
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
    only_in_db = db_file_ids - vector_doc_ids

    print(f'向量库中的唯一doc_id数量: {len(vector_doc_ids)}')
    print(f'数据库中的唯一file_id数量: {len(db_file_ids)}')
    print(f'只在向量库中存在（游离数据）: {len(only_in_vector)} 个')
    if only_in_vector:
        for doc_id in list(only_in_vector)[:10]:
            print(f'  - {doc_id}')
        if len(only_in_vector) > 10:
            print(f'  ... 还有 {len(only_in_vector) - 10} 个')
    print(f'只在数据库中存在（没有向量数据）: {len(only_in_db)} 个')
    if only_in_db:
        for file_id in list(only_in_db)[:10]:
            print(f'  - {file_id}: {db_files.get(file_id, "N/A")}')
        if len(only_in_db) > 10:
            print(f'  ... 还有 {len(only_in_db) - 10} 个')

    # 询问是否清理
    if only_in_vector:
        print('\n' + '='*60)
        choice = input('是否清理向量库中的游离数据? (y/n): ')
        if choice.lower() == 'y':
            for doc_id in only_in_vector:
                count = vector_store.delete_by_doc_id(doc_id)
                print(f'已删除 doc_id={doc_id} 的 {count} 个向量')
            print('清理完成!')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
