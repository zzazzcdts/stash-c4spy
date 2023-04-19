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
    # Import Stash logging system from py_common
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo. (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    # Import necessary modules.
    from lxml import html
    import requests
    import re
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup

    # Establish a requests session with a timeout of 5 seconds.
    session = requests.Session()
    timeout = 5

# If one of these modules is not installed:
except ModuleNotFoundError:
    log.error(
        "You need to install the python modules mentioned in requirements.txt"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal from the directory the scraper is located: pip install -r requirements.txt"
    )
    sys.exit()


# This function repairs the description, using text from the standard clips4sale.com site, and the l.clips4sale.com version.
# The standard site has the correct spacing, but sometimes strips apostrophes from words, whereas the l.clips4sale.com version has the correct text, but formatted as one large lump of text.
# This function cross-references both to get one canonical description.
def repair_description(base, lversion):
    # Split the text of both versions into separate words
    pattern = "(?<![\n\.]) {2}"
    base = re.sub(pattern, " ~~DOUBLESPACE~~ ", base)
    lversion = re.sub(pattern, " ~~DOUBLESPACE~~ ", lversion)
    base_words = base.split()
    l_words = lversion.split()

    # If there is a word mismatch, replace with version from the l.clips4sale.com site.
    try:
        # Loop over all words in the standard clips4sale site.
        for i in range(len(base_words)):
            # If the word from the standard site and the word from the l.clips4sale.com version do not match:
            if base_words[i] != l_words[i]:
                # If the current word contains a full stop:
                if '.' in base_words[i]:
                    # Replace the full stop with a full stop followed by a space.
                    base_words_fixed = base_words[i].replace('.', '. ')
                    # If there are three dots (i.e. an ellipses):
                    if '. . . ' in base_words_fixed:
                        # Join the three dots together.
                        base_words_fixed = base_words_fixed.replace('. . . ', '...')
                    # Replace the word with the version with the corrected full stops/ellipses.
                    base = base.replace(base_words[i], base_words_fixed.rstrip())
                # If the word being processed is 2 characters or longer:
                if len(base_words[i]) >= 2 and len(l_words[i]) >= 2:
                    # If the first and last character of both the standard and l.clips4sale.com version of the word match:
                    if base_words[i][:1] == l_words[i][:1] and base_words[i][-1] == l_words[i][-1]:
                        # Replace the word with the version from l.clips4sale.com
                        base = base.replace(base_words[i], l_words[i])
                    if base_words[i] == "~~DOUBLESPACE~~" and l_words[i] != "~~DOUBLESPACE~~":
                        base = base.replace(base_words[i], l_words[i])
                    else:
                        base = base.replace(base_words[i], "[CENSORED]")
    # If there is an indexing error, just skip the word.
    except IndexError:
        pass

    return base


# This function removes all HTML tags from the plain text of the description. Sometimes these leak through.
def strip_html_tags(description):
    # Remove HTML tags using regular expressions
    clean_text = re.compile('<.*?>')
    return re.sub(clean_text, '', description)


# This function replaces all single quotation marks with apostrophes.
def fix_single_quotes(description):
    # Replace single quotation marks (both left and right) with an apostrophe.
    description = description.replace('\u2018', '\u0027').replace('\u2019', '\u0027')
    return description


# Retrieve l.clips4sale.com link from original link.
def get_l_url(url):
    # Break the URL down into its core components.
    scheme, netloc, path = urlparse(url)[:3]
    # If the URL starts with "www.", remove this.
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # Split the URL by /
    path_parts = path.split("/")
    # Get the second-to-last part of the path - the clip ID number.
    last_path = path_parts[-2]
    # Generate the URL.
    new_url = f"https://l.clips4sale.com/clip/{last_path}"
    return new_url


# Retrieve text from the original C4S link. This version includes the correct spacing, but doesn't always include the correct apostrophes.
def get_base_description(url):
    # Send a GET request to the URL.
    response = session.get(url, timeout=timeout)

    # Create a BeautifulSoup object to parse the HTML content
    soup = BeautifulSoup(response.content, 'lxml')

    # Find the div tag with the class individualClipDescription
    div_tag = soup.find('div', {'class': 'individualClipDescription'})

    # Extract the text content of the div tag
    c4s_base_text = div_tag.get_text(separator='\n').rstrip().lstrip().replace("\n\n\n", "\n")

    # If there is text enclosed in <em> or <strong> tags in the description, add a newline after these tags so the sentences don't crash into each other.
    for tag in div_tag.find_all(['em', 'strong']):
        c4s_base_text = c4s_base_text.replace(str(tag), f"\n{tag}\n")

    return c4s_base_text


# Retrieve text from l.clips4sale.com version of the website. This version includes correct apostrophes, etc., but does not include the correct spacing.
def get_l_description(url):
    # Send a GET request to the URL
    response = session.get(url, timeout=timeout)
    # Create a BeautifulSoup object to parse the HTML content
    soup = BeautifulSoup(response.content, 'lxml')
    # Find the span tag with the class show_more
    span_tag = soup.find('span', {'class': 'show_more show_more_js'})
    # Extract the data-text attribute of the span tag
    c4s_l_text = span_tag['data-text']
    return c4s_l_text


# Function which generates a good description from a given Clips4sale link.
def get_good_description(url_to_process):
    # Get the base description from the standard Clips4sale site.
    basetext = get_base_description(url_to_process)
    # Get the URL for the l.clips4sale.com version of the site.
    l_url = get_l_url(url_to_process)
    # Get the description from the l.clips4sale.com version of the site.
    try:
        ltext = get_l_description(l_url)
    except TypeError as e:
        log.error("Missing l.clips4sale.com link, reverting to using base link description.")
        basetext = strip_html_tags(basetext)
        basetext = fix_single_quotes(basetext)
        return basetext
    # Call the description repair function.
    fixed = repair_description(basetext, ltext)
    # Strip HTML tags.
    fixed = strip_html_tags(fixed)
    # Replace single quotes with apostrophes.
    fixed = fix_single_quotes(fixed)
    return fixed


def output_json(title, tags, url, image, studio, performers, description, date):
    # Split the tags into a list (comma-separated), stripping away any trailing full stops or tags which are just "N/A"
    tag_list = [tag.strip().rstrip('.') for tag in tags.split(",") if tag.strip() != "N/A"]
    # Split the performers into a list (comma-separated), stripping away any trailing full stops.
    performer_list = [performer.strip().rstrip('.') for performer in performers.split(",")]
    # Create a tag dictionary from the tag list.
    tag_dicts = [{"name": tag} for tag in tag_list]
    # Create a performer dictionary from the performer list.
    performer_dicts = [{"name": performer} for performer in performer_list]
    # Dump all of this as JSON data.
    return json.dumps({
        "title": title,
        "tags": tag_dicts,
        "url": url,
        "image": image,
        "studio": {"name": studio},
        "performers": performer_dicts,
        "details": description,
        "date": date
    }, indent=4)


def scrape_scene(scene_url: str, session: requests.Session) -> dict:
    scrape = {}

    # Use the provided session object
    response = session.get(scene_url)
    soup = BeautifulSoup(response.content, 'lxml')

    # Title parsing
    title_element = soup.find('h3', {'class': '[ text-white mt-3-0 mb-1-0 text-2-4 ]'})
    title_pre_regex = title_element.text.rstrip()
    regex_pattern = r"(?i)[ \t]*((Super )?[SH]D)?[ ,-]*(\b(MP4|OPTIMUM|WMV|MOV|AVI|UHD|[48]K)\b|1080p|720p|480p|\(1080 HD\)|\(720 HD\)(Standard|High) Def(inition)?)+[ \t]*"
    title_processed = re.sub(regex_pattern, "", title_pre_regex)
    scrape['title'] = title_processed.rstrip(" -")

    # Date parsing
    added_section = soup.select_one('span:-soup-contains("Added:")')
    date_time_str = added_section.select_one('span.text-white').text.strip()
    date_obj = datetime.strptime(date_time_str, '%m/%d/%y %I:%M%p')
    scrape['date'] = date_obj.strftime('%Y-%m-%d')

    # Thumbnail parsing
    img_tag = soup.find('img', class_='clip_thumb_img')
    if img_tag:
        scrape['image'] = "https:" + img_tag['src']
    else:
        video_tag = soup.find('video')
        scrape['image'] = "https:" + video_tag['poster']

    # Studio parsing
    from_span = soup.find('span', {'class': 'font-bold'}, string='From: ')
    studio_link = from_span.find_next_sibling('a')
    scrape['studio'] = studio_link.get_text().replace('  ', ' ')

    # Tag parsing
    # Parse category
    category_span = soup.find('span', {'class': 'font-bold'}, string='Category: ')
    category_link = category_span.find_next_sibling('a')
    category = category_link.text.strip()

    # Parse 'Related Categories' and 'Keywords' sections
    related_links_span = soup.find_all('span', {'class': 'relatedCatLinks'})
    related_links_text = f"{category}, " + ", ".join(span.get_text().strip().rstrip(".") for span in related_links_span)
    scrape['tags'] = related_links_text.rstrip(', ')

    # Performer parsing
    # Using the same principles from the original YAML/xpath scraper - the performer details may be in the keyword tags.
    keywords_span = soup.find('span', {'class': '[ font-bold ]'}, string='Keywords: ')
    if keywords_span:
        # find the next sibling span element with class 'relatedCatLinks'
        related_span = keywords_span.find_next_sibling('span', {'class': 'relatedCatLinks'})
        # get the text of the related span
        scrape['performers'] = related_span.get_text().rstrip('.').lstrip(', ')
    scrape['performers'] += ", " + scrape['studio']

    # Description parsing
    scrape['description'] = get_good_description(scene_url).strip()

    json = output_json(scrape['title'], scrape['tags'], scene_url, scrape['image'], scrape['studio'],
                       scrape.get('performers', ''), scrape['description'], scrape['date'])

    print(json)


def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    name = fragment.get("title")
    if url is None and name is None:
        log.error("No URL/Name provided")
        sys.exit(1)
    scrape_scene(url, session)


if __name__ == "__main__":
    main()

# Last updated 2023-04-19
