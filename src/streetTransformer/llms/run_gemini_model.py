from __future__ import annotations
from pathlib import Path
from google import genai
from google.genai import types
from typing import List, Optional, Any, Union, Dict
import json
import concurrent.futures as cf


base_dir = Path(__file__).resolve().parent.parent.parent
print(f'Treating "{base_dir}" as `base_dir`')
FLUSH_EVERY = 10

import os
from dotenv import load_dotenv

load_dotenv()
os.getenv('GEMINI_API_KEY')

# Configure generation the Gem is set up
def setup_config(sys_prompt:str, temp:float=.9, top_p:float=.2, response_mime_type:str='application/json'):
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

def run_individual_model(system_prompt:str, files:List[Path], model_name:str='gemini-2.5-flash', client:genai.Client=genai.Client(), outfile:Optional[Path]=None):
    config = setup_config(system_prompt)
    contents = setup_contents(files=files, client=client)

    # geocode
    response = client.models.generate_content(
        model=model_name, 
        contents=contents,
        config=config,
    )

    if outfile:
        outfile.parent.mkdir(parents=True, exist_ok=True)
        with outfile.open('w+', encoding='utf-8') as f:
            f.write(response_to_text(response))

    return response_to_text(response)

def run_many_inputs(
    inputs: Dict[str, Dict[str, Any]],
    *,
    default_system_prompt: str,
    model: str = "gemini-2.5-flash",
    client: genai.Client = genai.Client(),
    outdir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run the same model config on many inputs.

    inputs: dict mapping alias -> {"files": [Path,...], "system_prompt": str?}
      - "files" is required
      - "system_prompt" optional (falls back to default_system_prompt)

    Returns dict alias -> response
    """
    results: Dict[str, Any] = {}

    for alias, entry in inputs.items():
        files = entry.get("files")
        if not files:
            raise ValueError(f"[{alias}] is missing 'files'")
        system_prompt = entry.get("system_prompt", default_system_prompt)

        outfile = None
        if outdir:
            outdir.mkdir(parents=True, exist_ok=True)
            outfile = outdir / f"{alias}.txt"

        resp = run_individual_model(
            system_prompt=system_prompt,
            files=files,
            client=client,
            outfile=outfile,
            model=model,
        )
        results[alias] = resp

    return results