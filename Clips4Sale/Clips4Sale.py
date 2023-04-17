import os
import sys
import json
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo. (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    from lxml import html
    import requests
    import re
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    log.error(
        "You need to install the python modules mentioned in requirements.txt"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal from the directory the scraper is located: pip install -r requirements.txt"
    )
    sys.exit()


def repair_description(base, lversion):
    # split the text of both versions into separate words
    base_words = base.split()
    l_words = lversion.split()

    # If there is a word mismatch, replace with version from the l.clips4sale.com site.
    try:
        for i in range(len(base_words)):
            if base_words[i] != l_words[i]:
                base = base.replace(base_words[i], l_words[i])
    except IndexError:
        return base

    return base


def strip_html_tags(description):
    # Remove HTML tags using regular expressions
    clean_text = re.compile('<.*?>')
    return re.sub(clean_text, '', description)


def fix_single_quotes(description):
    description = description.replace('\u2018', '\u0027').replace('\u2019', '\u0027')
    return description


# Retrieve l.clips4sale.com link from original link.
def get_l_url(url):
    scheme, netloc, path = urlparse(url)[:3]  # parse the URL into its components
    if netloc.startswith("www."):
        netloc = netloc[4:]  # remove the "www." prefix if it exists
    path_parts = path.split("/")
    last_path = path_parts[-2]  # get the second-to-last part of the path
    new_url = f"{scheme}://l.{netloc}/clip/{last_path}"
    return new_url


# Retrieve text from the original C4S link. This version includes the correct spacing, but doesn't always include the correct apostrophes.
def get_base_description(url):
    # send a GET request to the URL
    response = requests.get(url)

    # create a BeautifulSoup object to parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # find the div tag with the class individualClipDescription
    div_tag = soup.find('div', {'class': 'individualClipDescription'})

    # extract the text content of the div tag
    c4s_base_text = div_tag.get_text()

    return c4s_base_text


# Retrieve text from l.clips4sale.com version of the website. This version includes correct apostrophes, etc., but does not include the correct spacing.
def get_l_description(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    span_tag = soup.find('span', {'class': 'show_more show_more_js'})
    c4s_l_text = span_tag['data-text']
    return c4s_l_text


def get_good_description(url_to_process):
    basetext = get_base_description(url_to_process)
    l_url = get_l_url(url_to_process)
    ltext = get_l_description(l_url)
    fixed = repair_description(basetext, ltext)
    fixed = strip_html_tags(fixed)
    fixed = fix_single_quotes(fixed)
    return fixed


def output_json(title, tags, url, image, studio, performers, description):
    tag_list = tags.split(", ")
    tag_dicts = [{"name": tag} for tag in tag_list]
    performer_list = performers.split(", ")
    performer_dicts = [{"name": performer} for performer in performer_list]

    return json.dumps({
        "title": title,
        "tags": tag_dicts,
        "url": url,
        "image": image,
        "studio": {"name": studio},
        "performers": performer_dicts,
        "details": description
    })


def scrape_scene(scene_url: str) -> dict:
    # vars to set:
    # scrape['studio']
    # scrape['performers']
    scrape = {}

    # Grab page using BS4
    response = requests.get(scene_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Title parsing
    scrape['title'] = soup.find('h3', {'class': '[ text-white mt-3-0 mb-1-0 text-2-4 ]'}).text.rstrip()

    # Date parsing
    added_section = soup.select_one('span:-soup-contains("Added:")')
    date_time_str = added_section.select_one('span.text-white').text.strip()
    date_obj = datetime.strptime(date_time_str, '%m/%d/%y %I:%M%p')
    scrape['date'] = date_obj.strftime('%Y-%m-%d').rstrip()

    # Thumbnail parsing
    try:
        img_tag = soup.find('img', class_='clip_thumb_img')
        scrape['image'] = "https:" + img_tag['src']
    except:
        video_tag = soup.find('video')
        scrape['image'] = "https:" + video_tag['poster']

    # Studio parsing
    from_span = soup.find('span', {'class': 'font-bold'}, string='From: ')
    studio_link = from_span.find_next_sibling('a')
    scrape['studio'] = studio_link.get_text().replace('  ', ' ')

    # Tag parsing
    related_links_span = soup.find_all('span', {'class': 'relatedCatLinks'})
    related_links_text = ""
    for span in related_links_span:
        texttoadd = span.get_text().rstrip().lstrip().rstrip(".")
        related_links_text += texttoadd + ", "
    related_links_text = related_links_text.rstrip().rstrip('.').lstrip().rstrip(", ")
    scrape['tags'] = related_links_text

    # Performer parsing
    # Using the same principles from the original YAML/xpath scraper - the performer details may be in the keyword tags.
    keywords_span = soup.find('span', {'class': '[ font-bold ]'}, string='Keywords: ')
    if keywords_span:
        # find the next sibling span element with class 'relatedCatLinks'
        related_span = keywords_span.find_next_sibling('span', {'class': 'relatedCatLinks'})

        # get the text of the related span
        scrape['performers'] = related_span.get_text().rstrip().rstrip('.').lstrip().rstrip(", ")

    # Description parsing
    scrape['description'] = get_good_description(scene_url).rstrip().lstrip()

    json = output_json(scrape['title'], scrape['tags'], scene_url, scrape['image'], scrape['studio'],
                       scrape['performers'], scrape['description'])

    print(json)


def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    name = fragment.get("title")
    if url is None and name is None:
        log.error("No URL/Name provided")
        sys.exit(1)
    scrape_scene(url)


if __name__ == "__main__":
    main()

# Last updated 2023-04-17