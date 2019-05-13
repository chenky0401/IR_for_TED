import json
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
import os


transcript_url_extension = "/transcript.json?language=en"


CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_console()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def search_by_channelId(service, **kwargs):
    video_id_list = []
    results = service.search().list(**kwargs).execute()
    while results:
        if len(results['items']) != 0:
            for item in results['items']:
                if "videoId" in item["id"]:
                    video_id_list.append(item["id"]["videoId"])
            if 'nextPageToken' in results:
                kwargs['pageToken'] = results['nextPageToken']
                results = service.search().list(**kwargs).execute()
            else:
                break
            print(video_id_list)
        else:
            break
    return video_id_list


def write_video_id_list_to_file(outfile, service, **kwargs):
    # date format 1970-01-01T00:00:00Z
    earliest_published_year = 2006
    suffix = "-01-01T00:00:00Z"
    video_id_list = []
    with open(outfile, "w") as f:
        while earliest_published_year < 2020:
            publishedBefore = str(earliest_published_year + 1) + suffix
            publishedAfter = str(earliest_published_year) + suffix
            # YouTube API sucks, it can only get max of 500 results
            video_id_list = search_by_channelId(service, part='id', channelId="UCAuUUnT6oDeKwE6v1NGQxug",
                                                        regionCode="US", maxResults=50, publishedAfter=publishedAfter,
                                                        publishedBefore=publishedBefore)
            for video_id in video_id_list:
                f.write("%s\n" % video_id)
            earliest_published_year += 1


def write_videos_statistics_to_file(id_list, outfile, service, **kwargs):
    statistics_ = {}
    for talk_id in id_list:
        results = service.videos().list(part='snippet, statistics', id=talk_id).execute()
        if len(results['items']) != 0:
            for item in results['items']:
                print(item['statistics'])
                title = item['snippet']['title']
                if 'viewCount' in item['statistics']:
                    viewCount = item['statistics']['viewCount']
                else:
                    viewCount = 0
                if 'likeCount' in item['statistics']:
                    likeCount = item['statistics']['likeCount']
                else:
                    likeCount = 0

                if 'dislikeCount' in item['statistics']:
                    dislikeCount = item['statistics']['dislikeCount']
                else:
                    dislikeCount = 0
                if 'favoriteCount' in item['statistics']:
                    favoriteCount = item['statistics']['favoriteCount']
                else:
                    favoriteCount = 0
                if 'commentCount' in item['statistics']:
                    commentCount = item['statistics']['commentCount']
                else:
                    commentCount = 0

                statistics_[title] = viewCount, likeCount, dislikeCount, favoriteCount, commentCount

    with open(outfile, "w") as f:
        json.dump(statistics_, f, indent=4)


#  viewCount, likeCount, dislikeCount, favoriteCount, commentCount


def get_video_comments(service, **kwargs):
    comments = []
    try:
        results = service.commentThreads().list(**kwargs).execute()
        if len(results['items']) != 0:

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
    except:
        pass

    return comments




if __name__ == '__main__':
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # service = get_authenticated_service()
    # outfile = "TedTalks_YouTube_id.txt"
    # write_video_id_list_to_file(outfile, service)
    # outfile2 = "TedTalks_YouTube_Statistics.json"
    # outfile3 = "TedTalks_YouTube_Statistics2.json"
    # outfile4 = "TedTalks_YouTube_Statistics3.json"
    #
    # with open(outfile, "r") as f:
    #     YouTube_talk_ids = f.read()
    #     YouTube_talk_ids_list = YouTube_talk_ids.split("\n")[:-1]

    # YouTube_talk_ids_list1 = YouTube_talk_ids_list[:500]
    # YouTube_talk_ids_list2 = YouTube_talk_ids_list[500:1800]
    # YouTube_talk_ids_list3 = YouTube_talk_ids_list[1800:]

    # write_videos_statistics_to_file(YouTube_talk_ids_list1, outfile2, service)
    # write_videos_statistics_to_file(YouTube_talk_ids_list2, outfile3, service)
    # write_videos_statistics_to_file(YouTube_talk_ids_list3, outfile4, service)

    # with open("YouTubeStats.json") as f_in:
    #     YouTubeStats = json.load(f_in)

    # collection = {}
    # i = 0
    # for key, values in YouTubeStats.items():
    #     viewCount, likeCount, dislikeCount, favoriteCount, commentCount = values
    #     comments = get_video_comments(service, part='snippet', videoId=YouTube_talk_ids_list[i], textFormat='plainText',
    #                              order="relevance", maxResults=20)
    #     collection[key] = {"viewCount": viewCount, "likeCount": likeCount, "dislikeCount": dislikeCount,
    #                        "favoriteCount": favoriteCount, "commentCount": commentCount, "comments": comments}
    #     i += 1
    #
    # with open("YouTubeStatsComments.json", "w") as f:
    #     json.dump(collection, f, indent=4)

    with open("YouTubeStatsComments.json") as f_in:
        YouTubeStatsComments = json.load(f_in)

    with open("TedTalks_corpus_fixed.json") as f_in:
        TedTalks_corpus = json.load(f_in)

    new_collection = {}
    for key, values in TedTalks_corpus.items():
        new_collection[key] = values
        new_collection[key]["YouTube"] = {}
        for key2, values2 in YouTubeStatsComments.items():
            if "|" in str(key2):
                title2 = str(key2).split("|")[0].rstrip()
            elif ": " in str(key2):
                title2 = str(key2).split(": ")[1].rstrip()
            else:
                title2 = str(key2)

            if title2 == values["title"]:
                new_collection[key]["YouTube"]["num_views"] = int(values2["viewCount"])
                new_collection[key]["YouTube"]["num_comments"] = int(values2["commentCount"])
                new_collection[key]["YouTube"]["YouTube_likeCount"] = int(values2["likeCount"])
                new_collection[key]["YouTube"]["YouTube_dislikeCount"] = int(values2["dislikeCount"])
                new_collection[key]["YouTube"]["YouTube_favoriteCount"] = int(values2["favoriteCount"])
                v = []
                for i in range(len(values2["comments"])):
                    dict = values2["comments"][i]
                    new_dict = {}
                    new_dict[i] = {}
                    new_dict[i]["content"] = list(dict.keys())[0]
                    new_dict[i]["comment_author"] = list(dict.values())[0]["comment_author"]
                    v.append(new_dict)
                new_collection[key]["YouTube"]["comments"] = v
                break
        # print(new_collection)

        print("Finished iteration", int(key))


    with open("TEDTalksFullCorpusFixed.json", "w") as f:
        json.dump(new_collection, f, indent=4)





