==============
parish_scraper
==============


A collection of web-scraping bots which collect burial data from transcribed parish records.

Install:
========
1. clone
2. ``pip install -r requirements.txt``
3. install chromedriver: https://chromedriver.chromium.org/downloads, ensure version matches chrome.
4. reccomended: modify chromedriver.exe to obfuscate selenium. 

To modify chromedriver.exe, in command line:
============================================
1. ``vim <path to chromedriver.exe>``
2. ``:%s/cdc_/abc_/g``
3. ``:wq!`` and press ``return``

Use:
====
FamilySearch.org
================
1. add environment variables: ``FS_USERNAME`` and ``FS_PASSWORD``.
2. as code:
  ``bot = FamilySearchScraper()``
  
  ``bot.authenticate()``
  
  ``bot.get_burial_records(<place_name>, <start_year>, <end_year>)``
  
Ancestry.co.uk
==============
WARNING: automated software such as this violates Ancestry's use of services agreement. 
Usage of this software is at the users own risk and the user accepts all liability.

1. add environment variables: ``ANC_USERNAME`` and ``ANC_PASSWORD``.
2. as code:
  ``bot = AncestryScraper()``
  
  ``bot.authenticate()``
  
  ``bot.get_parish_urls(<collection_code>)``
  
  ``bot.scrape_collection()``
To-do:
======
- Tests
