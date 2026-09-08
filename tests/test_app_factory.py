import sys
from unittest.mock import MagicMock, patch
from langgraph.checkpoint.memory import MemorySaver
import app as app_module

def test_get_production_app_memory_fallback(monkeypatch):
    """
    Verifies get_production_app defaults to MemorySaver when DATABASE_URL is unset.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    app_instance = app_module.get_production_app()
    assert app_instance is not None
    assert hasattr(app_instance, "stream")

def test_get_production_app_postgres_branch(monkeypatch):
    """
    Verifies get_production_app instantiates PostgresSaver when DATABASE_URL is set.
    """
    test_db_url = "postgresql://user:pass@localhost:5432/aegis_test_db"
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    # 1. Subclass MemorySaver so isinstance(checkpointer, BaseCheckpointSaver) succeeds in compile()
    class MockPostgresSaver(MemorySaver):
        def __init__(self, conn):
            super().__init__()
            self.setup = MagicMock()

    # 2. Create mock modules
    mock_psycopg_pool = MagicMock()
    mock_postgres_saver_mod = MagicMock()
    
    mock_pool_inst = MagicMock()
    mock_psycopg_pool.ConnectionPool.return_value = mock_pool_inst
    
    # Return our valid checkpointer subclass instance
    mock_postgres_saver_mod.PostgresSaver = MockPostgresSaver

    # 3. Inject mock modules into sys.modules and force HAS_POSTGRES = True
    with patch.dict(sys.modules, {
        "psycopg_pool": mock_psycopg_pool,
        "langgraph.checkpoint.postgres": mock_postgres_saver_mod
    }):
        monkeypatch.setattr(app_module, "HAS_POSTGRES", True)

        # 4. Execute production app factory
        app_instance = app_module.get_production_app()

        # 5. Assertions
        mock_psycopg_pool.ConnectionPool.assert_called_once_with(conninfo=test_db_url)
        assert app_instance is not None