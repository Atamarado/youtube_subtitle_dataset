import traceback, argparse
from multiprocessing import Pool, cpu_count
from itertools import repeat
from downloader_class import Subtitles_downloader
import csv, os
from utils import chunks
from pytube import Playlist

# Change the version of Chromium used to one that exists
os.environ['PYPPETEER_CHROMIUM_REVISION'] = "999988"

def download_subs_single(queries, query_mode, out_path="out", save_links=True, scrolldown=1000, lang="en", get_generated_subtitles=True):
    assert query_mode in ["query", "playlist"]
    try:
        sub_downloader = Subtitles_downloader(out_path=out_path, save_links=save_links, scrolldown=scrolldown, lang=lang, get_generated_subtitles=get_generated_subtitles)
        if query_mode == "playlist":
            sub_downloader.search_by_url(queries)
        else:
            sub_downloader.search(queries)
        sub_downloader.download_subs()
    except:
        print('Thread failed!')
        traceback.print_exc()


def download_subs_mp(queries, query_mode, out_path="out", save_links=True, scrolldown=100, lang="en", get_generated_subtitles=True):
    queries = chunks(queries, (len(queries) // cpu_count() - 1))
    with Pool(cpu_count() - 1) as p:
        p.starmap(download_subs_single, zip(queries, repeat(query_mode), repeat(out_path), repeat(save_links), repeat(scrolldown), repeat(lang), repeat(get_generated_subtitles)))
    print('Done!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CLI for YT_subtitles - extracts Youtube subtitles from a list of search terms or a youtube Playlist link')
    parser.add_argument('--search_terms',
                        help='A comma separated list of search terms, alternatively, pass path to a csv with the -c '
                             'argument',
                        type=str, required=False)
    parser.add_argument('-p --playlist', help="URL to the Youtube playlist", type=str, required=False)
    parser.add_argument('--out_path', help='Output location for final .txt files', type=str, required=False,
                        default='output')
    parser.add_argument('-s', '--save_links', help='whether to save links to a .csv file', action="store_false")
    parser.add_argument('-c', '--csv',
                        help='if true, positional arg should be a path to a .csv file containing search terms',
                        action="store_true")
    parser.add_argument('--scroll', help='how far to scroll down in the youtube search', type=int, required=False,
                        default=100)
    args = parser.parse_args()
    os.makedirs(args.out_path, exist_ok=True)
    if args.save_links:
        os.makedirs("links", exist_ok=True)

    if args.playlist:
        playlist = Playlist(args.playlist)
        search_terms = list(playlist.video_urls)
    elif args.search_terms:
        search_terms = []
        with open(args.search_terms, newline='') as inputfile:
            for row in csv.reader(inputfile):
                search_terms.append(row)
        # flattens list of list into unique list of items that aren't empty
        search_terms = list(set([item for sublist in search_terms for item in sublist if item]))
    else:
        assert args.csv, "You need to provide either 'search_terms', 'playlist', or 'csv'"
        search_terms = args.search_terms.split(',')

    print('Searching Youtube for: \n {}'.format(search_terms))

    query_mode = "playlist" if args.playlist else "query"
    download_subs_mp(search_terms, query_mode, args.out_path, args.save_links, args.scroll)
