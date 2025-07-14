import os
import requests

from typing import List, NewType
from pathlib import Path

from datetime import datetime
import pandas as pd

from bs4 import BeautifulSoup

# create URL Type for clarity
URL = NewType('URL', str)

SAVE_BASE_PATH = '../data/project_documents/'
THIS_YEAR = datetime.now().year

def gather_project_details_year(year:int, page_url:URL) -> pd.DataFrame:
    """Get list of all projects, with names and associated document links for a given year"""
    projects = [] 

    # Get all data from URL
    response = requests.get(page_url)
    response.raise_for_status()

    # Instantiate BS parser
    soup = BeautifulSoup(response.text, "html.parser")

    # Get all project divs based on tags (note: Format changed in 2014)
    if year >= 2014:
        projects = soup.find_all("div", class_="cproject")
    else:
        projects = soup.find_all("article")

    # Loop through each project div to parse
    for proj in projects:
        if isinstance(proj, dict):
            print(proj)
            break
        h3 = proj.find("h3")
        if not h3:
            continue
        project_name = h3.get_text(strip=True)

        # Find all links inside descendants with class="arr"
        arr_containers = proj.find_all(class_="arr")
        links = []
        for container in arr_containers:
            for a in container.find_all("a", href=True):
                links.append(a["href"])

        # Find the closest preceding <h2>
        section_h2 = None
        for prev in proj.find_all_previous():
            if prev.name == "h2":
                section_h2 = prev.get_text(strip=True)
                break

        # Add to the projects
        projects.append({
            "year": year,
            "borough": section_h2,
            "name": project_name,
            "document_urls": links,
            "source_url": page_url
        })
        
    return pd.DataFrame(projects)

# Download the documents for a given row of projects
def download_and_save_project_docs(project_record:pd.Series,
                                   save_base_dir:Path|str=SAVE_BASE_PATH, overwrite=False) -> None:
    """For a given project, it downloads each document associated with it and saves them in a folder"""
    # Clean ID
    proj_id = project_record.name
    proj_name = project_record['name']
    proj_doc_urls = project_record['document_urls']
    proj_name = proj_name.replace('/', '--')


    # Create a new folder for it if it doesn't exist
    proj_dirname = f'{proj_id}--{proj_name}'
    proj_dirpath = os.path.join(save_base_dir, proj_dirname)

    if os.path.exists(proj_dirpath) and not overwrite:
        raise FileExistsError(f"Directory '{proj_dirpath}' already exists!\n\tRe-run with `overwrite=True` to continue")
    
    if not os.path.exists(proj_dirpath):
        os.mkdir(proj_dirpath)

    # Loop through all 
    i = 0
    while i < len(proj_doc_urls):
        document_name = f"{proj_id}--{i}--{proj_doc_urls[i].split('/')[-1]}"
        
        # download the documents
        try:
            r = requests.get(proj_doc_urls[i])
            r.raise_for_status()
            with open(os.path.join(proj_dirpath, document_name), 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f'\tFailed to download {proj_id}: {proj_doc_urls[i]}: {e}')

        i=i+1

    print(f"Proj: {proj_id}: {i} Doc{'s' if i != 1 else ''} Written!")

def gather_project_details_all_years(years:List[int], url_template:URL) -> pd.DataFrame:
    """Calls `gather_project_details_year` for every year provided, combines and runs some checks"""
    if (min(years) < 2007) | (max(years) > THIS_YEAR):
        raise ValueError(f"Years provided are not all within 2007-{datetime.now().year} range")
    
    # Receptacle for each year
    years_dict = {}

    for year in years:
        # Create url
        final_part = f'projects-{year}' if year != THIS_YEAR else 'current-projects'
        url = URL_TEMPLATE.format(final_part=final_part)
        print(url)

        try:
            year_data = gather_project_details_year(year, url)
            years_dict[str(year)] = year_data
            print(f'\t{year}: {year_data.shape}!')
        except Exception as e:
            print(f'\t{year}: {e}')

    # Combine together    
    projects_df = pd.concat(years_dict, ignore_index=True) 
    
    # Sanity Checks
    n_projects = projects_df.shape[0] # 941 projects
    n_docs = projects_df['document_links'].explode().shape[0] # 1,813 documents
    print(f'Found {n_projects} projects\n\tand {n_docs} documents')

    return projects_df

    

if __name__ == '__main__':
    URL_TEMPLATE = "https://www.nyc.gov/html/dot/html/about/{final_part}.shtml"        

    # Scrape all years
    #years_to_pull = list(range(2007, THIS_YEAR+1))
    years_to_pull = [2007]
    projects_df = gather_project_details_all_years(years_to_pull, URL_TEMPLATE)

    # Save projects df
    projects_df.to_csv('../data/project_documents/projects_df.csv')

    # Now download the docs for each and save
    projects_df.apply(download_and_save_project_docs, axis=1)