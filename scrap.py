import requests
from bs4 import BeautifulSoup
from re import compile as _re_compile
import json


base_url = "https://www.ted.com"

talks_url = base_url + "/talks?"

page_key = "page"

sort_key = "sort"

sort_value = "oldest"

transcript_url_extension = "/transcript.json?language=en"

# transcript json can be found at talks_url + extension

headers_pagelinks = {"Referer": "https://www.ted.com/talks",
                     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
                     }

headers_talklinks = {"Origin": "https://www.ted.com",
                     "Referer": "https://www.ted.com/talks/christian_moro_the_surprising_reason_our_muscles_get_tired/up-next",
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

        # data["talk_id"] = talk["id"]
        data["title"] = talk["title"]
        data["speaker"] = talk["speaker_name"]
        data["description"] = talk["description"]
        data["date"] = talk["recorded_at"][:10]
        data["duration"] = talk["duration"]
        data["thumbnails"] = talk["player_talks"][0]["thumb"]
        data["tags"] = talk["tags"]
        data["num_views"] = talk["viewed_count"]
        data["num_comments"] = talk_data["comments"]["count"] if talk_data["comments"] is not None else 0
        data["num_transcripts"] = len(talk["downloads"]["languages"])
        if data["num_transcripts"] != 0:
            data["transcript_language"] = [d['endonym'] for d in talk["downloads"]["languages"]]
        else:
            data["transcript_language"] = []
        data["categories"] = talk["ratings"]
        data["event"] = talk_data["event"]
        data["talk_link"] = base_url + talk_link

        ### Get the transcript ###
        if data["num_transcripts"] != 0:
            transc = requests.get(base_url + talk_link + transcript_url_extension, headers=headers_talklinks)

            # print(base_url + talk_link + transcript_url_extension)

            transc = transc.json()
            if "paragraphs" in transc:
                for t in transc["paragraphs"]:
                    if "trancript" not in data:
                        data["trancript"] = t["cues"][0]["text"]
                    else:
                        data["trancript"] += t["cues"][0]["text"]
            else:
                data["trancript"] = ""

        else:
            data["trancript"] = ""

        collection[str(index)] = data

    with open(outfile, "w") as f:
        json.dump(collection, f, indent=4)


if __name__ == '__main__':
    # num_pages = 107
    filepath = "talk_links.txt"
    # scrape_links(num_pages, outfile=filepath)
    scrape_talks(filepath, outfile="test.json")
