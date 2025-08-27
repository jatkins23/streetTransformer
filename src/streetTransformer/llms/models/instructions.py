import os
from dotenv import load_dotenv
from string import Template
from typing import Optional, Dict
from dataclasses import dataclass

# load_dotenv()
# os.getenv('GEMINI_API_KEY')

# Run each with FOCUS and without

DESCRIPTION = { # Basic Description of each model (for understanding purpose only)
    # Image
    'image_change_identifier'    : 'Identify change between two images focusing on given streetscape interventions (FEATURES)', 
    'image_change_locator'       : 'Identify where in the image the features are located. Run for any feature but focus on Sidewalk/Curb and Crosswalk', # Due to validation
    'image_change_describer'     : 'Describe the changes using a limited domain expertise and prompting for solely focusing on FEATURES. Use 1 sentence and then use CLIP to embed this.', # compare with document_summarizer embedding
    'image_document_linker'      : 'Which of these three documents describes the change between these two images?',
    # 'image_locator' -- to do better, would 
    # Document
    # 'document_change_identifier' : '', # nothing? Compare with ontology?
    #'document_change_locator'    : '', # nothing # something with the ontology
    'document_summarizer' : 'Describe the changes in the this document. Ignore geographic, government or process details - focus exclusively on streetscape changes that might', # Then use CLIP to embed and compare
    'document_image_linker'      : 'Which of these three sets of images best matches the description in this document? {FOCUS}'
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
    'image_document_linker'   : "Your goal in this task is to look at a set of two images of the same location at different periods of time, and then look at a set of three city documents that describe infrastructural change at an intersection level. Your goal is to determine which of the three documents best matches the changes that you can see in the two images. " + IMAGE_LABELS, 

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

    # Document
    'document_summarizer' : f"Ignore geographic, government or process details - focus exclusively on captial reconstruction changes to the streetscape using lingo of a Transportation Engineer including: {features_list}",
    'document_image_linker'     : "Ignore any refereces to geography. You are solely looking at the changes in the streetscape."


}

ASK = "Please respond in a well formatted json exclusively with {n_columns} tags:\n{columns_joined}"

COLUMNS = {
    # 
    'image_change_identifier' : {
        'significant_change'  : 'A boolean value if you detect significant change with regards to the above categories.',
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
    }

}

# 
@dataclass
class Query:
    name: str
    role: str
    goal: str
    columns: Dict[str, str]
    focus: Optional[str]       = None
    description: Optional[str] = None

    def text(self): 

        columns_joined = "\n".join(["\t- " + x for x in self.columns])
        text = f"""
        Role: {self.role}

        Goal: {self.goal} {self.focus}

        Respond: {ASK.format(
            n_columns=len(self.columns),
            columns_joined=columns_joined)
        }
        """
        #self.text = form
        return text

# Image Change Identifier
image_change_identifer = Query(
    name    = 'image_change_identifier', 
    role        = ROLE,
    goal        = GOAL['image_change_identifier'],
    focus       = FOCUS['image_change_identifier'],
    columns     = COLUMNS['image_change_identifier'],
    description = DESCRIPTION['image_change_identifier']
)

image_change_locator_sidewalk = Query(
    name        = 'image_change_locator_sidewalk',
    role        = ROLE,
    goal        = GOAL['image_change_locator'],
    focus       = FOCUS['image_change_locator'].format(feature='Sidewalk & Curb'),
    columns     = COLUMNS['image_change_locator'],
    description = DESCRIPTION['image_change_locator']
)

image_change_locator_crosswalk = Query(
    name        = 'image_change_locator_crosswalk',
    role        = ROLE,
    goal        = GOAL['image_change_locator'],
    focus       = (FOCUS['image_change_locator']).format(feature='Crosswalks'),
    columns     = COLUMNS['image_change_locator'],
    description = DESCRIPTION['image_change_locator']
)

image_change_describer = Query(
    name        = 'image_change_describer',
    role        = ROLE,
    goal        = GOAL['image_change_describer'],
    focus       = FOCUS['image_change_describer'],
    columns     = COLUMNS['image_change_describer'],
    description = DESCRIPTION['image_change_describer']
)

image_document_linker = Query(
    name        = 'image_document_linker',
    role        = ROLE,
    goal        = GOAL['image_document_linker'],
    focus       = FOCUS['image_document_linker'],
    columns     = COLUMNS['image_document_linker'],
    description = DESCRIPTION['image_document_linker']
)

document_summarizer = Query(
    name        = 'document_summarizer',
    role        = ROLE,
    goal        = GOAL['document_summarizer'],
    focus       = FOCUS['document_summarizer'],
    columns     = COLUMNS['document_summarizer'],
    description = DESCRIPTION['document_summarizer'],
)

document_image_linker = Query(
    name        = 'document_image_linker',
    role        = ROLE,
    goal        = GOAL['document_image_linker'],
    focus       = FOCUS['document_image_linker'],
    columns     = COLUMNS['document_image_linker'],
    description = DESCRIPTION['document_image_linker']
)

if __name__ == '__main__':
    print('image_change_identifer: ' + image_change_identifer.text())
    print('image_change_locator_sidewalk: ' + image_change_locator_sidewalk.text())
    print('image_change_locator_crosswalk: ' + image_change_locator_crosswalk.text())
    print('image_change_describer: ' + image_change_describer.text())
    print('image_document_linker: ' + image_document_linker.text())
    print('document_summarizer: ' + document_summarizer.text())
    print('document_image_linker: ' + document_image_linker.text())
    print('image_change_dater')

    # TODO: Add 'change-dater' for image (and documents?)
    # - Change Dater\


    # image_change_dater = Query(
    #     name        = 'image_change_dater',
    #     role        = ROLE,
    #     goal        = GOAL
    # )