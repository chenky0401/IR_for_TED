import requests
from bs4 import BeautifulSoup
from re import compile as _re_compile
import json
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
import os


# ideas and why I want to extract these data
# use tags, title, and description to calculate talks similarity
# show one pos and one neg comment for each talk to let user decide whether to watch that talk
# use sentiment analysis to get negative comments

base_url = "https://www.ted.com"

talks_url = base_url + "/talks?"

page_key = "page"

sort_key = "sort"

sort_value = "oldest"

transcript_url_extension = "/transcript.json?language=en"


CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_console()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_video_statistics(service, **kwargs):
    results = service.videos().list(**kwargs).execute()
    item = results['items'][0]
    views = item['statistics']['viewCount']
    likeCount = item['statistics']['likeCount']
    dislikeCount = item['statistics']['dislikeCount']
    favoriteCount = item['statistics']['favoriteCount']
    commentCount = item['statistics']['commentCount']
    return views, likeCount, dislikeCount, favoriteCount, commentCount


def get_video_comments(service, **kwargs):

    comments = []
    results = service.commentThreads().list(**kwargs).execute()
    for item in results['items']:
        comment_as_dict = {}
        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']

        commenter_rating = item['snippet']['topLevelComment']['snippet']['viewerRating']

        # The rating the viewer has given to this comment.
        # Note that this property does not currently identify dislike ratings,
        # though this behavior is subject to change.
        # In the meantime, the property value is like if the viewer has rated the comment positively.
        # The value is none in all other cases,
        # including the user having given the comment a negative rating or not having rated the comment.
        # Valid values for this property are: like, none
        comment_like_count = item['snippet']['topLevelComment']['snippet']['likeCount']

        comment_author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']

        comment_as_dict[comment] = {"comment_author": comment_author, "commenter_rating": commenter_rating,
        "comment_like_count": comment_like_count}

        comments.append(comment_as_dict)

    return comments


def get_search_results(service, talk_title, **kwargs):
    results = service.search().list(**kwargs).execute()
    title_first_result = results['items'][0]['snippet']['title'].split("|")[0].rstrip()
    if title_first_result != talk_title:
        # talk not found in YouTube
        return None
    else:
        id_first_result = results['items'][0]['id']['videoId']
        return id_first_result


def get_talk_comments_and_statistics(service, talk_title):
    comments = []
    results_id = get_search_results(service, talk_title, q=talk_title, part='id,snippet',
                                    channelId="UCAuUUnT6oDeKwE6v1NGQxug", regionCode="US")

    if results_id is None:
        # talk not found in YouTube
        return comments, 0, 0, 0, 0, 0
    else:
        # get the most relevant 100 comments
        comments = get_video_comments(service, part='snippet', videoId=results_id, textFormat='plainText',
                                      order="relevance", maxResults=100)

        views, likeCount, dislikeCount, favoriteCount, commentCount = get_video_statistics(service, part='statistics', id=results_id)

        return comments, views, likeCount, dislikeCount, favoriteCount, commentCount


headers_pagelinks = {"Referer": "https://www.ted.com/talks",
                     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
                     }

headers_talklinks = {"Origin": "https://www.ted.com",
                     "Referer": "https://www.ted.com/talks/christian_moro_the_surprising_reason_our_muscles_get_tired/up-next",
                     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
                     }

headers_YouTube= {"Referer": "https://www.youtube.com",
                     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
                     }

def scrape_links(num_pages, outfile):
    '''
    Scrapes individual ted talks links
    :param: num_pages: total number of pages for Ted talks in Ted Talks official website
            outfile: output file path to save to
    '''
    count = 0

    with open(outfile, 'w') as file:

        for current_page in range(1, num_pages + 1):

            page_html = requests.get(talks_url, params={page_key: current_page, sort_key: sort_value}, headers=headers_pagelinks).text
            soup = BeautifulSoup(page_html, "html.parser")
            talks = soup.find(id="browse-results").find_all("a", class_="ga-link")[1::2]

            for talk in talks:
                count += 1
                file.write("%s\n" % talk["href"])
        print("Total number of links scraped: ", count)


def scrape_talks(filepath, outfile):
    '''
    Scrapes the talk pages for a TED talk, getting information and the
    transcript tokenized by cue cards.
    Returns nothing.
    Takes list of talk links, filepath to output of scrapes, and filepath to
    output of skipped talks.
    '''

    with open(filepath, 'r') as file:
        talk_links = file.read()
        talk_links = talk_links.split("\n")[:-1]

    collection = {}

    for index, talk_link in enumerate(talk_links):

    ### Get information about the talk ###

        talk_page_html = requests.get(base_url + talk_link, headers=headers_talklinks).text
        talk_soup = BeautifulSoup(talk_page_html, "html.parser")

        # Scrape <script> that contains ' "__INITIAL_DATA__" object

        script = talk_soup.find("script", string=_re_compile("__INITIAL_DATA__"))

        # Getting html after object declaration and removing newline and outer object close
        talk_data_string = script.text.split("\"__INITIAL_DATA__\":")[1][:-3]
        talk_data = json.loads(talk_data_string)
        talk = talk_data["talks"][0]

        data = {}

        # I couldn't find a way to extract the comments from www.ted.com
        # But anyway, all comments from www.ted.com seem to be positive. (only people who love tedtalks go to www.ted.com)
        # So I only use the comments from YouTube (and YouTube is much more popular across the world)

        data["title"] = talk["title"]
        data["speaker"] = talk["speaker_name"]
        data["description"] = talk["description"]
        data["date"] = talk["recorded_at"][:10]
        data["duration"] = talk["duration"]
        data["thumbnails"] = talk["player_talks"][0]["thumb"]
        data["tags"] = talk["tags"]

        # data["num_views"] = talk["viewed_count"]
        # data["num_comments"] = talk_data["comments"]["count"] if talk_data["comments"] is not None else 0
        ted_com_num_comments = talk_data["comments"]["count"] if talk_data["comments"] is not None else 0

        data["num_transcripts"] = len(talk["downloads"]["languages"])
        if data["num_transcripts"] != 0:
            data["transcript_language"] = [d['endonym'] for d in talk["downloads"]["languages"]]
        else:
            data["transcript_language"] = []
        data["categories"] = talk["ratings"]
        data["event"] = talk_data["event"]
        data["talk_link"] = base_url + talk_link

        # get data from YouTube

        data["comments"], YouTube_views, YouTube_likeCount, YouTube_dislikeCount, YouTube_favoriteCount, YouTube_commentCount = \
            get_talk_comments_and_statistics(service, data["title"])

        # merge ted.com and YouTube data

        data["num_views"] = talk["viewed_count"] + int(YouTube_views)
        data["num_comments"] = ted_com_num_comments + int(YouTube_commentCount)
        data["YouTube_likeCount"] = int(YouTube_likeCount)
        data["YouTube_dislikeCount"] = int(YouTube_dislikeCount)
        data["YouTube_favoriteCount"] = int(YouTube_favoriteCount)

        ### Get the transcript ###
        if data["num_transcripts"] != 0:
            transc = requests.get(base_url + talk_link + transcript_url_extension, headers=headers_talklinks)

            transc = transc.json()
            if "paragraphs" in transc:
                for t in transc["paragraphs"]:
                    if "transcript" not in data:
                        data["transcript"] = t["cues"][0]["text"]
                    else:
                        data["transcript"] += t["cues"][0]["text"]
            else:
                data["transcript"] = ""

        else:
            data["transcript"] = ""

        collection[str(index + 1)] = data

    with open(outfile, "w") as f:
        json.dump(collection, f, indent=4)


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    service = get_authenticated_service()
    # num_pages = 107
    filepath = "talk_links.txt"
    # scrape_links(num_pages, outfile=filepath)
    scrape_talks(filepath, outfile="TedTalks_corpus.json")


    # When running locally, disable OAuthlib's HTTPs verification. When
    # running in production *do not* leave this option enabled.




    # collection = {}
    #
    # talk_link = "/talks/michael_arntfield_how_you_can_help_solve_cold_cases"
    # talk_page_html = requests.get(base_url + talk_link, headers=headers_talklinks).text
    # talk_soup = BeautifulSoup(talk_page_html, "html.parser")
    #
    # # Scrape <script> that contains ' "__INITIAL_DATA__" object
    #
    # script = talk_soup.find("script", string=_re_compile("__INITIAL_DATA__"))
    #
    # # Getting html after object declaration and removing newline and outer object close
    # talk_data_string = script.text.split("\"__INITIAL_DATA__\":")[1][:-3]
    # talk_data = json.loads(talk_data_string)
    # talk = talk_data["talks"][0]
    #
    # data = {}
    #
    # # data["talk_id"] = talk["id"]
    # data["title"] = talk["title"]
    # data["speaker"] = talk["speaker_name"]
    # data["description"] = talk["description"]
    # data["date"] = talk["recorded_at"][:10]
    # data["duration"] = talk["duration"]
    # data["thumbnails"] = talk["player_talks"][0]["thumb"]
    # data["tags"] = talk["tags"]
    # data["num_views"] = talk["viewed_count"]
    # data["num_comments"] = talk_data["comments"]["count"] if talk_data["comments"] is not None else 0
    # data["num_transcripts"] = len(talk["downloads"]["languages"])
    # if data["num_transcripts"] != 0:
    #     data["transcript_language"] = [d['endonym'] for d in talk["downloads"]["languages"]]
    # else:
    #     data["transcript_language"] = []
    # data["categories"] = talk["ratings"]
    # data["event"] = talk_data["event"]
    # data["talk_link"] = base_url + talk_link
    #
    # ### Get the transcript ###
    # if data["num_transcripts"] != 0:
    #     transc = requests.get(base_url + talk_link + transcript_url_extension, headers=headers_talklinks)
    #
    #     # print(base_url + talk_link + transcript_url_extension)
    #
    #     transc = transc.json()
    #     if "paragraphs" in transc:
    #         for t in transc["paragraphs"]:
    #             if "trancript" not in data:
    #                 data["trancript"] = t["cues"][0]["text"]
    #             else:
    #                 data["trancript"] += t["cues"][0]["text"]
    #     else:
    #         data["trancript"] = ""
    #
    # else:
    #     data["trancript"] = ""
    #
    # collection["3841"] = data
    #
    # with open("extras", "w") as f:
    #     json.dump(collection, f, indent=4)
