# stash-c4s-pyscraper
# THIS PLUGIN IS NOW DEPRECATED DUE TO CHANGES TO THE C4S SITE - PLEASE DO NOT USE
## The plugin has been left on Github for posterity, or in case any of its component code is of any use. It's all open-source - feel free to rip it apart and cannibalise it for any purpose
Python-based Clips4Sale scraper for Stash

## Dependencies
This is a Python scraper, and as such, Python (Python3) needs to be installed.
- The official Stash docker container already contains python and all needed modules.
- For Windows systems, install python from [python.org](https://www.python.org/downloads/windows/) ([instructions](https://phoenixnap.com/kb/how-to-install-python-3-windows)), NOT from the Windows store.
- For Linux systems please consult the relevant distro instructions.
- For Μac systems either use homebrew eg `brew install python3` or use the python.org installer ([instructions](https://www.lifewire.com/how-to-install-python-on-mac-4781318))

## pip requirements
- bs4
- lxml
- requests

## Features
- Addresses a bug where descriptions are sometimes rendered without apostrophes. This is achieved by pulling in the description from an alternative source (l.clips4sale.com as opposed to clips4sale.com) and combining the two sources into one perfect description. It compares the description word-by-word from each source, and if there's a mismatch, replaces it with the word from l.clips4sale.com (i.e. the one with apostrophes).
- Strips errant HTML tags from the text of the description.
- Replaces single quotation marks with apostrophes, preventing instances of "don‘t" or "don’t", etc, and replacing them with "don't".
- Introduced a fallback for thumbnail processing. There appears to be two types of thumbnail for C4S content - one is a static thumbnail (most likely a custom thumbnail uploaded by the content creator) and the other is a still frame from a GIF preview. This script favours the static thumbnail, and falls back to the GIF still frame if that isn't available. In short, there should always be a picture of some sort this time. No more missing images.
- Line breaks are now processed correctly. Before, there were instances of paragraphs immediately following on from one another (not even leaving a space) - this should now be rectified.

## Pitfalls
- I have tested this on a couple of hundred video clips, and the only issue I've encountered is the occasional 'Invariant violation' error - this happens in about one in every 50-100 scrapes or so, and can be rectified by just running the scraper again.
- Takes quite a bit longer than the YML/Xpath based scraper. It's probably quite inefficient code - I think there are three calls made to the C4S website. I'm sure this could be slimmed down.

## Special thanks
I'd like to thank the writers of the following scrapers on the CommunityScrapers git repository - their code has proven very useful in helping this come together:
- bnkai, who wrote the ManyVids Python scraper: https://github.com/stashapp/CommunityScrapers/commits/master/scrapers/ManyVids
- The numerous contributors (who include halorrr, peolic, bnkai, Belleyy, JackDawson94 and DoctorD1501 at the time of writing) to the Clips4Sale YML/Xpath based scraper: https://github.com/stashapp/CommunityScrapers/commits/master/scrapers/Clips4Sale.yml. The search code from this original scraper has been implemented in this version.
- estellaarrieta, who wrote the WowNetworkVenus Python scraper, from which I managed to work out a lot about the structure of Python scrapers, etc.

Also, mention has to go to ChatGPT, without which I wouldn't have been able to fumble blindly through this project.
