import os
from dotenv import load_dotenv
from typing import Callable, Any
from dataclasses import dataclass, asdict
from dataclasses_jsonschema import JsonSchemaMixin 
import json
from ...config.constants import DATA_PATH

# chrome

#Uri = NewType("URI", str)
URI = str
YEARS = ['2006', '2012' ,'2014', '2018', '2024']

# load_dotenv()
# os.getenv('GEMINI_API_KEY')

# Run each with FOCUS and without

DESCRIPTION = { # Basic Description of each model (for understanding purpose only)
    # Image
    'image_change_identifier'    : 'Identify change between two images focusing on given streetscape interventions (FEATURES)', 
    'sidebyside_change_identifier': 'Identify change between two sets of images (sets include satellite and rasterized segmentation) focusing on given streetscape interventions (FEATURES)', 
    'image_change_locator'       : 'Identify where in the image the features are located. Run for any feature but focus on Sidewalk/Curb and Crosswalk', # Due to validation
    'image_change_describer'     : 'Describe the changes using a limited domain expertise and prompting for solely focusing on FEATURES. Use 1 sentence and then use CLIP to embed this.', # compare with document_summarizer embedding
    'sidebyside_change_describer': 'Describe the changes using a limited domain expertise and prompting for solely focusing on FEATURES. Use 1 sentence and then use CLIP to embed this. (includes segmentation)', # compare with document_summarizer embedding
    'image_document_linker'      : 'Which of these three documents describes the change between these two images?',
    'image_change_dater'         : 'Given an ordered set of images of the same location over time, identify when the change occured',
    'sidebyside_change_dater'         : 'Given an ordered set of image, segmentation pairs of the same location over time, identify when the change occured',
    # 'image_locator' -- to do better, would 
    # Document
    # 'document_change_identifier' : '', # nothing? Compare with ontology?
    #'document_change_locator'    : '', # nothing # something with the ontology
    'document_summarizer'        : 'Describe the changes in the this document. Ignore geographic details, street names, references to agencies - focus exclusively on streetscape changes the documents describe in text and images', # Then use CLIP to embed and compare
    'document_image_linker'      : 'Which of these three sets of images best matches the description in this document? {FOCUS}',
    'document_feature_tagger'    : 'Obtain a feature list from a document (using LLM)'
}

ROLE = "You are a Transportation Engineer employed by the city tasked with analyzing changes in intersection streetscape over time."

#FEATURES = ['Curb Extensions & Medians', 'Pedestrian Plazas in Previous Roadway', 'Bus Lanes', 'Bike Lanes or Paths', 'Crosswalk changes', 'Turn Lanes', 'Other Roadway Geometry Changes']
FEATURES = ['Curb Extensions', 'New or Expanded Median/Pedestrian Refuge Island', 'Bike Enhancement', 'Median Tip Extension', 'Raised Median', 'Lane Removal or Road Narrowing', 'Bus Bulb', 'Shared Street', 'Sidewalk Redesign']
features_list =', '.join([f"'{x}'" for x in FEATURES])

IMAGE_LABELS = "The first image is the before and and the second is the after."

SEGMENTATION_ADDITION = 'For your ease, we have provided a graphical segmentation of the infrastructure network for each image. They are positioned to the left of each image.'

GOAL = {
    # Images
    # - Change Identifier
    'image_change_identifier'      : "Your goal is to look at two satellite images taken of the same location at different times and identify if there are any changes in the structural street design which may have taken place between the snapshots. Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS, # TODO: Check if too much focus.
    'sidebyside_change_identifier' : "Your goal is to look at two set of images that represent the same location at different times and identify if there are any changes in the structural street design which may have taken place between the snapshots. Each image set contains a satellite image (left), and a digital segmentation of the satelite image (right) segmented into different infrastructual feature classes represented as colors). Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS,
    # - Change Locator
    'image_change_locator'         : "Your goal is to look at two satellite images taken of the same location at different times and locate any possible changes in {feature} which may have taken place between the snapshots. Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS,
    # - Change Describer
    'image_change_describer'       : "Your goal is to look at two satellite images taken of the same location at different times and write a 1 sentence description of the changes that you see. " + IMAGE_LABELS,
    'sidebyside_change_describer'  : "Your goal is to look at two set of images that represent the same location at different times and write a 1 sentence description of the changes that you see. Each image set contains a satellite image (left), and a digital segmentation of the satelite image (right) segmented into different infrastructual feature classes represented as colors)" + IMAGE_LABELS,
    # - Link to Documents
    'image_document_linker'        : "Your task is to look at two satellite images taken of the same location at different dates, and then look at a set of three city documents that describe infrastructural change at an intersection level. Your goal is to determine which of the three documents best matches the changes that you can see between the two images StreetScape Interventions." + IMAGE_LABELS, 
    'sidebyside_document_linker'   : "Your goal is to look at a set of two images of the same location at different dates, and then look at a set of three city documents that describe infrastructural change at an intersection level. Your goal is to determine which of the three documents best matches the changes that you can see between the two images related to StreetScape Interventions." + IMAGE_LABELS, 
    # - Change Dater
    'image_change_dater'           : "Your task is to look at an ordered set of images of the same location across different years. The image file's name represents the years. Your goal is to identify in which year image the infrastrcutural change occured, if it did at all.",
    'sidebyside_change_dater'      : "Your goal is to look at an ordered set of sets of images that represent the same location at different times and identify if there are any changes in the structural street design which may have taken place between the snapshots. Each image set contains a satellite image (left), and a digital segmentation of the satelite image (right) segmented into different infrastructual feature classes represented as colors). Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS,

    # Documents
    # - Change Identifer
    # - Change Describer
    'document_feature_tagger'     : "Your goal in this task is to read this document describing change made at a city intersection and identifer specific streetscape infrastructure interventions that took place. ",
    'document_summarizer'         : "Your goal in this task is to read this document describing change made at a city intersection and write a 1 sentence description of the changes that it desribes taking place. ",
    'document_image_linker'      : "Your goal in this task is to read this document and look at 3 different set of two images. These image sets each represent the same location at a different"
    ""
    " location at different periods of time, and then look at a set of three city documents that describe infrastructural change at an intersection level. Your goal is to determine which of the three documents best matches the changes that you can see in the two images."
}

FOCUS = {
    # Image
    # - Change Identifier
    'image_change_identifier'   : f"Limit this analysis to only capital reconstruction features including: {features_list})",
    # - Change Locator
    'image_change_locator'      : "Focus exclusively on {feature} and ignore other changes",
    # - Change Describer
    'image_change_describer'    : f"Limit this analysis to only capital reconstruction features including: {features_list})",
    # - Link to Documents
    'image_document_linker'     : "", # Not necessary?
    # - Change Dater

    # Document
    'document_feature_tagger'   : f"Ignore geographic details, street names, references to agencies - focus exclusively on captial reconstruction changes to the streetscape.",
    'document_summarizer'       : f"Ignore geographic details, street names, references to agencies - focus exclusively on captial reconstruction changes to the streetscape using lingo of a Transportation Engineer including: {features_list}",
    'document_image_linker'     : "Ignore any refereces to geography. You are solely looking at the changes in the streetscape.",
    'image_change_dater'        : f"Limit this analysis to only capital reconstruction features including: {features_list})."
}

ASK = "Please respond in a well formatted json exclusively with {n_columns} tags:\n{columns_joined}"

MODEL_INPUT = {
    # location_id, start_year, end_year
    'image_change_identifier': [('start_image', URI), ('end_image', URI)],
    'image_change_locator'   : [('start_image', URI), ('end_image', URI), ('feature', str)],
    'image_change_describer' : [('start_image', URI), ('end_image', URI)],
    'image_document_linker'  : ['start_image', URI, ('end_image', URI), 
                                ('documents', (('document_A', URI), ('document_B', URI), ('document_C', URI)))],
    'document_summarizer'    : [('document', URI)],
    'document_feature_tagger': [('document', URI)],
    'document_image_linker'  : [('document', URI),
                                ('images', (('image_A', URI), ('image_B', URI), ('image_C', URI)))],
    'image_change_dater'     : [('image_list', list[URI])]
}

@dataclass
class QueryOutput(JsonSchemaMixin):
    pass

@dataclass
class ChangeIdentifierOutput(QueryOutput):
    change_detected: bool
    confidence: int
    features: list[str]

@dataclass
class LocatorOutput(QueryOutput):
    coordinates: list[float]
    confidence: int

@dataclass
class DescriberOutput(QueryOutput):
    description: str

@dataclass
class LinkerOutput(QueryOutput):
    match_label: str
    match_score: int

@dataclass
class DaterOutput(QueryOutput):
    change_detected: bool
    change_locations: list[dict[str, Any]]


@dataclass
class TaggerOutput(QueryOutput):
    features: list[str]

MODEL_OUTPUT = {
    # 
    'image_change_identifier' : {
        'change_detected'     : 'A boolean value if you detect significant change with regards to the above categories. Respond exclusively with True or False.',
        'features_detected'   : 'A list of the specific features you see having changed between the two photos. This list should feature exclusively the keywords included above.',
        'confidence'          : 'An integer confidence level (0 to 5 with 5 being the highest) of how sure you are there really is significant change relating exclusively to the features mentioned above.',
    },
    'sidebyside_change_identifier' : {
        'change_detected'     : 'A boolean value if you detect significant change with regards to the above categories. Respond exclusively with True or False.',
        'features_detected'   : 'A list of the specific features you see having changed between the two sets of images. This list should feature exclusively the keywords included above.',
        'confidence'          : 'An integer confidence level (0 to 5 with 5 being the highest) of how sure you are there really is significant change relating exclusively to the features mentioned above.',
    },
    'image_change_locator'    : {
        'coordinates'         : 'A set of pixel locations within the image where the change was detected. If no change detected, return an empty list.',
        'confidence'          : 'An integer confidence measure (0 to 5 with 5 being the highest) the bounding box.'
    },
    'image_change_describer'  : {
        'description'         : 'A one sentence description of the change seen.',
    },
    'image_document_linker'   : {
        'document_label'      : 'The label of the document (Document A, B, or C) that best matches the set of images. Respond exclusively with A, B or C',
        #'document_name'       : 'the name of the document that best matches the images',
        'match_score'         : 'An integer score 0-5 (5 being the best) for how well this document matches the set of images'
    },
    'document_feature_tagger': {
        'features'            : f'A list of the specific features you see having changed between the two sets of images. This list should feature exclusively the keywords in [{features_list}].',
    },
    'document_summarizer': {
        'summary'             : 'A one sentence description of the change described.'
    },
    'document_image_linker'   : {
        'image_label'         : 'The label of the set of images (Image A, B, or C) that best matches the document. Respond exclusively with A, B or C', # TODO
        'match_score'         : 'A score 0-5 (10 being the best) for how well this set of images matches the document'
    },
    'image_change_dater'      : {
        'change_detected'     : 'A boolean value if you detect significant change with regards to the above categories. Respond exclusively with True or False',
        'change_locations'    : f"A list of image IDs that you believe show a significant change from the image before. Please only respond with only the labels of the image files provided."
    }
}

QUERIES = {}

# 
@dataclass
class Query:
    name: str
    role: str
    goal: str
    output_prompt: dict[str, str]
    output_schema: Callable # QueryOutput
    input: dict[str, str]|None = None # TODO: Add thies
    focus: str|None            = None
    description: str|None      = None
    load_func: Callable|None   = None

    def text(self): 

        columns_joined = "\n".join([f"\t- {k}: {v}" for k, v in self.output_prompt.items()])
        text = f"""
        Role: {self.role}

        Goal: {self.goal} {self.focus}

        Respond: {ASK.format(
            n_columns=len(self.output_prompt),
            columns_joined=columns_joined)
        }
        """
        #self.text = form
        return text

# Image Change Identifier
QUERIES['image_change_identifier'] = Query(
    name          = 'image_change_identifier', 
    role          = ROLE,
    goal          = GOAL['image_change_identifier'],
    focus         = FOCUS['image_change_identifier'],
    input         = MODEL_INPUT['image_change_identifier'],
    output_prompt = MODEL_OUTPUT['image_change_identifier'],
    output_schema = ChangeIdentifierOutput,
    description   = DESCRIPTION['image_change_identifier']
)

QUERIES['sidebyside_change_identifier'] = Query(
    name          = 'sidebyside_change_identifier', 
    role          = ROLE,
    goal          = GOAL['image_change_identifier'],
    focus         = FOCUS['image_change_identifier'],
    input         = MODEL_INPUT['image_change_identifier'],
    output_prompt = MODEL_OUTPUT['sidebyside_change_identifier'],
    output_schema = ChangeIdentifierOutput,
    description   = DESCRIPTION['image_change_identifier']
)


QUERIES['image_change_locator_sidewalk'] = Query(
    name          = 'image_change_locator_sidewalk',
    role          = ROLE,
    goal          = GOAL['image_change_locator'],
    focus         = FOCUS['image_change_locator'].format(feature='Sidewalk & Curb'),
    input         = MODEL_INPUT['image_change_locator'],
    output_prompt = MODEL_OUTPUT['image_change_locator'],
    output_schema = LocatorOutput,
    description   = DESCRIPTION['image_change_locator']
)

QUERIES['image_change_locator_crosswalk'] = Query(
    name          = 'image_change_locator_crosswalk',
    role          = ROLE,
    goal          = GOAL['image_change_locator'],
    focus         = (FOCUS['image_change_locator']).format(feature='Crosswalks'),
    input         = MODEL_INPUT['image_change_locator'],
    output_prompt = MODEL_OUTPUT['image_change_locator'],
    output_schema = LocatorOutput,
    description   = DESCRIPTION['image_change_locator']
)

QUERIES['image_change_describer'] = Query(
    name          = 'image_change_describer',
    role          = ROLE,
    goal          = GOAL['image_change_describer'],
    focus         = FOCUS['image_change_describer'],
    input         = MODEL_INPUT['image_change_describer'],
    output_prompt = MODEL_OUTPUT['image_change_describer'],
    output_schema = DescriberOutput,
    description   = DESCRIPTION['image_change_describer']
)

QUERIES['sidebyside_change_describer'] = Query(
    name          = 'sidebyside_change_describer',
    role          = ROLE,
    goal          = GOAL['sidebyside_change_describer'],
    focus         = FOCUS['image_change_describer'],
    input         = MODEL_INPUT['image_change_describer'],
    output_prompt = MODEL_OUTPUT['image_change_describer'],
    output_schema = DescriberOutput,
    description   = DESCRIPTION['sidebyside_change_describer']
)


QUERIES['image_document_linker'] = Query(
    name          = 'image_document_linker',
    role          = ROLE,
    goal          = GOAL['image_document_linker'],
    focus         = FOCUS['image_document_linker'],
    input         = MODEL_INPUT['image_document_linker'],
    output_prompt = MODEL_OUTPUT['image_document_linker'],
    output_schema = LinkerOutput,
    description   = DESCRIPTION['image_document_linker']
)

QUERIES['image_change_dater'] = Query(
    name          = 'image_change_dater',
    role          = ROLE,
    goal          = GOAL['image_change_dater'],
    focus         = FOCUS['image_change_dater'],
    input         = MODEL_INPUT['image_change_dater'],
    output_prompt = MODEL_OUTPUT['image_change_dater'],
    output_schema = DaterOutput,
    description   = DESCRIPTION['image_change_dater']
)

QUERIES['sidebyside_change_dater'] = Query(
    name          = 'sidebyside_change_dater',
    role          = ROLE,
    goal          = GOAL['sidebyside_change_dater'],
    focus         = FOCUS['image_change_dater'],
    input         = MODEL_INPUT['image_change_dater'],
    output_prompt = MODEL_OUTPUT['image_change_dater'],
    output_schema = DaterOutput,
    description   = DESCRIPTION['sidebyside_change_dater']
)

QUERIES['document_summarizer'] = Query(
    name          = 'document_summarizer',
    role          = ROLE,
    goal          = GOAL['document_summarizer'],
    focus         = FOCUS['document_summarizer'],
    input         = MODEL_INPUT['document_summarizer'],
    output_prompt = MODEL_OUTPUT['document_summarizer'],
    output_schema = DescriberOutput,
    description   = DESCRIPTION['document_summarizer'],
)

QUERIES['document_image_linker'] = Query(
    name          = 'document_image_linker',
    role          = ROLE,
    goal          = GOAL['document_image_linker'],
    focus         = FOCUS['document_image_linker'],
    input         = MODEL_INPUT['document_image_linker'],
    output_prompt = MODEL_OUTPUT['document_image_linker'],
    output_schema = LinkerOutput,
    description   = DESCRIPTION['document_image_linker']
)

QUERIES['document_feature_tagger'] = Query(
    name          = 'document_feature_tagger',
    role          = ROLE,
    goal          = GOAL['document_feature_tagger'],
    focus         = FOCUS['document_feature_tagger'],
    input         = MODEL_INPUT['document_feature_tagger'],
    output_prompt = MODEL_OUTPUT['document_feature_tagger'],
    output_schema = LinkerOutput,
    description   = DESCRIPTION['document_feature_tagger']
)

QUERIES['test'] = Query(
    name          = 'test_query',
    role          = '',
    goal          = 'Please describe the input in 10 words',
    focus         = '',
    input         = {'': ''},
    output_prompt = {'': ''},
    output_schema = DescriberOutput,
    description   = 'Test to see what is the image'
)

from dataclasses import dataclass, asdict
from typing import Any, get_origin, get_args, List, Dict, Optional, Union
import json

# --- Helpers ---
def type_to_str(tp: Any) -> str:
    return str(tp)

def str_to_type(s: str) -> Any:
    # Very simple parser: uses eval inside typing's namespace
    import typing, builtins
    ns = {**typing.__dict__, **builtins.__dict__}
    return eval(s, ns)

def custom_serializer(obj):
    # Handle typing objects and bare Python types
    if isinstance(obj, type) or "typing." in str(obj) or "[" in str(obj):
        return type_to_str(obj)
    raise TypeError(f"{obj} is not JSON serializable")


if __name__ == '__main__':
    for name, q in QUERIES.items():
        print(name)
        print(q.text())