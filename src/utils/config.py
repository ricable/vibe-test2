"""
Configuration management for Multi-Agent RAG system
"""

import os
from dotenv import load_dotenv
from pathlib import Path


class Config:
    """Central configuration for the multi-agent RAG system"""

    def __init__(self):
        load_dotenv()

        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')

        # Model Configuration
        self.student_model = os.getenv('STUDENT_MODEL', 'gpt-4o-mini')
        self.reflection_model = os.getenv('REFLECTION_MODEL', 'gpt-4o')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

        # Vector Database
        self.vector_db_path = Path(os.getenv('VECTOR_DB_PATH', './data/embeddings/faiss_index'))
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '512'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '50'))

        # MLflow
        self.mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', './mlruns')
        self.mlflow_experiment_name = os.getenv('MLFLOW_EXPERIMENT_NAME', 'multi_agent_rag_dspy')

        # GEPA Optimizer
        self.gepa_num_iterations = int(os.getenv('GEPA_NUM_ITERATIONS', '10'))
        self.gepa_population_size = int(os.getenv('GEPA_POPULATION_SIZE', '20'))
        self.gepa_pareto_frontier_size = int(os.getenv('GEPA_PARETO_FRONTIER_SIZE', '5'))
        self.enable_tool_optimization = os.getenv('ENABLE_TOOL_OPTIMIZATION', 'true').lower() == 'true'

        # Meta-Cognitive Reasoning
        self.confidence_threshold = float(os.getenv('META_COGNITIVE_CONFIDENCE_THRESHOLD', '0.8'))
        self.max_retry_attempts = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))

        # Subagent Domains
        self.subagent_domains = os.getenv('SUBAGENT_DOMAINS', 'diabetes,copd,cardiology').split(',')

        # PostgreSQL (for RuVector integration)
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.postgres_db = os.getenv('POSTGRES_DB', 'ruvector')
        self.postgres_user = os.getenv('POSTGRES_USER', 'ruvector')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', 'ruvector')

    @property
    def postgres_connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# Global config instance
config = Config()
