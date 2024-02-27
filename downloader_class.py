import csv
import math
import re
import random
import os
import traceback
from bs4 import BeautifulSoup as bs
from requests_html import HTMLSession, MaxRetries
from tqdm import tqdm
from youtube_transcript_api import YouTubeTranscriptApi
from utils import lang_code_to_name


class Subtitles_downloader():

    def __init__(self, out_path="out", lang="en", save_links=True, scrolldown=10000, get_generated_subtitles=True, single_line=True):
        print('loading HTML session...')
        self.session = HTMLSession()
        self.sub_filter_code = "&sp=EgIoAQ%253D%253D"
        self.out_path = out_path
        self.lang = lang
        self.save_links = save_links
        self.scrolldown = scrolldown
        self.video_ids = []
        self.get_generated_subtitles = get_generated_subtitles
        self.single_line = single_line

    def search_by_url(self, links):
        if not isinstance(links, list):
            links = [links]
        self.video_ids = [link.split('v=')[1] for link in links]

    def search(self, queries):
        """
        returns a list of video ids for videos that match the search term, and have subtitles.
        :param queries: list of search queries
        :param scrolldown: number of times to page down
        """
        if isinstance(queries, list):
            for q in queries:
                try:
                    if self.save_links:
                        # check if this search has already been made, if so, skip
                        csv_out_path = 'links/{}_search_results.csv'.format(q)
                        if os.path.isfile(csv_out_path):
                            #TODO: read video ids from csv & check txt files instead of just assuming each id has been downloaded
                            pass

                    search_url = "https://www.youtube.com/results?search_query={}{}".format(q, self.sub_filter_code)
                    print('Fetching search results for "{}"...'.format(q))
                    response = self.session.get(search_url)
                    print('Executing JS...')
                    try:
                        response.html.render(scrolldown=self.scrolldown, timeout=30.0)
                    except MaxRetries as e:
                        print(e)
                        continue

                    # create bs object to parse HTML
                    soup = bs(response.html.html, "html.parser")

                    # get all video ids from soup
                    query_ids = []
                    count = 0
                    for count, link in enumerate(
                            list(set(soup.findAll('a', attrs={'href': re.compile("^/watch\?v=.{8,12}")})))):
                        query_ids.append(link.get('href').split('v=')[1])
                    self.video_ids.extend(query_ids)

                    # save links to csv file
                    if self.save_links:
                        with open(csv_out_path, "w") as f:
                            writer = csv.writer(f)
                            writer.writerows([query_ids])

                    print('{} unique links found for "{}"!'.format(count, q))
                except:
                    print('Search query {} failed!'.format(q))
                    traceback.print_exc()
        else:
            raise TypeError("search queries must be list")

    def download_subs(self):
        for video_id in tqdm(list(set(self.video_ids)), desc="Downloading subtitles..."):
            try:
                # gets list of available transcript from YTtranscriptAPI
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

                # init dictionary to store results and out name for txt file
                out = {}
                out_name = "{}/{}".format(self.out_path, video_id)

                # count number of languages available
                for t in transcript_list:
                    if (t.is_generated and not self.get_generated_subtitles) or (not t.is_generated and self.get_generated_subtitles):
                        continue
                    if self.lang != t.language_code:
                        continue

                    # fetch the actual transcript
                    transcript = t.fetch()

                    # write every minute of every language in transcript to a results dict
                    out[t.language_code] = {}
                    total_minutes = -1
                    for i in transcript:
                        end = i["start"] + i["duration"]
                        minute = int(math.floor(end / 60.0))
                        header_txt = ''
                        if minute > total_minutes:
                            total_minutes = minute
                        if minute in out[t.language_code]:
                            out[t.language_code][minute] += '{}\n'.format(i["text"])
                        else:
                            out[t.language_code][minute] = '{}{}\n'.format(header_txt, i["text"])

                # write every minute of every language in transcript to txt file, shuffling language order
                with open("{}.txt".format(out_name), "w") as text_file:
                    minutes = list(out.values())
                    all_minutes = set(x for l in minutes for x in l)
                    for m in all_minutes:
                        keys = list(out.keys())
                        random.shuffle(keys)
                        for l in keys:
                            try:
                                text_to_write = out[l][m]
                                if self.single_line:
                                    text_to_write = text_to_write.replace("\n", " ")
                                text_file.write(text_to_write)
                            except:
                                pass
            except Exception:
                print('Download for {} failed!'.format(video_id))
                traceback.print_exc()
