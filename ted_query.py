"""
Author: Kuan-Yu Chen
"""
import re
from flask import *
from ted_index import Talk
from pprint import pprint
from elasticsearch_dsl import Q
from elasticsearch_dsl.utils import AttrList
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from wordcloud import WordCloud


app = Flask(__name__)

# Initialize global variables for rendering page
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

        # update global variable template data
        tmp_main = main_q
        tmp_speaker = speaker_q
        tmp_duration = duration_q

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
    mintime *= 60
    maxtime *= 60

    # store query values to display in search boxes in UI
    shows = {}
    shows['query'] = main_q
    shows['speaker'] = speaker_q
    shows['duration'] = duration_q


    # Create a search object to query our index 
    search = Search(index='ted_index')

    # determine the subset of results to display (based on current <page> value)
    start = 0 + (page-1)*10
    end = 10 + (page-1)*10

    # Build up your elasticsearch query in piecemeal fashion based on the user's parameters passed in.
    # The search API is "chainable".
    # Each call to search.query method adds criteria to our growing elasticsearch query.
    # You will change this section based on how you want to process the query data input into your interface.
        
    # search for runtime using a range query
    s = search.query('range', duration={'gte':mintime, 'lte':maxtime})

    # search for matching stars
    s = s.query('match', speaker=speaker_q) if len(speaker_q) > 0 else s

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
                        if q:
                            rest_text_q.append(q)

            for ph_q in phrase_q:
                s = s.query('multi_match', query=ph_q, type='phrase', fields=['title^2', 'transcript', 'description'], operator='and')

            if len(rest_text_q) != 0:
                rest_text_q = ' '.join(rest_text_q)
                s = s.query('multi_match', query=rest_text_q, type='cross_fields', fields=['title^2', 'transcript', 'description'], operator='and')

        else:
            s = s.query('multi_match', query=main_q, type='cross_fields', fields=['title^2', 'transcript', 'description'], operator='and')

    # highlight
    s = highlight(s)


    # execute search and return results in specified range.
    response = s[start:end].execute()

    is_disjunct_search = True if response.hits.total == 0 else False

    if is_disjunct_search:
        s = s_copy
        if has_phrase:
            q = Q('match_all')
            if len(rest_text_q) != 0:
                q = Q('multi_match', query=rest_text_q, type='cross_fields', fields=['title^2', 'transcript', 'description'], operator='or')

            for ph_q in phrase_q:
                q = q | Q('multi_match', query=ph_q, type='phrase', fields=['title^2', 'transcript', 'description'], operator='or')
                
            s = s.query(q)
        else:
            s = s.query('multi_match', query=main_q, type='cross_fields', fields=['title^2', 'transcript', 'description'], operator='or')

        s = highlight(s)
        response = s[start:end].execute()

    # get the total number of matching results
    result_num = response.hits.total
    # insert data into response
    resultList = {}
    max_view, max_comment = 0, 0
    for hit in response.hits:
        result = {}
        result['score'] = hit.meta.score
        result['relevance'] = '%.2f'%((hit.meta.score / response.hits.max_score)*100)
        result['speaker'] = hit.speaker
        result['num_views'] = hit.num_views
        result['num_comments'] = hit.num_comments
        result['posted_date'] = hit.date
        result['link'] = hit.link
        result['embed'] = re.sub('www', 'embed', hit.link)
        result['pic'] = hit.pic
        result['ratings'] = hit.ratings
        result['transcript'] = hit.transcript
        result['rec'] = hit.rec
        result['duration'] = int(hit.duration/60)+1
        if hit.youtube != {}:
            result['num_views'] += hit.youtube.num_views
            result['likes'] = hit.youtube.YouTube_likeCount
            result['dislikes'] = hit.youtube.YouTube_dislikeCount
            result['comments'] = []
            # for c in hit.youtube.comments:
            for i in range(len(hit.youtube.comments)):
                c = hit.youtube.comments[i]
                d = list(list(c.__dict__.values())[0].values())[0]
                result['comments'].append(d["content"]+" -- "+d["comment_author"])
                if i == 2:
                    break

        else:
            result['likes'] = 0
            result['dislikes'] = 0
            result['comments'] = []
        if max_view < result['num_views']:
            max_view = result['num_views']

        if max_comment < hit.num_comments:
            max_comment = hit.num_comments

        try:
            hmh = hit.meta.highlight
        except:
            pass

        has_highlight = True if 'highlight' in hit.meta else False
        
        result['title'] = hmh.title[0] if has_highlight and 'title' in hmh else hit.title
        result['description'] = hmh.description[0] if has_highlight and 'description' in hmh else hit.description

        resultList[hit.meta.id] = result

    for key, result in resultList.items():
        pop = 1/2 * (result['num_views']/max_view) + 1/2 * (result['num_comments']/max_comment)
        pop = 100 * pop
        result['popularity'] = '%.2f'%pop

    # make the result list available globally
    gresults = resultList
        
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

            if rest_t and duration_q == "0" and len(speaker_q)==0:
                message.append('Unknown search term: '+' '.join(rest_t))

        if len(speaker_q) > 0:
            message.append('Cannot find speaker: '+speaker_q)


        return render_template('result.html', results=message, res_num=result_num, page_num=page, queries=shows)

# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    global gresults

    # fetch the movie from the elasticsearch index using its id
    try:
        film = gresults[res]
    except:
        pass

        talk = Talk.get(id=res, index='ted_index')
        filmdic = talk.to_dict()

        film = filmdic

    filmtitle = film['title']
    film['embed'] = re.sub('www', 'embed', film["link"])

    try:
        if len(film["ratings"]) > 0:
            word_list = [ (h["name"], h["count"]) for h in film["ratings"]]
            path = word_cloud(word_list, res)
            film['wc'] = path
    except:
        film['wc'] = ""
    recs = {}
    for r in film['rec'].split():
        # print(">>", r)
        rec = {}
        talk = Talk.get(id=str(int(r)+1), index='ted_index')
        filmdic = talk.to_dict()
        rec["pic"] = filmdic["pic"]
        rec["title"] = filmdic["title"]
        rec["link"] = filmdic["link"]
        rec["embed"] = re.sub('www', 'embed', rec["link"])
        recs[r] = rec

    return render_template('talk_page.html', res=res, film=film, title=filmtitle, recs=recs)


def highlight(s):
    s = s.highlight_options(pre_tags='<mark>', post_tags='</mark>')
    s = s.highlight('transcript', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('title', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('description', fragment_size=999999999, number_of_fragments=1)

    return s

def word_cloud(word_list, n):
    """
    Create word cloud.
    """
    total = sum(i[1] for i in word_list)
    if total != 0:
        freq = {i[0]:(i[1]/total) for i in word_list if i[1] != 0}
        # Generate a word cloud image
        wc = WordCloud(width=1200, height=800, background_color="white")
        wc.generate_from_frequencies(freq)
        # Save the generated image
        wc.to_file("static/img/"+n+".jpg")
    else:
        print("no img")
    return "../static/img/"+n+".jpg"


if __name__ == "__main__":
    app.run(debug=True)
