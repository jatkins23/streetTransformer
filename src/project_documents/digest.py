from pathlib import Path
import pdfplumber
import argparse
from ollama import chat, ChatResponse

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('file')

    args = parser.parse_args()

    return args

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from pdf document"""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)

def chunk_text(text: str, max_tokens: int = 1000, overlap: int = 200):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks

def ollama_process_pdf(model_name: str, pdf_path: Path):
    # Extract
    raw = extract_text_from_pdf(pdf_path)
    # Chunk
    chunks = chunk_text(raw)

    # Loop through chunks
    stream = chat(
        model=model_name,
        messages=[{"role": "user", "content": "Summarize the following text:\n\n" + chunks[0]}],
        stream=True
    )

    for chunk in stream:
        print(chunk.message.content, end="", flush=True)


## Duplicative ##
def run_model(model, chunks):
    responses = []
    stream = chat(
        model=model,
        messages=[{'role': 'user', 'content': chunks[0]}],
        stream=True
    )

    for chunk in stream:
        responses.append(chunk.message.content)
        print(chunk.message.content, end="", flush=True)

    return ' '.join(responses)

if __name__ == '__main__':
    args = parse_args()
    
    input_file = Path(args.file)
    assert input_file.suffix.lower() == '.pdf'

    summary = ollama_process_pdf('doc_reader', input_file)

    print("\n\n=== Full Aggregated Output ===\n", summary)