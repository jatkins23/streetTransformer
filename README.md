
# Street Design Evolution Analysis

## Background
Build a methodology to analyze, align and compare different modalities of documenting urban built-environment change. In New York City, we have 3 parallel methods of understanding how street-design infrastructure changes over time:
* Satellite Imagery
* Open-source City Data
* Project Documents

Each describe the same process in different ways. The goal of this project is to define a generalizable translation framework between these different documentation methods and, in doing so, build an extendable and indexable way of searching the space of street design projects.

## My High-level Questions
* Should/How do I better separate functions that are necessary once (like document scrapers, data-loading, etc) from things that run every time?
* How do I align the dashboard and package functions better?
* What are better ways of 
* Where should I move towards a more Object-Oriented approach?
* Better error handling. Better logging?
* How do I modularize the dashboard better?


## Structure

* 6 modules in `src`
    * `data_load` - Loading location geodata. 
    * `llms` - Handling interactions llm modeling.
    * `process_imagery` - Everything to do with satellite imagery (except pulling it initially).
    * `project_data` - Compiles structured, numeric data from NYC OpenData.
    * `project_documents` - Everything to deal gathering, aligning and digesting pdf projet documents.
    * `utils` - Utility functions for use in other portions
* `dashboard`: interactive dashboard for comparing t
* `scripts`: not really used anymore but should include the data pipeline itself
* `data`: Not pushed. Should be in a defined structure. I'll share my data folder and document later.

## src Modules

### `data_load`

For loading the intersections. Contains two modules, one that loads intersections using the `Intersection` change

#### To Do List
- [ ] Ensure that the LION version plays nice with `join_and_stitch`
- [ ] Expand to not-exactly inter locations
- [ ] Figure out a better way to do it with open source

### `llms`

#### Description
Contains one .py file which mainly just interacts with `ollama`. 

#### Usage
    from src.llms.run_llm_model import run_model
    run_model([model_name], [list_of_image_paths], stream=False)

Can also run it via command line. Check `src.llms.run_llm_model` source code to see options. 

**Note: need to first set up the models using [ollama](https://ollama.com/) and build each model manually using `ollama create [model_name] -f [link_to_modelfile]`

#### My Questions
* Should I move the `models` folder into a different (`assets`?) folder?
* Should I separate the different types of models (e.g. imagery_feature_tagger, document_digester) into their relevant modules rather than in an LLM dir?

#### Future Goals
- [ ] Add functions to create new models
- [ ] Add methodology to include images and documents in the training data.
- [ ] Add tuning/RAG capabilities here too?
- [ ] Add API calls here as well

### `process_imagery`

#### Goal
* take the inputs from `load_locations`, buffer them, assign them to tiles, stitch those tiles together, and save in a different location.

#### My Questions
* I've been working on reorganizing join_and_stitch into a more organized modular system but somewhat unsure where to go next.
* Should I cut each stitched location back down to a uniform size?

#### To Do List
- [x] Move to LION dataset
- [ ] Fix Naming Scheme (no |, better id system, display name)
- [ ] Streamline the intiial pipeline - build programmatic way to pull historic imagery from `tile2net` and customize the storage location and naming structure
- [ ] De-couple portions of `gather_location_imagery`. Modularize process better.
- [ ] Brighten images or otherwise better align
    - [ ] scikit_imagery?
- [ ] Confirm that the given radius works? I think its not large enough right now and leads some locations to be on the edge of the image.

### `project_data`

#### Goal
Compile various datasets from [NYC OpenData](https://opendata.cityofnewyork.us/).

[Catalog of sources](https://docs.google.com/document/d/1blmkZDJahWCfuxNTKBEAkNx_fYryT69QCzQdk90hbJ0/edit?tab=t.0)

There are three different types of datasets. 

1) *Project Data* - catalogs ongoing projects themselves. Exists at both the block and intersection level.
2) *Feature Data* - catalogs instances different types of features including implementation. These are more diverse and harder to align

    * I've begun by using 4 feature datasets: `Bike Routes`, `Bus Lanes`, `Pedestrian Plazas`, `Traffic Calming`

3) *Planimetric Data* - I haven't looked at this yet. But I think it could be very useful, though maybe harder to get time-data involved

#### To Do List
- [x] Use location_id
- [x] Align basic intersection-based data-sets
- [ ] find unified method of measuring time
- [ ] fix the aggregator function. 
- [ ] **`snapshot` function which can instantiate a version of the dataset at a given time**
- [ ] Create feature-based MVP
- [ ] Link to *Document Digester*
- [ ] Link to dashboard


### `project_documents`

#### Description
Everything to do with the PDF project documents. Currently just scrape them from the city

#### Questions
* Not sure exactly how to seaparate the pre-computation portion from the live running/digesting version. Also not sure whether the modeling would go in here or in `llms`

#### To Do
- [ ] Link Docs to `proj_data` using a fuzzy match (Jaccard similarity maybe?)
- [ ] Experiment with LLM-based document_digesters to try to get feature-tags out of the docs. (context will be important)

### `utils`

#### Description
Utility functions for use in many places.

#### Components
* `constants.py` - constants and precomputation. But also some of this exists in `.env`
* `geodata.py` - just a wrapper around from_wkt
* `image_paths.py` - this is duplicative
* `logger.py` - not yet implemented

#### Questions
- How do I better organize? How to align with dashboard global functions (in `setup.py`)

### `viz`
Was useful for basic visualziations but I've since moved to the dashboard. It does contain the code for a before/after interactive visualization that I would like to keep


## Dashboard

### Components
* `app.py` - application
* `layout` - front-end
* `callbacks` - back-end interaction
* `assets` - HTML/CSS
* `setup.py` - grabs/sets constants and imports methods from other modules.

### Usage
    ```uv run dashboard/app.py```

### Questions
* I really don't know how to better keep abstraction. Its starting to get too bloated to keep track of things. What I did with the `intersection-picker` widget, I'd like to do for everything 

### Future Goals
- [ ] rework `config`/`setup.py`
- [ ] big refactor to avoid hardcoding css, and make the layout functions more readable
- [ ] map interface. Choose from map or scrollable? Include geocoded search.
    - filter to neighborhood
- [ ] create basic compare for feature-detector projects
- [ ] display names
- [ ] Linking datasets
    - [x] Display project data for a given location [this is done in a branch but needs to be expanded]
        - make pretty
    - [ ] display project documents for a given location 
    - [ ] reorganize to allow selecting projects and then displaying imagery.
- [ ] rethink the design

## Scripts
I think all of this is superceded at this point

## Usage
Can run the image-processing module using either

    uv run src/process_imagery/join_and_stitch.py (for Downtown Brooklyn)

or, if you have the data all downloaded

    from src.process_imagery.join_and_stitch import gather_location_imagery
    gather_location_imagery('[Location]') 
