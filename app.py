# app.py
import os
from graph.credit_graph import build_credit_graph, HAS_POSTGRES

def get_production_app():
    """
    Instantiates graph with PostgresSaver if DB_URI environment variable is present,
    otherwise falls back to MemorySaver.
    """
    db_uri = os.getenv("DATABASE_URL")
    
    if db_uri and HAS_POSTGRES:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool
        
        print("[Aegis Runtime] Initializing Production PostgresCheckpointer...")
        pool = ConnectionPool(conninfo=db_uri)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        return build_credit_graph(checkpointer=checkpointer)
    else:
        print("[Aegis Runtime] Initializing Local MemorySaver Checkpointer...")
        return build_credit_graph()

if __name__ == "__main__":
    app = get_production_app()
    print("[Aegis Runtime] StateGraph compiled successfully and ready for thread execution.")