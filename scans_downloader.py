from bs4 import BeautifulSoup
import os
import random
import requests
from sys import argv
from threading import Thread
from tqdm import tqdm
from win11toast import toast


GREEN: str = "\033[92m"
RED: str = "\033[91m"
RESET: str = "\033[0m"
MAX_THREADS: int = 20

LANG: str = "FR"
MANGA: str = "One Piece"
# MANGA: str = "The Promised Neverland"
SEPARATOR: str = '_'
MANGA_URL_NAME: str = MANGA.lower().replace(' ', SEPARATOR)
WEBSITE: str = "https://www.scan-vf.net"

SCANS_FOLDER_NAME: str = f"{MANGA} Scans {LANG}"
RESOURCES_FOLDER_NAME: str = "resources"
ICONS_FOLDER_NAME: str = "icons"

SCANS_FOLDER_PATH: str = os.path.join(os.getcwd(), SCANS_FOLDER_NAME)
RESOURCES_FOLDER: str = os.path.join(os.getcwd(), RESOURCES_FOLDER_NAME)
ICONS_FOLDER: str = os.path.join(RESOURCES_FOLDER, ICONS_FOLDER_NAME)
ONE_PIECE_ICONS_FOLDER: str = os.path.join(ICONS_FOLDER, MANGA)

def log(s: str, color: str = ""):
    print(f"{color}[ScansDownloader]", s, flush=True, end=f"{RESET}\n")


def add_zero_if_below_ten(n: int) -> str:
    return ("0" if n < 10 else "") + str(n)


def get_bar(chapter: int, position: int = 0):
    return tqdm(desc=f"[ScansDownloader] {MANGA} Chapter {chapter:>2}", bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}", position=position, ncols=150, leave=True)


def get_chapter(chapter: int, bar: tqdm) -> bool:
    chapter_url: str = f"{WEBSITE}/index.php/{MANGA_URL_NAME}/chapitre-{chapter}"
    response = requests.get(chapter_url)

    if response.status_code != 200:
        bar.bar_format = RED + bar.bar_format + f" - Failed to retrieve the webpage. Status code: {response.status_code}" + RESET
        bar.refresh()
        return False

    try:
        soup = BeautifulSoup(response.content, "html.parser")
        extension: str = os.path.splitext(soup.find("img", {"class": "img-responsive scan-page"}).get("src"))[1].replace(' ', '')
        n_pages: int = len(soup.find("select", {"class": "selectpicker"}).find_all())
        bar.total = n_pages

        if not os.path.exists(SCANS_FOLDER_PATH):
            try: os.makedirs(SCANS_FOLDER_PATH)
            except: pass

        chapter_path: str = os.path.join(SCANS_FOLDER_PATH, str(chapter))
        if not os.path.exists(chapter_path):
                try: os.makedirs(chapter_path)
                except: pass

        for page in range(1, n_pages + 1):
            page_url = f"{WEBSITE}/uploads/manga/{MANGA_URL_NAME}/chapters/chapitre-{chapter}/{add_zero_if_below_ten(page)}{extension}"
            img_data = requests.get(page_url).content
            page_filename: str = f"{"".join([word[0] for word in MANGA.split(" ")])}-{add_zero_if_below_ten(chapter)}-{add_zero_if_below_ten(page)}{extension}"

            with open(os.path.join(chapter_path, page_filename), "wb") as f:
                f.write(img_data)

            bar.update(1)
            if bar.n == n_pages:
                bar.bar_format = GREEN + bar.bar_format + " - Downloaded successfully" + RESET
                bar.refresh()
    except Exception as e:
        bar.bar_format = GREEN + bar.bar_format + f" - Error : {str(e)}" + RESET
        bar.refresh()
        return False

    return True


def get_chapters_from_list(chapters_list: list[tuple[int, tqdm]]):
    for chapter, bar in chapters_list:
        get_chapter(chapter, bar)


def get_chapters_in_threads(min_chapter: int, max_chapter: int) -> bool:
    if min_chapter > max_chapter:
        log(f"Min chapter ({min_chapter}) lower than max chapter ({max_chapter})", color=RED)
        return False

    bars = [ get_bar(chapter, abs(chapter-max_chapter)) for chapter in range(min_chapter, max_chapter+1) ]
    threads = []
    for chapter in range(min_chapter, min_chapter + MAX_THREADS):
        t = Thread(target=get_chapters_from_list,  args=[ [ (n, bars[n-min_chapter]) for n in range(chapter, max_chapter+1, MAX_THREADS) ] ])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


def send_windows_notification(start_chapter: int, end_chapter: int):
    title: str = "Scans Downloader"
    icons: list[str] = os.listdir(ONE_PIECE_ICONS_FOLDER)
    rand_icon: str = os.path.join(ONE_PIECE_ICONS_FOLDER, icons[random.randint(0, len(icons) - 1)])
    button: dict = {"activationType": "protocol", "arguments": os.path.join(SCANS_FOLDER_PATH, str(start_chapter)), "content": "Open folder"}
    body: str

    if start_chapter == end_chapter:
        body=f"New {MANGA} Chapter {start_chapter} !"
    else:
        body=f"New {MANGA} Chapters {start_chapter}-{end_chapter} !"

    toast(title, body=body, icon=rand_icon, button=button)

    return


def daily_routine():
    max_chapter: int

    try: max_chapter = int(max(os.listdir(SCANS_FOLDER_PATH))) + 1
    except FileNotFoundError: return False

    min_chapter: int = max_chapter
    while get_chapter(max_chapter, get_bar(max_chapter)) == True:
        max_chapter += 1

    if max_chapter > min_chapter:
        send_windows_notification(min_chapter, max_chapter - 1)

    return True


if __name__ == "__main__":
    argc: int = len(argv) - 1

    if argc == 0:
        daily_routine()
    elif argc == 1:
        chapter: int = int(argv[1])
        get_chapter(chapter, get_bar(chapter))
    elif argc == 2:
        min_chapter: int = int(argv[1])
        max_chapter: int = int(argv[2])
        get_chapters_in_threads(min_chapter, max_chapter)