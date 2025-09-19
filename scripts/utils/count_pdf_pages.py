from pathlib import Path
import fitz  # PyMuPDF
import sys

def count_pdf_pages(root_folder: Path) -> int:
    total_pages = 0
    for pdf_path in root_folder.rglob("*.pdf"):
        try:
            with fitz.open(pdf_path) as doc:
                n = doc.page_count
                total_pages += n
                print(f"{pdf_path} → {n} pages")
        except Exception as e:
            print(f"Could not read {pdf_path}: {e}")
    print(f"\nTotal pages across all PDFs: {total_pages}")
    return total_pages

# Example usage
if __name__ == "__main__":
    folder = Path(str(sys.argv[-1]))
    count_pdf_pages(folder)