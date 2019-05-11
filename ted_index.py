import json
import re
import time

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import tokenizer, analyzer
from elasticsearch_dsl.query import MultiMatch, Match


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


            
    # "tags": _list2str(talks[str(talk_id)]['tags']),
    # "num_views": talks[str(talk_id)]['num_views'],

    # "link": talks[str(talk_id)]['link'],
    # "ratings": talks[str(talk_id)]['ratings']

    title = Text(analyzer=text_analyzer)
    speaker = Text(analyzer=nnp_analyzer)
    transcript = Text(analyzer=text_analyzer)
    date = Text()
    duration = Integer()
    tags = Text(analyzer=nnp_analyzer)
    num_views = Integer()
    num_comments = Integer()
    link = Text()
    # ratings = ?


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

    film_index = Index('ted_index')

    # film_index.analyzer(my_analyzer)

    if film_index.exists():
        film_index.delete()  # Overwrite any previous version
    film_index.document(Talk)
    film_index.create()
    
    # Open the json film corpus
    with open('test_corpus.json', 'r', encoding='utf-8') as data_file:
    # with open('ted_corpus.json', 'r', encoding='utf-8') as data_file:
        # load movies from json file into dictionary
        talks = json.load(data_file)
        size = len(talks)

    def _check_int(x):
        """x is either an int or an empty list"""
        return x if type(x) == int else 0

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

            "link": talks[str(talk_id)]['link'],
            "ratings": talks[str(talk_id)]['ratings']
 
            }

    helpers.bulk(es, actions()) 

# command line invocation builds index and prints the running time.
def main():
    start_time = time.time()
    buildIndex()
    print("=== Built index in %s seconds ===" % (time.time() - start_time))

if __name__ == '__main__':
    main()