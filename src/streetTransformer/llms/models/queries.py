import os
from dotenv import load_dotenv
from typing import Callable
from dataclasses import dataclass, asdict
import json
from ...config.constants import DATA_PATH

# chrome

#Uri = NewType("URI", str)
URI = str

# load_dotenv()
# os.getenv('GEMINI_API_KEY')

# Run each with FOCUS and without

DESCRIPTION = { # Basic Description of each model (for understanding purpose only)
    # Image
    'image_change_identifier'    : 'Identify change between two images focusing on given streetscape interventions (FEATURES)', 
    'image_change_locator'       : 'Identify where in the image the features are located. Run for any feature but focus on Sidewalk/Curb and Crosswalk', # Due to validation
    'image_change_describer'     : 'Describe the changes using a limited domain expertise and prompting for solely focusing on FEATURES. Use 1 sentence and then use CLIP to embed this.', # compare with document_summarizer embedding
    'image_document_linker'      : 'Which of these three documents describes the change between these two images?',
    'image_change_dater'         : 'Given an ordered set of images of the same location over time, identify when the change occured',
    # 'image_locator' -- to do better, would 
    # Document
    # 'document_change_identifier' : '', # nothing? Compare with ontology?
    #'document_change_locator'    : '', # nothing # something with the ontology
    'document_summarizer' : 'Describe the changes in the this document. Ignore geographic, government or process details - focus exclusively on streetscape changes that might', # Then use CLIP to embed and compare
    'document_image_linker'      : 'Which of these three sets of images best matches the description in this document? {FOCUS}'
    ''
}

ROLE = "You are a Transportation Engineer employed by the city tasked with analyzing changes in intersection streetscape over time."

FEATURES = ['Curb Extensions & Medians', 'Pedestrian Plazas in Previous Roadway', 'Bus Lanes', 'Bike Lanes or Paths', 'Crosswalk changes', 'Turn Lanes', 'Other Roadway Geometry Changes']
features_list =', '.join([f"'{x}'" for x in FEATURES])

IMAGE_LABELS = "The first image (Image A) is the before and and the second (Image B) is the after."

GOAL = {
    # Images
    # - Change Identifier
    'image_change_identifier' : "Your goal in this task is to look at two satellite images taken of the same location at different times and identify if there are any changes in the structural street design which may have taken place between the snapshots. Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS, # TODO: Check if too much focus.
    # - Change Locator
    'image_change_locator'    : "Your goal in this task is to look at two satellite images taken of the same location at different times and any possible locate changes in {feature} which may have taken place between the snapshots. Do NOT hesitate to say there is not significant change if you do not see them. " + IMAGE_LABELS,
    # - Change Describer
    'image_change_describer'  : "Your goal in this task is to look at two satellite images taken of the same location at different times and write a 1 sentence description of the changes that you see. " + IMAGE_LABELS,
    # - Link to Documents
    'image_document_linker'   : "Your goal in this task is to look at a set of two images of the same location at different dates, and then look at a set of three city documents that describe infrastructural change at an intersection level. Your goal is to determine which of the three documents best matches the changes that you can see in the two images. " + IMAGE_LABELS, 
    # - Change Dater
    'image_change_dater'      : "Your goal in this task is to look at an ordered set of images of the same location across different dates, and identify when the significant infrastrcutural change occured, if it did at all.",

    # Documents
    # - Change Identifer
    # - Change Describer
    'document_summarizer' : "Your goal in this task is to read this document describing the change in and write a 1 sentence description of the changes that it desribes taking place at the intersection of {crossstreets}",
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
    'image_change_dater'        : f"Limit this analysis to only capital reconstruction features including: {features_list})",

    # Document
    'document_summarizer' : f"Ignore geographic, government or process details - focus exclusively on captial reconstruction changes to the streetscape using lingo of a Transportation Engineer including: {features_list}",
    'document_image_linker'     : "Ignore any refereces to geography. You are solely looking at the changes in the streetscape."


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
    'document_image_linker'  : [('document', URI),
                                ('images', (('image_A', URI), ('image_B', URI), ('image_C', URI)))],
    'image_change_dater'     : [('image_list', list[URI])]

}

MODEL_OUTPUT = {
    # 
    'image_change_identifier' : {
        'change_detected'     : 'A boolean value if you detect significant change with regards to the above categories.',
        'features_detected'   : 'A list of the specific features you see having changed between the two photos. This list should feature exclusively the keywords included above.',
        'confidence'          : 'A confidence level (0 to 5 with 5 being the highest) of how sure you are there really is significant change relating exclusively to the features mentioned above.',
    },
    'image_change_locator'    : {
        'coordinates'         : 'A list of bounding boxes of pixel locatons within the image where the change was detected.',
        'confidence'          : 'A list of confidence measures (0 to 5 with 5 being the highest) for each bounding box in order.'
    },
    'image_change_describer'  : {
        'description'         : 'A one sentence description of the change seen',
    },
    'image_document_linker'   : {
        'document_position'   : 'the position (1st, 2nd or 3rd) of the document that best matches the set of images',
        #'document_name'       : 'the name of the document that best matches the images',
        'match_score'         : 'A score 0-5 (10 being the best) for how well this document matches the set of images'
    },
    'document_summarizer': {
        'summary'             : 'A one sentence description of the change described'
    },
    'document_image_linker'   : {
        'image_position'      : 'the position (1st, 2nd or 3rd) of the set of images that best matches the document',
        'match_score'         : 'A score 0-5 (10 being the best) for how well this set of images matches the document'
    },
    'image_change_dater'      : {
        'change_detected'     : 'A boolean value if you detect significant change with regards to the above categories.',
        'change_locations'    : """
            A list of dictionaries that identify when key change occurs. These dictionaries will include: {
                'image_id': the id  of the first image in the list showing this change 
                'features_detected':  the specific features detected in this change
                'confidence': A score 0-5 (10 being the best) for how well this document matches the set of images
            }
            """
    }
}

QUERIES = {}

# 
@dataclass
class Query:
    name: str
    role: str
    goal: str
    output: dict[str, str]
    input: dict[str, str]|None = None # TODO: Add thies
    focus: str|None            = None
    description: str|None      = None
    load_func: Callable|None   = None

    def text(self): 

        columns_joined = "\n".join(["\t- " + x for x in self.output])
        text = f"""
        Role: {self.role}

        Goal: {self.goal} {self.focus}

        Respond: {ASK.format(
            n_columns=len(self.output),
            columns_joined=columns_joined)
        }
        """
        #self.text = form
        return text



# Image Change Identifier
QUERIES['image_change_identifier'] = Query(
    name    = 'image_change_identifier', 
    role        = ROLE,
    goal        = GOAL['image_change_identifier'],
    focus       = FOCUS['image_change_identifier'],
    input       = MODEL_INPUT['image_change_identifier'],
    output      = MODEL_OUTPUT['image_change_identifier'],
    description = DESCRIPTION['image_change_identifier']
)

QUERIES['image_change_locator_sidewalk'] = Query(
    name        = 'image_change_locator_sidewalk',
    role        = ROLE,
    goal        = GOAL['image_change_locator'],
    focus       = FOCUS['image_change_locator'].format(feature='Sidewalk & Curb'),
    input       = MODEL_INPUT['image_change_locator'],
    output      = MODEL_OUTPUT['image_change_locator'],
    description = DESCRIPTION['image_change_locator']
)

QUERIES['image_change_locator_crosswalk'] = Query(
    name        = 'image_change_locator_crosswalk',
    role        = ROLE,
    goal        = GOAL['image_change_locator'],
    focus       = (FOCUS['image_change_locator']).format(feature='Crosswalks'),
    input       = MODEL_INPUT['image_change_locator'],
    output      = MODEL_OUTPUT['image_change_locator'],
    description = DESCRIPTION['image_change_locator']
)

QUERIES['image_change_describer'] = Query(
    name        = 'image_change_describer',
    role        = ROLE,
    goal        = GOAL['image_change_describer'],
    focus       = FOCUS['image_change_describer'],
    input       = MODEL_INPUT['image_change_describer'],
    output      = MODEL_OUTPUT['image_change_describer'],
    description = DESCRIPTION['image_change_describer']
)

QUERIES['image_document_linker'] = Query(
    name        = 'image_document_linker',
    role        = ROLE,
    goal        = GOAL['image_document_linker'],
    focus       = FOCUS['image_document_linker'],
    input       = MODEL_INPUT['image_document_linker'],
    output      = MODEL_OUTPUT['image_document_linker'],
    description = DESCRIPTION['image_document_linker']
)

QUERIES['image_change_dater'] = Query(
    name        = 'image_change_dater',
    role        = ROLE,
    goal        = GOAL['image_change_dater'],
    focus       = FOCUS['image_change_dater'],
    input       = MODEL_INPUT['image_change_dater'],
    output      = MODEL_OUTPUT['image_change_dater'],
    description = DESCRIPTION['image_change_dater']
)

QUERIES['document_summarizer'] = Query(
    name        = 'document_summarizer',
    role        = ROLE,
    goal        = GOAL['document_summarizer'],
    focus       = FOCUS['document_summarizer'],
    input       = MODEL_INPUT['document_summarizer'],
    output      = MODEL_OUTPUT['document_summarizer'],
    description = DESCRIPTION['document_summarizer'],
)

QUERIES['document_image_linker'] = Query(
    name        = 'document_image_linker',
    role        = ROLE,
    goal        = GOAL['document_image_linker'],
    focus       = FOCUS['document_image_linker'],
    input       = MODEL_INPUT['document_image_linker'],
    output      = MODEL_OUTPUT['document_image_linker'],
    description = DESCRIPTION['document_image_linker']
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
    MODEL_OUTPUT_FILE = DATA_PATH / 'runtime' / 'model_config' / 'queries.json'
    MODEL_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    errors=0
    with open(MODEL_OUTPUT_FILE, 'w') as f:
        f.write('[\n')
        for k, v in QUERIES.items():
            try:
                json_str = json.dumps(asdict(v), default=custom_serializer, indent=2)
                f.write(json_str + ',\n')
            except Exception as e:
                errors+= 1
                print(f'{k}-{v}-{e}')

        f.write('\n]')