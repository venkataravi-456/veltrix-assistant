import shutil
import os
import pytest
from src.config import settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Fresh copy of veltrix.db for testing
    backup_db = settings.DB_PATH + ".backup"
    if os.path.exists(settings.DB_PATH) and not os.path.exists(backup_db):
        shutil.copy(settings.DB_PATH, backup_db)
        
    # Restore fresh DB from original source
    orig_src = "c:/Project/veltrix_assessment/veltrix.db"
    if os.path.exists(orig_src):
        shutil.copy(orig_src, settings.DB_PATH)
        
    yield
    
    # Restore backup if needed
    if os.path.exists(orig_src):
        shutil.copy(orig_src, settings.DB_PATH)
