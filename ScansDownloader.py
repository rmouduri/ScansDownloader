from bs4 import BeautifulSoup
import os
import random
import re
import requests
from sys import argv
from threading import Thread, Lock
from tqdm import tqdm
from win11toast import toast
from argparse import ArgumentParser


GREEN: str = "\033[92m"
RED: str = "\033[91m"
RESET: str = "\033[0m"


class ScansDownloader:
    class MangaNotAvailableError(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    
    class MissingArgumentError(Exception):
        def __init__(self, *args):
            super().__init__(*args)

    def __init__(self):
        parser: ArgumentParser = ArgumentParser()
        parser.add_argument("manga", type=str, help="The manga to download")
        parser.add_argument("chapters", nargs='?', type=str, help="List of chapters separated with '-' for a range or a ',' for single chapters, e.g: 10-20,25 for chapters 10 to 20 and chapter 25")
        parser.add_argument("-l", "--lang", choices=["FR", "EN", "DE", "ITA"], type=str, default="FR", help="Choose the language of the manga")
        parser.add_argument("-t", "--threads", type=int, default=20, help="Number of concurrent threads downloading scans")
        parser.add_argument("-o", "--out-dir", type=str, default=os.getcwd(), help="Path where folder \"{MANGA} Scans {LANG}\" will be created")
        parser.add_argument("-r", "--routine", action="store_true", help="Checks for new chapters of {MANGA} and downloads them")
        args = parser.parse_args()
 
        if not args.routine and not args.chapters: raise self.MissingArgumentError("Neither --chapter or --routine is provided")

        # Uninitialized properties
        self.bars: list[tqdm]
        self.threads: list[Thread]

        # Initialized properties
        self.manga: str = args.manga.title()
        self.chapters_mutex: Lock = Lock()
        self.routine: bool = args.routine
        self.n_threads: int = args.threads
        self.lang: str = args.lang
        self.website: str = self.get_website(self.lang)
        self.manga_url_name: str = self.get_manga_url_name()
        self.chapters_list: list[int | float] = None if self.routine else self.get_chapters_list(args.chapters)
        self.n_chapters: int = None if self.routine else len(self.chapters_list)
        self.chapters_list_idx: int = 0

        # Paths properties
        RESOURCES_FOLDER_NAME: str = "resources"
        ICONS_FOLDER_NAME: str = "icons"
        SCANS_FOLDER_NAME: str = f"{self.manga} Scans {self.lang}"
        self.resources_path: str = os.path.join(os.getcwd(), RESOURCES_FOLDER_NAME)
        self.icons_path: str = os.path.join(self.resources_path, ICONS_FOLDER_NAME)
        self.one_piece_icons_folder: str = os.path.join(self.icons_path, "One Piece")
        self.scans_folder_path: str = os.path.join(os.getcwd(), SCANS_FOLDER_NAME)

    @staticmethod
    def log(s: str, color: str = ""):
        print(f"{color}[{__class__.__name__}]", s, flush=True, end=f"{RESET}\n")
    
    @staticmethod
    def add_zero_if_below_ten(n: int) -> str:
        return ("0" if n < 10 else "") + str(n)

    @staticmethod
    def get_chapters_list(chapters: str) -> list[int | float]:
        def chapter_to_num(chapter: str):
            return float(chapter) if '.' in chapter else int(chapter)

        split_input: list[str] = re.split("(-|,)", chapters)
        split_input_len: int = len(split_input)
        chapters_set: set[int | float] = set()
        idx: int = 0

        while idx < split_input_len:
            if idx == split_input_len - 1:
                chapters_set.add(chapter_to_num(split_input[idx]))
                break
            
            delimiter: str = split_input[idx + 1]
            if delimiter == '-':
                chapters_set.update(n_chap for n_chap in range(int(split_input[idx]), int(split_input[idx + 2]) + 1))
                idx += 4
            elif delimiter == ',':
                chapters_set.add(chapter_to_num(split_input[idx]))
                idx += 2

        final_list: list[int | float] = list(chapters_set)
        final_list.sort()

        return final_list
    
    @staticmethod
    def get_website(lang: str) -> str:
        if lang == "FR":
            return "https://www.scan-vf.net"

    def get_manga_url_name(self) -> str:
        DELIMITERS: list[str] = [ '-', '_', '' ]

        for delimiter in DELIMITERS:
            manga_url_name: str = self.manga.lower().replace(' ', delimiter)
            url: str = f"{self.website}/{manga_url_name}"
            response = requests.get(url)

            if response.status_code == 200:
                return manga_url_name

        raise self.MangaNotAvailableError(f"Can't find `{self.manga}` in `{self.website}`")

    def next_chapter_bar(self) -> list[int, tqdm]:
        with self.chapters_mutex:
            if self.chapters_list_idx >= len(self.chapters_list):
                return [] # False

            chapter: int = self.chapters_list_idx
            self.chapters_list_idx += 1
            return [ self.chapters_list[chapter], self.bars[chapter] ]

    def get_bar(self, chapter: int, position: int = 0):
        return tqdm(desc=f"[{__class__.__name__}] {self.manga} Chapter {chapter:>{len(str(self.chapters_list[-1])) if self.chapters_list else 3}}", bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", position=position, ncols=150, leave=True)

    def get_chapter_url(self, chapter: int) -> str:
        if self.lang == "FR":
            return f"{self.website}/index.php/{self.manga_url_name}/chapitre-{chapter}"

    def get_chapter(self, chapter: int | float, bar: tqdm) -> bool:
        chapter_url: str = self.get_chapter_url(chapter)
        response = requests.get(chapter_url)
        if response.status_code != 200:
            bar.bar_format = RED + bar.bar_format + f" - Failed to retrieve the webpage. Status code: {response.status_code}" + RESET
            bar.refresh()
            return False

        try:
            soup = BeautifulSoup(response.content, "html.parser")
            pages_list = soup.find("div", {"id": "all"}).find_all("img")
            n_pages: int = len(pages_list)
            bar.total = n_pages
            
            if not os.path.exists(self.scans_folder_path):
                try: os.makedirs(self.scans_folder_path)
                except: pass

            chapter_path: str = os.path.join(self.scans_folder_path, str(chapter))
            if not os.path.exists(chapter_path):
                try: os.makedirs(chapter_path)
                except: pass

            for index, page in enumerate(pages_list, start=1):
                page_url: str = page.get("data-src").replace(' ', '')
                extension: str = os.path.splitext(page_url)[1]
                img_data = requests.get(page_url).content
                page_filename: str = f"{"".join([word[0] for word in self.manga.split(" ")])}-{self.add_zero_if_below_ten(chapter)}-{self.add_zero_if_below_ten(index)}{extension}"

                with open(os.path.join(chapter_path, page_filename), "wb") as f:
                    f.write(img_data)

                bar.update(1)
                if bar.n == n_pages:
                    bar.bar_format = GREEN + bar.bar_format + " - Downloaded successfully" + RESET
                    bar.refresh()
        except Exception as e:
            bar.bar_format = RED + bar.bar_format + f" - Error : {str(e)}" + RESET
            bar.refresh()
            return False
        
        return True

    def get_all_chapters(self):
        chapter_bar_tuple: list[int, tqdm]
        while chapter_bar_tuple := self.next_chapter_bar():
            self.get_chapter(chapter_bar_tuple[0], chapter_bar_tuple[1])

    def get_chapters_in_threads(self) -> bool:
        self.bars = [ self.get_bar(chapter, abs(idx - self.n_chapters)) for idx, chapter in enumerate(self.chapters_list, start=1) ]
        self.threads = []

        for _ in range(self.n_threads if self.n_threads <= self.n_chapters else self.n_chapters):
            t = Thread(target=self.get_all_chapters, args=[])
            self.threads.append(t)
            t.start()

        for t in self.threads:
            t.join()

    def send_windows_notification(self, start_chapter: int, end_chapter: int):
        title: str = "Scans Downloader"
        icons: list[str] = os.listdir(self.one_piece_icons_folder)
        rand_icon: str = os.path.join(self.one_piece_icons_folder, icons[random.randint(0, len(icons) - 1)])
        button: dict = {"activationType": "protocol", "arguments": os.path.join(self.scans_folder_path, str(start_chapter)), "content": "Open folder"}
        body: str

        if start_chapter == end_chapter:
            body=f"New {self.manga} Chapter {start_chapter} !"
        else:
            body=f"New {self.manga} Chapters {start_chapter}-{end_chapter} !"

        toast(title, body=body, icon=rand_icon, button=button)

    def daily_routine(self):
        max_chapter: int
        try: max_chapter = int(max([ float(chap) for chap in os.listdir(self.scans_folder_path) ])) + 1
        except FileNotFoundError: return False

        min_chapter: int = max_chapter
        while  self.get_chapter(max_chapter, self.get_bar(max_chapter)) == True:
            max_chapter += 1

        if max_chapter > min_chapter:
            self.send_windows_notification(min_chapter, max_chapter - 1)

        return True

    def start(self):
        if self.routine:
            self.daily_routine()
        else:
            self.get_chapters_in_threads()


if __name__ == "__main__":
    scans_dl = ScansDownloader()

    scans_dl.start()