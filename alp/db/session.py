from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATA_DIR = Path.home() / '.alp'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'mvp.db'

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)