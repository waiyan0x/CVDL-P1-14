"""Download standard EasyOCR weights once; inference subsequently works offline."""
import os
from pathlib import Path
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()
import easyocr

root = Path(__file__).resolve().parents[1]
easyocr.Reader(['en'], gpu=False, model_storage_directory=str(root / '.cache/easyocr'), verbose=False)
print('EasyOCR weights ready. No network connection is needed to run the demo.')
