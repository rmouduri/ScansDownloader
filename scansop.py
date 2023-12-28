from sys import argv
from csv import reader
import requests
from bs4 import BeautifulSoup
import os


def get_scans(start_chapter, end_chapter):
    fail_list = []
    start_chapter -= 1

    while start_chapter < end_chapter:
        start_chapter += 1
        url = f'https://www.lelmanga.com/one-piece-{start_chapter}'
        response = requests.get(url)

        try:
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                if not os.path.exists("one_piece_scans_fr"):
                    os.makedirs("one_piece_scans_fr")

                readerarea = soup.find('div', {'id': 'readerarea'})
                img_tags = readerarea.find_all('img')

                page = 0
                for img in img_tags:
                    img_url = img.get("src")

                    if img_url:
                        extension = os.path.splitext(img_url)[1]
                        img_data = requests.get(img_url).content
                        page += 1

                        if not os.path.exists(f"one_piece_scans_fr/{start_chapter}"):
                            os.makedirs(f"one_piece_scans_fr/{start_chapter}")

                        with open(os.path.join(f"one_piece_scans_fr/{start_chapter}/OP-{start_chapter}-{page}{extension}", ), "wb") as f:
                            f.write(img_data)

                print(f"{start_chapter}: Success.")
            else:
                print(f"{start_chapter}: Failed to retrieve the webpage. Status code:", response.status_code)
                fail_list.append(start_chapter)

        except Exception as e:
            print(f'Error {start_chapter}: {str(e)}')
            fail_list.append(start_chapter)
    
    return fail_list


if __name__ == "__main__":
    if len(argv) == 2 and argv[1].isnumeric():
        error = get_scans(int(argv[1]), int(argv[1]))
        print(error)
    elif len(argv) == 3 and argv[1].isnumeric() and argv[2].isnumeric():
        error = get_scans(int(argv[1]), int(argv[2]))
        print(error)
    else:
        print(
            "\nInvalid arguments.\n",
            "Usage:\n",
            "\tscansop.py [chapter_number_to_download]\n"
            "\tscansop.py [starting_chapter_number_to_download] [ending_chapter_number_to_download]\n",
            sep=''
        )