import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
DATA_PATH = Path(str(os.getenv('DATA_PATH')))
OPENNYC_PATH = DATA_PATH / 'raw' / 'citydata' / 'openNYC'
DOCUMENTS_PATH = DATA_PATH / 'raw' / 'documents'
UNIVERSES_PATH = DATA_PATH / 'runtime' / 'universes'

# Env Variables
YEARS = list(range(2006, 2025))
YEARS_str = [str(y) for y in YEARS]