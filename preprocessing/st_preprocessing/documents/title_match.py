# TODO: This code should provide an token-based mechanism for aligning (and fuzzy-matching) document titles with 

# The main function should take in a list of document titles (or maybe documents themselves) including location and year, and a set of caprecon projects 


import os
from typing import List, Optional


import numpy as np
import pandas as pd
import geopandas as gpd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def find_most_similar_titles(query_title:str, test_titles:pd.Series, top_n:Optional[int]=5) -> pd.DataFrame:
    """Finds the most similar `top_n` titles to a given `query_title` in a list of `test_titles`. 

    Args:
        query_title (str): _description_
        test_titles (pd.Series): _description_
        top_n (Optional[int], optional): _description_. Defaults to 5.

    Returns:
        pd.DataFrame: _description_
    """
                             #weights:Optional[np.ndarray]=None) -> pd.DataFrame:
    # if weights is None:
    #     weights = np.ones_like(test_titles)

    # Combine t
    all_titles = [query_title] + test_titles.fillna("").astype(str).to_list()

    # Vectorize the
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(all_titles)
    
    # Then create a similarity matrix
    similarity_scores = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1:])

    # Flatten
    similarity_vector = similarity_scores.flatten()
    
    # turn 
    similarity_df = pd.DataFrame({
        'project': test_titles,
        #'weight': weights
    })
    similarity_df['similarity'] = similarity_vector
    similarity_df = similarity_df.sort_values(by='similarity', ascending=False)

    # Get top_n
    if top_n is not None:
        similarity_df = similarity_df.head(top_n)

    return similarity_df

def align_document_title_to_project_titles():
    pass

def match_documents_to_projects(documents_df:pd.DataFrame, caprecon_gdf:gpd.GeoDataFrame):
    pass


if __name__ == '__main__':
    PROJECT_TITLES = os.listdir('../proj_data/project_documents')
    print(PROJECT_TITLES)

    split_titles = [(x.split('--')[0], '--'.join(x.split('--')[1:])) for x in PROJECT_TITLES]
    print(split_titles)

    titles = ["Deep Learning for NLP", "NLP with Deep Neural Networks", 'test two', 'test three']
    titles = [x[1] for x in split_titles]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf = vectorizer.fit_transform(titles)

    similarity_matrix = cosine_similarity(tfidf)
    print(similarity_matrix)