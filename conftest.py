# conftest.py
import sys
from pathlib import Path

# Force the project root directory into sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))