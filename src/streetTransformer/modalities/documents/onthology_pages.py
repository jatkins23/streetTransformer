import os
import re
import logging
import duckdb
import fitz  # PyMuPDF
import trafilatura
from pathlib import Path
from rdflib import Graph, Literal, RDF, URIRef, Namespace, XSD
import contextlib
import pandas as pd
import geopandas as gpd
from argparse import ArgumentParser
import tqdm



from streettransformer.config.constants import UNIVERSES_PATH, DATA_PATH

DATA_DIR = Path("dot_docs"); DATA_DIR.mkdir(exist_ok=True)
DB_PATH = "dot_interventions2.duckdb"
ONTOLOGY_FILE = "nycdot_extracted_ontology.ttl"
INTERVENTIONS_DICT = {
    
    'Pedestrian-related': [
        "pedestrian plaza", "curb extension", "refuge island", "median",
        "leading pedestrian interval", "exclusive pedestrian phase", "daylighting",
        "crosswalk visibility improvement", "pedestrian wayfinding signage"
    ],

    'bicycle-related': [
        "protected bike lane", "conventional bike lane", "bike boulevard",
        "offset crossing", "bike signal", "bike box"
    ],
    
    'bus & transit': [
        "bus boarding island", "bus rapid transit", "queue jump lane",
        "bus lane enforcement camera"
    ],
    
    'traffic and signal control': [

        "traffic calming", "one-way conversion", "signal timing modification",
        "road diet", "left-turn calming", "roadway geometry change",
        "Barnes Dance", "turn restriction"
    ],

    'curb management': [
        "loading zone", "parking regulation change", "placard reform",
        "shared curb management zone"
    ],
    
    'vision zero': [ # https://data.cityofnewyork.us/Transportation/Serious-Injury-Response-Tracking-Analysis-Program-/xeqp-qz8h/about_data
        "speed camera", "red light camera", "weigh-in-motion enforcement",
        "SIRTA crash analysis", "automated enforcement"
    ],

    'mobility programs': [
        "bike share", "e-scooter share", "open streets", "safe routes to school",
    ],

    'streetscape and design': [
        "greenway connector", "stormwater bioswale", "tree pit",
        "public seating", "street furniture redesign", "art installation",
    ],
    
    'lighting and safety': [
        "led street lighting", "vision zero signage", "pedestrian-scale lighting"
    ]
}


logging.basicConfig(level=logging.INFO)
logging.getLogger("pdfminer").setLevel(logging.ERROR)


con = duckdb.connect(DB_PATH)
con.execute("""
CREATE TABLE IF NOT EXISTS interventions (
    proj_id INTEGER,
    doc_id TEXT,
    title TEXT,
    path TEXT,
    intervention_category TEXT,
    intervention TEXT,
    sentence TEXT,
    page_number INTEGER
);
""")

# Check if doc_id was already processed
def is_doc_processed(doc_id):
    return con.execute("SELECT COUNT(*) FROM interventions WHERE doc_id = ?", (doc_id,)).fetchone()[0] > 0

def extract_text_with_pages(file_path):
    pages = []
    if file_path.suffix.lower() == ".pdf": 
        with contextlib.redirect_stderr(open(os.devnull, "w")):
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                pages.append((i + 1, page.get_text()))
    elif file_path.suffix.lower() in ['.html', '.htm']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        text = trafilatura.extract(html)
        pages.append((1, text))
    return pages


def extract_intervention_mentions(
        pages,
        proj_id:int,
        doc_id:str,
        path:str
):
    results = []
    for page_num, text in pages:
        for sentence in re.split(r'(?<=[.!?])\s+', text)[0:1]:
            for category, terms in INTERVENTIONS_DICT.items():
                for term in terms:
                    pattern = re.escape(term)
                    if re.search(rf"\b{pattern}\b", sentence, re.IGNORECASE):
                        results.append((proj_id, doc_id, category, term.lower(), sentence.strip(), path, page_num))
    return results

def build_ontology(rows):
    g = Graph()
    DOT = Namespace("http://nyc.gov/dot#")
    g.bind("dot", DOT)

    for proj_id, doc_id, intervention_category, intervention, sentence, path, page_number in rows:
        iri = URIRef(f"http://nyc.gov/dot/doc/{doc_id}#{intervention.replace(' ', '_')}_p{page_number}")
        g.add((iri, RDF.type, DOT.Intervention))
        g.add((iri, DOT.label, Literal(intervention_category, datatype=XSD.string)))
        g.add((iri, DOT.label, Literal(intervention, datatype=XSD.string)))
        g.add((iri, DOT.exampleSentence, Literal(sentence, datatype=XSD.string)))
        g.add((iri, DOT.pageNumber, Literal(page_number, datatype=XSD.integer)))
        g.add((iri, DOT.sourcePATH, Literal(path, datatype=XSD.anyURI)))

    g.serialize(destination=ONTOLOGY_FILE, format='turtle')
    #print(f"Ontology saved to {ONTOLOGY_FILE}")



def run_pipeline(documents_gdf:pd.DataFrame|gpd.GeoDataFrame):
    # Gather documents
    all_mentions = []

    # Loop through documents
    for row in tqdm.tqdm(documents_gdf.itertuples(), total=documents_gdf.shape[0]):
        # Download: TODO: just need to get file_name
        relative_paths = row.relative_paths
        for idx in range(len(relative_paths)):
            abs_path = DATA_PATH / str(relative_paths[idx])
            if not abs_path.exists():
                continue

            doc_id = f'{row.project_id}--{idx}'

            # Check if already processed (for cacheing, I think?)
            if is_doc_processed(doc_id):
                logging.info(f"Skipping already processed document: {doc_id}")
                continue

            # Get text from pages
            pages = extract_text_with_pages(abs_path)
            if not any(text for _, text in pages):
                logging.warning(f"No extractable text in: {doc_id}")
                continue
            mentions = extract_intervention_mentions(pages, proj_id=int(row.project_id), doc_id=doc_id, path=str(relative_paths[idx]))
            all_mentions.extend(mentions)
        
        if all_mentions:
            # Write to the duckdb
            con.executemany("INSERT INTO interventions (proj_id, doc_id, intervention_category, intervention, sentence, path, page_number) VALUES (?, ?, ?, ?, ?, ?, ?);", all_mentions)
            build_ontology(all_mentions)

#just so I can sanity check
def export_anthology(outfile="intervention_anthology.txt"):
    rows = con.execute("""
        SELECT DISTINCT intervention, COUNT(*) as freq FROM interventions
        GROUP BY intervention ORDER BY freq DESC;
    """).fetchall()
    with open(outfile, 'w') as f:
        for intv, freq in rows:
            f.write(f"### {intv.upper()} ({freq} mentions)\n\n")
            sentences = con.execute(
                "SELECT sentence, path, page_number FROM interventions WHERE intervention = ? LIMIT 10;",
                (intv,)).fetchall()
            for s, u, p in sentences:
                f.write(f"- Page {p}: {s} [source]({u})\n")
            f.write("\n")

if __name__ == '__main__':
    # parser = ArgumentParser()
    # parser.add_argument('universe_name', type=str, default='caprecon_control5k', required=False)
    # args = parser.parse_args()

    #documents_gdf_path =  UNIVERSES_PATH / args.universe_name / 'documents.parquet'
    documents_gdf_path =  UNIVERSES_PATH / 'caprecon_control5k' / 'documents.parquet'
    docs_gdf = gpd.read_parquet(documents_gdf_path)
    
    run_pipeline(docs_gdf)
    outfile = UNIVERSES_PATH.parent / 'results' / 'caprecon_control5k' / 'intervention_anthology.txt'
    outfile.parent.mkdir(parents=True, exist_ok=True)
    export_anthology(outfile = str(outfile))
    rows = con.execute("""
        SELECT DISTINCT intervention, COUNT(*) as freq FROM interventions
        GROUP BY intervention ORDER BY freq DESC;
    """).fetchall()

    #print("\n".join(res))
    print('\n'.join([str(r) for r in rows]))

