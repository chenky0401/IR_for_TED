"""
This module implements a (partial, sample) query interface for elasticsearch movie search. 
You will need to rewrite and expand sections to support the types of queries over the fields in your UI.

Documentation for elasticsearch query DSL:
https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html

For python version of DSL:
https://elasticsearch-dsl.readthedocs.io/en/latest/

Search DSL:
https://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html
"""

import re
from flask import *
from ted_index import Talk
from pprint import pprint
from elasticsearch_dsl import Q
from elasticsearch_dsl.utils import AttrList
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

app = Flask(__name__)

# Initialize global variables for rendering page
# Free text, speaker, tags(list), duration(list?), 

# ranking(list: relevance, popularity(num_views)), subtitle language(list)

tmp_main = ""
tmp_speaker = ""
tmp_min = ""
tmp_max = ""
    
gresults = {}

# display query page
@app.route("/")
def search():
    return render_template('query.html')

# display results page for first set of results and "next" sets.
@app.route("/results", defaults={'page': 1}, methods=['GET','POST'])
@app.route("/results/<page>", methods=['GET','POST'])
def results(page):
    global tmp_main, tmp_speaker, tmp_duration
    global gresults

    global phrase_q, rest_text_q
    global is_disjunct_search
    global stopwords 

    # https://www.elastic.co/guide/en/elasticsearch/guide/current/stopwords.html
    stopwords = set(["a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in",
                 "into", "is", "it", "no", "not", "of", "on", "or", "such", "that", "the", "their",
                 "then", "there", "these", "they", "this", "to", "was", "will", "with"])


    # convert the <page> parameter in url to integer.
    if type(page) is not int:
        page = int(page.encode('utf-8'))    
    # if the method of request is post (for initial query), store query in local global variables
    # if the method of request is get (for "next" results), extract query contents from client's global variables  
    if request.method == 'POST':

        main_q = request.form['query']+" "
        speaker_q = request.form['speaker'].strip()
        duration_q = request.form['duration'].strip()

        print("71 m:%s sp:%s dur:%s" % (main_q, speaker_q, duration_q))

        # if duration_q == "0":
        #     mintime, maxtime = 0, 99999
        # elif duration_q == "1":
        #     mintime, maxtime = 0, 5
        # elif duration_q == "2":
        #     mintime, maxtime = 5, 10
        # elif duration_q == "3":
        #     mintime, maxtime = 10, 20
        # else:
        #     mintime, maxtime = 20, 99999


        # mintime_q = request.form['mintime'].strip()
        # mintime = 0 if len(mintime_q) == 0 else int(mintime_q)
        # maxtime_q = request.form['maxtime'].strip()
        # maxtime = 99999 if len(mintime_q) == 0 else int(maxtime_q)


        # if len(mintime_q) is 0:
        #     mintime = 0
        # else:
        #     mintime = int(mintime_q)
        # maxtime_q = request.form['maxtime'].strip()
        # if len(maxtime_q) is 0:
        #     maxtime = 99999
        # else: 
        #     maxtime = int(maxtime_q)

        # update global variable template data
        tmp_main = main_q
        tmp_speaker = speaker_q
        tmp_duration = duration_q

        # tmp_min = mintime
        # tmp_max = maxtime
    else:
        # use the current values stored in global variables.
        main_q = tmp_main
        speaker_q = tmp_speaker
        duration_q = tmp_duration

    if duration_q == "0":
        mintime, maxtime = 0, 99999
    elif duration_q == "1":
        mintime, maxtime = 0, 5
    elif duration_q == "2":
        mintime, maxtime = 5, 10
    elif duration_q == "3":
        mintime, maxtime = 10, 20
    else:
        mintime, maxtime = 20, 99999
        # mintime = tmp_min
        # mintime_q = tmp_min if tmp_min > 0 else ""
        # maxtime = tmp_max
        # maxtime_q = tmp_max if tmp_max < 99999 else ""



        # if tmp_min > 0:
        #     mintime_q = tmp_min
        # else:
        #     mintime_q = ""
        # maxtime = tmp_max
        # if tmp_max < 99999:
        #     maxtime_q = tmp_max
        # else:
        #     maxtime_q = ""
    # print("140 min: %d max: %d" %(mintime, maxtime))
    # store query values to display in search boxes in UI
    shows = {}
    shows['query'] = main_q
    shows['speaker'] = speaker_q
    shows['duration'] = duration_q
    # shows['maxtime'] = maxtime_q
    # shows['mintime'] = mintime_q
    

    # Create a search object to query our index 
    search = Search(index='ted_index')

    # Build up your elasticsearch query in piecemeal fashion based on the user's parameters passed in.
    # The search API is "chainable".
    # Each call to search.query method adds criteria to our growing elasticsearch query.
    # You will change this section based on how you want to process the query data input into your interface.
        
    # search for runtime using a range query
    s = search.query('range', duration={'gte':mintime, 'lte':maxtime})
    # print(160, s.execute())
    
    # search for matching stars
    # You should support multiple values (list)
    s = s.query('match', speaker=speaker_q) if len(speaker_q) > 0 else s
    # print(166, s.execute())
    # s = s.query('match', starring=star_q) if len(star_q) > 0 else s
    # s = s.query('match', language=lang_q) if len(lang_q) > 0 else s
    # s = s.query('match', country=ctry_q) if len(ctry_q) > 0 else s
    # s = s.query('match', director=dir_q) if len(dir_q) > 0 else s
    # s = s.query('match', location=loc_q) if len(loc_q) > 0 else s
    # s = s.query('match', time=time_q) if len(time_q) > 0 else s
    # s = s.query('match', categories=cat_q) if len(cat_q) > 0 else s

    s_copy = s
    phrase_q, rest_text_q = [], []

    # Conjunctive search over multiple fields (title and text) using the main_q passed in
    if len(main_q) > 0:
        has_phrase = True if main_q.count('"') > 1 else False
        if has_phrase:
            for q in main_q.split('"'):
                if len(q) > 0:
                    if q[-1] != " ":
                        phrase_q.append(q)
                    else:
                        q = q.strip()
                        # print(">>>"+q.strip()+"<<<")
                        if q:
                            rest_text_q.append(q)

            for ph_q in phrase_q:
                s = s.query('multi_match', query=ph_q, type='phrase', fields=['title^2', 'transcript'], operator='and')
                # print(104, s.execute())

            if len(rest_text_q) != 0:
                # print(rest_text_q)
                rest_text_q = ' '.join(rest_text_q)
                s = s.query('multi_match', query=rest_text_q, type='cross_fields', fields=['title^2', 'transcript'], operator='and')
                # print(200, s.execute())

        else:
            s = s.query('multi_match', query=main_q, type='cross_fields', fields=['title^2', 'transcript'], operator='and')
            # print(200, s.execute())

    # highlight
    s = highlight(s)

    # determine the subset of results to display (based on current <page> value)
    start = 0 + (page-1)*10
    end = 10 + (page-1)*10
    
    # execute search and return results in specified range.
    response = s[start:end].execute()
    # print(response)

    is_disjunct_search = True if response.hits.total == 0 else False

    if is_disjunct_search:
        s = s_copy
        if has_phrase:
            q = Q('match_all')
            if len(rest_text_q) != 0:
                # print(rest_text_q)
                q = Q('multi_match', query=rest_text_q, type='cross_fields', fields=['title^2', 'transcript'], operator='or')

            for ph_q in phrase_q:
                q = q | Q('multi_match', query=ph_q, type='phrase', fields=['title^2', 'transcript'], operator='or')
                
            s = s.query(q)
        else:
            s = s.query('multi_match', query=main_q, type='cross_fields', fields=['title^2', 'transcript'], operator='or')

        s = highlight(s)
        response = s[start:end].execute()
        # print(response)

    # print("phrase: ", phrase_q)
    # print("rest:"+rest_text_q+"<<<<")
    # print("isdis: ", is_disjunct_search)

    # insert data into response
    resultList = {}
    # print(response.hits)
    for hit in response.hits:
        result={}
        result['score'] = hit.meta.score
        
        try:
            hmh = hit.meta.highlight
        except:
            pass

        has_highlight = True if 'highlight' in hit.meta else False
        
        result['title'] = hmh.title[0] if has_highlight and 'title' in hmh else hit.title
        result['transcript'] = hmh.transcript[0] if has_highlight and 'transcript' in hmh else hit.transcript
        # result['star'] = hmh.star[0] if has_highlight and 'star' in hmh else hit.starring
        # result['language'] = hmh.language[0] if has_highlight and 'language' in hmh else hit.language
        # result['country'] = hmh.country[0] if has_highlight and 'country' in hmh else hit.country
        # result['director'] = hmh.director[0] if has_highlight and 'director' in hmh else hit.director
        # result['location'] = hmh.location[0] if has_highlight and 'location' in hmh else hit.location
        # result['time'] = hmh.time[0] if has_highlight and 'time' in hmh else hit.time
        # result['categories'] = hmh.categories[0] if has_highlight and 'categories' in hmh else hit.categories
        resultList[hit.meta.id] = result


    # make the result list available globally
    gresults = resultList
    # print(">>>>", gresults)
    
    # get the total number of matching results
    result_num = response.hits.total
    
    stop_t = []
    rest_t = []
    terms = re.sub('"', '', main_q).split()
    for t in terms:
        if t in stopwords:
            stop_t.append(t)
        else:
            rest_t.append(t)

    # if we find the results, extract title and text information from doc_data, else do nothing
    if result_num > 0:
        return render_template('result.html', is_disjunct_search=is_disjunct_search, stop_len=len(stop_t), stops=stop_t, results=resultList, res_num=result_num, page_num=page, queries=shows)
    else:
        message = []
        if len(main_q) > 0:
            if stop_t:
                message.append('Ignoring term(s): '+' '.join(stop_t))

            # if rest_t:

            # TODO: 
            if rest_t and duration_q == "0" and len(speaker_q)==0:
                message.append('Unknown search term: '+' '.join(rest_t))

        if len(speaker_q) > 0:
            message.append('Cannot find speaker: '+speaker_q)
        # if len(dir_q) > 0:
        #     message.append('Cannot find director: '+dir_q)
        # if len(lang_q) > 0:
        #     message.append('Cannot find language: '+lang_q)
        # if len(ctry_q) > 0:
        #     message.append('Cannot find country: '+ctry_q)
        # if len(loc_q) > 0:
        #     message.append('Cannot find location: '+loc_q)
        # if len(cat_q) > 0:
        #     message.append('Cannot find category: '+cat_q)

        return render_template('result.html', results=message, res_num=result_num, page_num=page, queries=shows)

# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    # global gresults
    # print(">>>", gresults)
    film = gresults[res]
    filmtitle = film['title']
    for term in film:
        if type(film[term]) is AttrList:
            s = "\n"
            for item in film[term]:
                s += item + ",\n "
            film[term] = s
    # fetch the movie from the elasticsearch index using its id
    talk = Talk.get(id=res, index='ted_index')
    filmdic = talk.to_dict()
    film['duration'] = str(filmdic['duration']) + " min"

    return render_template('talk_page.html', film=film, title=filmtitle)


def highlight(s):
    s = s.highlight_options(pre_tags='<mark>', post_tags='</mark>')
    s = s.highlight('transcript', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('title', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('starring', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('language', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('country', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('director', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('location', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('time', fragment_size=999999999, number_of_fragments=1)
    # s = s.highlight('categories', fragment_size=999999999, number_of_fragments=1)

    return s


if __name__ == "__main__":
    app.run(debug=True)
