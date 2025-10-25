"""ClickHouse连接管理器 - 从配置读取，禁止硬编码"""
import clickhouse_connect
from clickhouse_connect.driver import Client
from functools import lru_cache
import logging

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ClickHouseManager:
    """ClickHouse连接管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Client | None = None
    
    @property
    def client(self) -> Client:
        """获取ClickHouse客户端（单例模式）"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> Client:
        """创建ClickHouse客户端 - 所有配置从settings读取"""
        try:
            client = clickhouse_connect.get_client(
                host=self.settings.clickhouse_host,
                port=self.settings.clickhouse_port,
                database=self.settings.clickhouse_database,
                username=self.settings.clickhouse_user,
                password=self.settings.clickhouse_password,
                settings={
                    'max_execution_time': self.settings.tool_timeout,
                }
            )
            logger.info(
                f"ClickHouse connected: {self.settings.clickhouse_host}:"
                f"{self.settings.clickhouse_port}/{self.settings.clickhouse_database}"
            )
            return client
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = self.client.query("SELECT 1")
            return result.result_rows[0][0] == 1
        except Exception as e:
            logger.error(f"ClickHouse connection test failed: {e}")
            return False
    
    def get_tables(self) -> list[str]:
        """获取所有表名"""
        query = f"SHOW TABLES FROM {self.settings.clickhouse_database}"
        result = self.client.query(query)
        return [row[0] for row in result.result_rows]
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("ClickHouse connection closed")


# 全局单例
_manager: ClickHouseManager | None = None


@lru_cache(maxsize=1)
def get_clickhouse_manager() -> ClickHouseManager:
    """获取ClickHouse管理器单例"""
    global _manager
    if _manager is None:
        _manager = ClickHouseManager()
    return _manager


def get_clickhouse_client() -> Client:
    """快捷函数：获取ClickHouse客户端"""
    return get_clickhouse_manager().client

