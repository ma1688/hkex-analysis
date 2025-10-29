#!/usr/bin/env python3
"""
清理重复数据脚本
用于删除基于file_path的重复文档记录
"""

import sys
from pathlib import Path

# 导入项目配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config.settings import get_settings
import clickhouse_connect

settings = get_settings()

def cleanup_duplicates(dry_run: bool = True):
    """
    清理重复文档
    
    Args:
        dry_run: True=仅显示将要删除的记录，False=真正删除
    """
    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password
    )
    
    print("=" * 80)
    print("  清理重复数据工具")
    print("=" * 80)
    
    # 1. 查找重复文档（基于file_path）
    print("\n🔍 查找重复文档...")
    
    duplicates_query = """
    SELECT 
        file_path,
        groupArray(doc_id) as doc_ids,
        count() as cnt
    FROM documents_v2
    GROUP BY file_path
    HAVING cnt > 1
    ORDER BY cnt DESC
    """
    
    duplicates = client.query(duplicates_query).result_rows
    
    if not duplicates:
        print("✅ 未发现重复文档")
        return
    
    print(f"⚠️  发现 {len(duplicates)} 个文件有重复记录")
    print("-" * 80)
    
    total_to_delete = 0
    
    for file_path, doc_ids, count in duplicates:
        print(f"\n文件: {file_path}")
        print(f"重复记录数: {count}")
        print(f"doc_ids: {doc_ids}")
        
        # 保留最新的记录，删除旧记录
        if len(doc_ids) > 1:
            # 查询创建时间，保留最新的
            time_query = f"""
            SELECT doc_id, created_at 
            FROM documents_v2 
            WHERE doc_id IN {tuple(doc_ids)}
            ORDER BY created_at DESC
            """
            
            records = client.query(time_query).result_rows
            keep_doc_id = records[0][0]  # 最新的
            delete_doc_ids = [r[0] for r in records[1:]]  # 要删除的
            
            print(f"  保留: {keep_doc_id}")
            print(f"  删除: {delete_doc_ids}")
            
            total_to_delete += len(delete_doc_ids)
            
            if not dry_run:
                # 删除旧的文档记录
                for doc_id in delete_doc_ids:
                    # 先删除章节
                    client.command(f"ALTER TABLE document_sections DELETE WHERE doc_id = '{doc_id}'")
                    # 再删除文档
                    client.command(f"ALTER TABLE documents_v2 DELETE WHERE doc_id = '{doc_id}'")
                    print(f"  ✅ 已删除: {doc_id}")
    
    print("\n" + "=" * 80)
    if dry_run:
        print(f"⚠️  预演模式：将删除 {total_to_delete} 条记录")
        print("运行 'python cleanup_duplicates.py --execute' 执行真正删除")
    else:
        print(f"✅ 已删除 {total_to_delete} 条记录")
        print("正在优化表...")
        client.command("OPTIMIZE TABLE documents_v2 FINAL")
        client.command("OPTIMIZE TABLE document_sections FINAL")
        print("✅ 表优化完成")
    print("=" * 80)
    
    client.close()


def main():
    dry_run = True
    
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False
        print("⚠️  警告：将执行真正的删除操作！")
        response = input("确认继续？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return
    
    cleanup_duplicates(dry_run=dry_run)


if __name__ == '__main__':
    main()

