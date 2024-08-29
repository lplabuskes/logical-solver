from problem import Problem
from typing import List
from bs4 import BeautifulSoup
import re


HLABEL_CLASS = "labelboxh"
CLUE_CLASS = "clue"

def find_items(html: str) -> List[List[str]]:
    soup = BeautifulSoup(html, "html.parser")
    hlabels = soup.find_all(class_=HLABEL_CLASS)
    categories = {}
    for obj in hlabels:
        cat_idx = ord(obj.attrs["id"][9]) - 65
        obj_idx = int(obj.attrs["id"][10:]) - 1
        if cat_idx not in categories:
            categories[cat_idx] = [(obj_idx, obj.text.replace("\xa0", " "))]
        else:
            categories[cat_idx].append((obj_idx, obj.text.replace("\xa0", " ")))
    for key, value in categories.items():
        in_order = [txt for _, txt in sorted(value)]
        categories[key] = in_order

    # Category B isn't in the horizontal labels
    pattern = re.compile('labelb_ary\[[0-9]+\] = "(.*)";')
    results = pattern.findall(html)
    categories[1] = [r.replace("\xa0", " ") for r in results]
    
    items_out = []
    for i in range(len(categories)):
        items_out.append(categories[i])

    return items_out


def find_clues(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    clues = soup.find_all(class_=CLUE_CLASS)
    clues = [clue.text for clue in clues]
    return clues


def parse_problem_html(html: str) -> Problem:
    clues = find_clues(html)
    items = find_items(html)
    n_cat = len(items)
    n_item = len(items[0])
    prob = Problem(n_cat, n_item, clues)

    for i, cat in enumerate(items):
        for j, name in enumerate(cat):
            prob.categories[i].set_name(j, name)
    prob.parse_clues()
    
    return prob


def problem_from_path(path: str) -> Problem:
    # Want to eventually handle images
    # Currently this is all designed to work with source html from puzzlebaron.com
    if path.endswith(".html"):
        with open(path, "r") as f:
            html = f.read()
        return parse_problem_html(html)


if __name__ == "__main__":
    with open(".\\problem.html", "r") as f:
        html = f.read()
    find_clues(html)
