"""Load original sample without requiring a binary file in source transfers."""
from pathlib import Path
import base64
def sample_bytes():
 root=Path(__file__).resolve().parent
 path=root/'data/sample.xlsx'
 return path.read_bytes() if path.exists() else base64.b64decode((root/'data/sample.xlsx.b64').read_text(encoding='ascii'))
