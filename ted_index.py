import json
import re
import time

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import tokenizer, analyzer
from elasticsearch_dsl.query import MultiMatch, Match
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
# Connect to local host server
connections.create_connection(hosts=['127.0.0.1'])

# Create elasticsearch object
es = Elasticsearch()

# Define analyzers appropriate for your data.
# You can create a custom analyzer by choosing among elasticsearch options
# or writing your own functions.
# Elasticsearch also has default analyzers that might be appropriate.
text_analyzer = analyzer("text_analyzer", tokenizer="whitespace", filter=["stop", "lowercase", "porter_stem"])

nnp_analyzer = analyzer("nnp_analyzer", tokenizer="whitespace", filter=["lowercase"])

# Define document mapping (schema) by defining a class as a subclass of Document.
# This defines fields and their properties (type and analysis applied).
# You can use existing es analyzers or use ones you define yourself as above.
class Talk(Document):
    title = Text(analyzer=text_analyzer)
    speaker = Text(analyzer=nnp_analyzer)
    transcript = Text(analyzer=text_analyzer)

    date = Text()
    duration = Integer()
    tags = Text(analyzer=nnp_analyzer)
    num_views = Integer()
    num_comments = Integer()
    link = Text()
    description = Text(analyzer=text_analyzer)

    # override the Document save method to include subclass field definitions
    def save(self, *args, **kwargs):
        return super(Talk, self).save(*args, **kwargs)

# Populate the index
def buildIndex():
    """
    buildIndex creates a new film index, deleting any existing index of
    the same name.
    It loads a json file containing the movie corpus and does bulk loading
    using a generator function.
    """

    ted_index = Index('ted_index')

    # ted_index.analyzer(my_analyzer)

    if ted_index.exists():
        ted_index.delete()  # Overwrite any previous version
    ted_index.document(Talk)
    ted_index.create()
    
    # Open the json film corpus
    # with open('test_corpus.json', 'r', encoding='utf-8') as data_file:
    # with open('test2.json', 'r', encoding='utf-8') as data_file:
    with open('TEDTalksFullCorpus.json', 'r', encoding='utf-8') as data_file:

        # load movies from json file into dictionary
        talks = json.load(data_file)
        # print(talks.__dict__)
        size = len(talks)

        docs = [ v["transcript"]+v["description"]+v["title"]+' '.join(v["tags"]) for k, v in talks.items() ]
        # d = [ ' '.join(v["tags"]) for k, v in talks.items() ]
        # d = [ v["title"] for k, v in talks.items() ]
        vect = TfidfVectorizer(min_df=1)
        tfidf = vect.fit_transform(docs)
        # tfidf = vect.fit_transform(d)
        comp = (tfidf * tfidf.T).A
        # print(comp)
        # print(comp.shape)

        for k, v in talks.items():
            # print(comp[int(k)])
            arr = comp[int(k)-1]
            rec = arr.argsort()[-5:][::-1]
            # print(np.array2string(rec[1:]))
            talks[k]["rec"] = np.array2string(rec[1:])[1:-1]
            # print(">>", talks[k]["rec"])
            # heap = [  score in comp[int(k)] ]
            # break

    def _list2str(x):
        """x is either a list or a str"""
        return ", ".join(x) if type(x) == list else x

    # Action series for bulk loading with helpers.bulk function.
    # Implemented as a generator, to return one movie with each call.
    # Note that we include the index name here.
    # The Document type is always 'doc'.
    # Every item to be indexed must have a unique key.
    def actions():
        # mid is movie id (used as key into movies dictionary)
        for talk_id in range(1, size+1):
        # for talk_id in range(size):
            yield {
            "_index": "ted_index",
            "_type": 'doc',
            "_id": talk_id,
            "title": talks[str(talk_id)]['title'],
            "speaker": talks[str(talk_id)]['speaker'],
            "transcript": talks[str(talk_id)]['transcript'],
            "date": talks[str(talk_id)]['date'],
            "duration": talks[str(talk_id)]['duration'],
            "tags": _list2str(talks[str(talk_id)]['tags']),
            "num_views": talks[str(talk_id)]['num_views'],
            "num_comments": talks[str(talk_id)]['num_comments'],
            "link": talks[str(talk_id)]['talk_link'],
            "ratings": talks[str(talk_id)]['categories'],
            "description": talks[str(talk_id)]['description'],
            "pic": talks[str(talk_id)]['thumbnails'],
            "rec": talks[str(talk_id)]['rec']
            # "y_like": talks[str(talk_id)]['YouTube_likeCount'],
            # "y_like": talks[str(talk_id)]['YouTube_dislikeCount']

            }

    helpers.bulk(es, actions()) 

# command line invocation builds index and prints the running time.
def main():
    start_time = time.time()
    buildIndex()
    print("=== Built index in %s seconds ===" % (time.time() - start_time))

if __name__ == '__main__':
    main()