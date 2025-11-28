import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        # FIX: psycopg2 does not support 'postgresql+asyncpg://' scheme.
        # We replace it with 'postgresql://' to make it compatible.
        sync_db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = psycopg2.connect(sync_db_url)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e

def run_pg_sql(query: str, params: tuple = None, fetch_one: bool = False):
    """
    Executes a SQL query and returns the results as a dictionary.
    Handles connection opening/closing automatically.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            
            # handling cases where no result is returned (e.g. INSERT/UPDATE)
            if cur.description is None:
                conn.commit()
                return {"status": "success"}

            if fetch_one:
                result = cur.fetchone()
            else:
                result = cur.fetchall()
            
            conn.commit()
            
            # Convert RealDictRow to standard dict for JSON serialization
            if isinstance(result, list):
                return [dict(row) for row in result]
            elif result:
                return dict(result)
            return None
            
    except Exception as e:
        conn.rollback()
        print(f"SQL Error: {e}")
        raise e
    finally:
        conn.close()

def get_embedding(
        text: str,     
        model: str = "gemini-embedding-001",
    	output_dim: int = 1536
    ) -> List[float]:
    """
    Generates an embedding vector for the given text using Gemini.
    """
    try:
        # Using the model specified in your schema default
        # Ensure you are using a model you have access to, e.g., 'text-embedding-004'
        result = client.models.embed_content(
			model=model,
			contents=text,
			config=types.EmbedContentConfig(
				task_type="SEMANTIC_SIMILARITY",
				output_dimensionality=output_dim,
			),
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Embedding Error: {e}")
        # Return a zero vector or handle specific error logic
        return []