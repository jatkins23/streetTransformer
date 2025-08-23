
# Rework without `fitz`: use PyPDF2 to extract page text, then detect intersections.

# A framework for digesting document pdf files and translating them to geocoded data

# Goals:
# - for a given project:

# - for a given document:
#   - convert to a usable format:
#   - Extract all mentioned intersection locations/cross streets
#   - geocode each using a geocode API
#   - convert this to a multi-string

# Functions: 
#   - take in a document and output a usable format
#   - take in a usable format, run a model, and output a list of geocoded texts
#   - take in a document and output a list of 
#   - take in a list of documents/proects and output a datafile of addresses
#   geocoding:
#       - [geocode.py] take in a cross-street and translate to a point geometry
#       - reconcile multiple point geometries and see if its a linear object

#   CLI:
#       - parse_arguments
#
import re
from typing import List, Tuple, Dict
import PyPDF2
import pandas as pd
from pathlib import Path
import fitz # PyMuPDF
import pytesseract
from PIL import Image
import argparse

STREET_SUFFIXES = (
    "Street","St","Avenue","Ave","Boulevard","Blvd","Road","Rd","Drive","Dr",
    "Place","Pl","Court","Ct","Lane","Ln","Terrace","Terr","Parkway","Pkwy",
    "Way","Walk","Mall","Plaza","Square","Sq","Esplanade","West","East","North","South"
)
STREET_ALT = "|".join(sorted(STREET_SUFFIXES, key=len, reverse=True))
STREET_PAT = re.compile(rf"\b([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*)\s({STREET_ALT})\b")

DPI = 200

# pdf_path = Path('/Users/jon/Documents/Employment/2025 VIDA Lab/proj_data/project_documents/96--Grand Army Plaza Enhancements/96--0--201104_gap-schedule.pdf')
# if pdf_path.exists:
#     print('\npath exists!\n')

# 1) extract all text
def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    reader = PyPDF2.PdfReader(str(pdf_path))
    pages_text: List[str] = []

    for pg in reader.pages:
        txt = (pg.extract_text() or "")
        # normalize whitespace
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\s*\n\s*", "\n", txt)
        pages_text.append(txt)
    return pages_text

# 2) OCR

# def norm(name: str, suf: str) -> str:
#     # Title-case but keep acronyms
#     tokens = f"{name} {suf}".split()
#     return " ".join([t if t.isupper() else t.capitalize() for t in tokens])

# rows = []
# for i, text in enumerate(pages_text, start=1):
#     for m in STREET_PAT.finditer(text):
#         rows.append({"page": i, "street": norm(m.group(1), m.group(2))})

# print(rows)
# df = pd.DataFrame(rows).drop_duplicates().sort_values(["page","street"]).reset_index(drop=True)

# unique_df = pd.DataFrame(sorted(df["street"].unique()), columns=["street"])
# print(unique_df)

#def get_streets_from_pdf():

def extract_ocr_from_pdf(pdf_path: Path)-> List[str]:
    try:    
        doc = fitz.open(str(pdf_path))
        out_text = []
        for i, page in enumerate(doc):
            # Render page to image
            zoom = DPI / 72  # 72 dpi is default
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # OCR
            t = pytesseract.image_to_string(img, lang="eng")
            # Normalize whitespace
            t = re.sub(r"[ \t]+", " ", t)
            t = re.sub(r"\s*\n\s*", "\n", t)
            out_text.append(t)
        ocr_text = out_text
    except Exception as e:
        ocr_text = [""] * len(base_text)
        print(f"OCR unavailable or failed: {e}")

    return ocr_text


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('document', type=str)
    args = parser.parse_args()
    #'/Users/jon/Documents/Employment/2025 VIDA Lab/proj_data/project_documents/96--Grand Army Plaza Enhancements/96--0--201104_gap-schedule.pdf'

    base_text = extract_text_from_pdf(args.document)
    ocr_text = extract_ocr_from_pdf(args.document)
    print('\n')
    print(base_text)
    print('\n')
    print(ocr_text)
    print('\n')
    #print(args.document)