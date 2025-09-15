# TODO: Now this is duplicative. It should inherit functions from src.streetTarnsformer.llms.run_gemini_model

from pathlib import Path
from google import genai
from google.genai import types
from typing import List, Optional, Any
from dotenv import load_dotenv
from tqdm import tqdm
import os
import re
import json

import pandas as pd 
base_dir = Path(__file__).resolve().parent.parent.parent
print(f'Treating "{base_dir}" as `base_dir`')
DOCS_DIR = base_dir.parent / 'proj_data/project_documents/'
DOCUMENTS_df = pd.read_csv(DOCS_DIR / 'projects_df.csv', index_col=0)

OUT_NDJSON = Path("gemini_output2.ndjson")   # append-only log (one JSON per line)
OUT_CSV    = Path("gemini_output2.csv")      # final tabular export
FLUSH_EVERY = 10                            # fsync every N writes for safety


load_dotenv()
os.getenv('GEMINI_API_KEY')

# Set up Gem
SYSTEM_INSTRUCTIONS = """
You are a city employee tasked with determining the location of street construction projects from a pdf. 

Your goal is to read through the document and return structured data of all intersections that are affected by the project. You will then return the locations found (and the relevant page) and then geocode it. You should also return your confidence in each assessment (1-5). Be sure to check the diagrams as well which should detail exactly which cross-streets are affected.

The response should be returned in a json structure with only the relevant data. There can (but aren't necessarily) multiple per trip.
    `cross_streets`: List[str]
    `page_found`: int
    `coordinates`: (float, float)
    `confidence`: int
"""

def gather_all_project_docs(docs_df: pd.DataFrame, source_dir: Path):
    export_dir = {}
    
    for idx, name in zip(docs_df.index, docs_df.name):
        pattern = re.compile(rf"^{idx}--\b")
        project_dirs = [p for p in source_dir.iterdir() if p.is_dir() and pattern.match(p.name)]
        
        if len(project_dirs) != 1:
            raise ValueError()
        else:
            project_dir = project_dirs[0]

        documents = [x for x in project_dir.iterdir()]
        
        export_dir[idx] = documents

    return export_dir
       

# Configure generation the Gem is set up
def setup_config(sys_prompt:str=SYSTEM_INSTRUCTIONS, temp:float=.9, top_p:float=.2, response_mime_type:str='application/json'):
    config = types.GenerateContentConfig(
        system_instruction=sys_prompt,
        temperature=temp,
        top_p=top_p,
        response_mime_type=response_mime_type  # to encourage JSON output
    )
    return config

# Make a single-shot request (text-only or multimodal w/ file)
def setup_contents(files:List[Path], client, user_prompt:str='Documents: '):
    contents = [user_prompt]
    for pdf_file in files:
        if pdf_file.exists(): 
            uploaded = client.files.upload(file=pdf_file)
            if uploaded:
                contents.append(uploaded)

    return contents

def run_individual_model(client, files:List[Path], outfile:Optional[Path]=None):
    config = setup_config()
    contents = setup_contents(files=files, client=client)

    # geocode
    response = client.models.generate_content(
        model="gemini-2.5-flash",   # swap to 2.5-pro for stronger reasoning
        contents=contents,
        config=config,
    )

    return response

def load_downloaded_ids(path: Path) -> set:
    """Read existing ndjson and collect ids already processed."""
    done = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done.add(rec["id"])
                except Exception:
                    # tolerate partial or malformed lines
                    continue
    return done

def response_to_text(resp: Any) -> str:
    """Extract text robustly whether run_individual_model returns an object or a string."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    # try common attributes
    for attr in ("text", "content", "message"):
        if hasattr(resp, attr):
            val = getattr(resp, attr)
            return val if isinstance(val, str) else str(val)
    return str(resp)

def process_all_docs(projects_docs_dict: dict, out_ndjson:Path=OUT_NDJSON, out_csv:Path=OUT_CSV, flush_every:int=FLUSH_EVERY):
    # connect to client
    client = genai.Client()  # picks up GOOGLE_API_KEY automatically

    # Run
    total_rows = len(projects_docs_dict.keys())
    wrote = 0

    done_ids = load_downloaded_ids(out_ndjson)
    with out_ndjson.open("a", encoding="utf-8") as out_f:
        for idx, files in tqdm(projects_docs_dict.items(), total=total_rows, desc="Proecessing locations"): 
            if idx in done_ids:
                continue

            try:
                resp = run_individual_model(client, files)
                text = response_to_text(resp)
            except Exception as e:
                print(f"Error {idx} - {e}")
                text = ""
            
            # append one compact JSON per line (safe to resume)
            rec = {"id": idx, "text": text}
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1


            # periodically flush to disk so progress isn't lost
            if wrote % flush_every == 0:
                out_f.flush()
                os.fsync(out_f.fileno())

    # Build the final CSV *from the ndjson log* (includes all past runs)
    df = pd.read_json(out_ndjson, lines=True)

    # If you prefer a wide format keyed by id, keep as-is. Otherwise set index or reorder:
    # df = df.sort_values("id")  # optional
    df.to_csv(out_csv, index=False)


if __name__ == '__main__':
    # Assemble all docs
    projects_docs_dict = gather_all_project_docs(DOCUMENTS_df, DOCS_DIR)

    # Process all docs
    process_all_docs(projects_docs_dict, out_ndjson=(base_dir / 'data/project_documents/geocoded/gemini_output2.ndjson'))