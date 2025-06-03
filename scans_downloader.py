from bs4 import BeautifulSoup
import os
import random
import requests
from sys import argv
from threading import Thread
from win11toast import toast


GREEN: str = "\033[92m"
RED: str = "\033[91m"
RESET: str = "\033[0m"
MAX_THREADS: int = 20

LANG: str = "FR"
MANGA: str = "One Piece"
WEBSITE: str = "https://www.lelmanga.com"

SCANS_FOLDER_NAME: str = f"{MANGA} Scans {LANG}"
RESOURCES_FOLDER_NAME: str = "resources"
ICONS_FOLDER_NAME: str = "icons"

SCANS_FOLDER_PATH: str = os.path.join(os.getcwd(), SCANS_FOLDER_NAME)
RESOURCES_FOLDER: str = os.path.join(os.getcwd(), RESOURCES_FOLDER_NAME)
ICONS_FOLDER: str = os.path.join(RESOURCES_FOLDER, ICONS_FOLDER_NAME)
ONE_PIECE_ICONS_FOLDER: str = os.path.join(ICONS_FOLDER, MANGA)


def log(s: str, color: str = ""):
    print(f"{color}[ScansDownloader]", s, flush=True, end=f"{RESET}\n")


def get_chapter(chapter: int) -> bool:
    url: str = f"{WEBSITE}/{MANGA.lower().replace(' ', '-')}-{chapter}"
    response = requests.get(url)

    if response.status_code != 200:
        log(f"[Chapter {chapter}] Failed to retrieve the webpage. Status code: {response.status_code}", color=RED)
        return False

    log(f"Downloading chapter {chapter}...")
    try:
        soup = BeautifulSoup(response.content, "html.parser")

        if not os.path.exists(SCANS_FOLDER_PATH):
            try: os.makedirs(SCANS_FOLDER_PATH)
            except: pass

        readerarea = soup.find("div", {"id": "readerarea"})
        imgTags = readerarea.find_all("img")

        for page, img in enumerate(imgTags, start=1): # start=1 as lelmanga adds an image of their website as 1st image
            imgUrl = img.get("src")

            if imgUrl:
                extension = os.path.splitext(imgUrl)[1]
                imgData = requests.get(imgUrl).content

                chapter_path: str = os.path.join(SCANS_FOLDER_PATH, str(chapter))
                if not os.path.exists(chapter_path):
                    os.makedirs(chapter_path)

                page_filename: str = f"OP-{chapter}-{page}{extension}"
                with open(os.path.join(chapter_path, page_filename), "wb") as f:
                    f.write(imgData)

        log(f"Chapter {chapter} downloaded successfully.", color=GREEN)
    except Exception as e:
        log(f"Error {chapter}: {str(e)}", color=RED)
        return False

    return True


def get_chapters_from_list(chapters_list: list[int]):
    for chapter in chapters_list:
        get_chapter(chapter)


def get_chapters_in_threads(min_chapter: int, max_chapter: int) -> bool:
    if min_chapter > max_chapter:
        log(f"Min chapter ({min_chapter}) lower than max chapter ({max_chapter})", color=RED)
        return False
    
    threads = []
    for chapter in range(min_chapter, min_chapter + MAX_THREADS):
        t = Thread(target=get_chapters_from_list,  args=[[n for n in range(chapter, max_chapter+1, MAX_THREADS)]])
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
    while get_chapter(max_chapter) == True:
        max_chapter += 1

    if max_chapter > min_chapter:
        send_windows_notification(min_chapter, max_chapter - 1)

    return True


if __name__ == "__main__":
    argc: int = len(argv) - 1

    if argc == 0:
        daily_routine()
    elif argc == 1:
        get_chapter(int(argv[1]))
    elif argc == 2:
        get_chapters_in_threads(int(argv[1]), int(argv[2]))