from __future__ import annotations
from pathlib import Path
from google import genai
from google.genai import types

import time
import random
import threading
from collections import deque
from typing import List, Optional, Any, Union, Dict, Tuple
import json
import concurrent.futures as cf

FLUSH_EVERY = 10

import os
from dotenv import load_dotenv

load_dotenv()
os.getenv('GEMINI_API_KEY')

# Configure generation the Gem is set up
def setup_config(sys_prompt:str, temp:float=.9, top_p:float=.2, response_mime_type:str='application/json') -> types.GenerateContentConfig:
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

def upload_imgs(img_paths:Dict[str, Path], base_path:Optional[Path]=None, client:genai.Client=genai.Client()) -> Dict[str, types.File]:
    if base_path:
        img_full_paths = {k: base_path / p for k, p in img_paths.items()}
    else:
        img_full_paths = img_paths
    return {k: client.files.upload(file=p) for k, p in img_full_paths.items()}


# 
def setup_contents_imagecompare_json(start_img_uri:str, end_img_uri:str, user_prompt:str='Here are the images. Image A is BEFORE, B is AFTER: ') -> types.ContentListUnionDict:
    if start_img_uri and end_img_uri:
        contents = [{
            'role': 'user',
            'parts': [
                {'text': user_prompt},
                {'text': 'image A (before):'},
                {"file_data": {"file_uri": start_img_uri, "mime_type": "image/png"}},
                {'text': 'image B (before):'},
                {"file_data": {"file_uri": end_img_uri, "mime_type": "image/png"}}
            ]
        }]
        return contents
    else:
        raise Warning('Unable to upload image')


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

# ---- Simple thread-safe RPM limiter ----
class RateLimiter:
    """Allow up to max_calls per 'period' seconds (sliding window)."""
    def __init__(self, max_calls: int, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.time()
            # drop timestamps older than the window
            while self._calls and now - self._calls[0] >= self.period:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                # sleep until the oldest call exits the window
                wait = self.period - (now - self._calls[0]) + 0.01
                time.sleep(max(0.0, wait))
                # after sleeping, clean up again
                now = time.time()
                while self._calls and now - self._calls[0] >= self.period:
                    self._calls.popleft()

            self._calls.append(time.time())


# a module-level limiter you can share across calls/threads
DEFAULT_LIMITER = RateLimiter(max_calls=15, period=60.0)

def _is_retryable(err: Exception) -> bool:
    status = getattr(err, "status", None) or getattr(err, "code", None)
    http_status = getattr(err, "http_status", None)
    text = str(err).lower()

    if http_status in (408, 429, 500, 502, 503, 504):
        return True
    if status in ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "ABORTED", "DEADLINE_EXCEEDED"):
        return True
    if any(s in text for s in ("rate limit", "quota", "resource exhausted", "temporarily unavailable", "retry")):
        return True
    return False


def run_individual_model(
    system_prompt: str,
    files: Dict[str, Path],
    model_name: str = "gemini-2.5-flash",
    client: genai.Client = genai.Client(),
    outfile: Optional[Path] = None,
    *,
    limiter: RateLimiter = DEFAULT_LIMITER,  # pass a shared limiter if you want
    max_retries: int = 6,
    initial_backoff: float = 1.0,
    max_backoff: float = 30.0,
    jitter: bool = True,
):
    """
    Calls Gemini with an RPM limiter (default 15/min) and exponential backoff.
    Returns the response text.
    """
    config = setup_config(system_prompt)
    contents = setup_contents(files=files, client=client)

    # Gate this call so we do not exceed 15 RPM.
    limiter.acquire()

    attempt = 0
    backoff = initial_backoff

    while True:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            text = response_to_text(response)

            if outfile:
                outfile.parent.mkdir(parents=True, exist_ok=True)
                with outfile.open("w+", encoding="utf-8") as f:
                    f.write(text)

            return text

        except Exception as e:
            attempt += 1
            if attempt > max_retries or not _is_retryable(e):
                raise

            # Exponential backoff with optional jitter
            sleep_s = random.uniform(0, backoff) if jitter else backoff
            time.sleep(sleep_s)
            backoff = min(backoff * 2, max_backoff)


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
            model_name=model,
        )
        results[alias] = resp

    return results



# Prepare for batch mode
# def upload(path, mime="image/png", client:Optional[genai.Client]=None):
#     if client is None:
#         client=genai.Client()
#     return client.files.upload(file=path, config=types.UploadFileConfig(mime_type=mime))

# generate_request = {
#     'key': key
# }




# request_key = f'r-{location_id}-{year_id}'
# def write_batch_input(location_id:int, year_id:str, images:Dict[str, Path], additional_files:Dict, config:Dict, contents:Dict):
#     request_key = f'r-{location_id}-{year_id}'
#     request_key = f'r-{location_id}-{images[]}'




# def prepare_batch_inputs(
#         inputs:Dict[int, Dict[str, Path]],
#         outfile:Path|str,
        
# ):
#     upload_imgs(location)

