import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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