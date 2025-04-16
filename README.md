MAKEXML.py
  This file takes a list of start pages in urls.txt and crawls each one recusively to make an XML sitemap for each.
  - Creates a separate xml sitemap for every site in your urls.txt file
  - Crawls recusively
  - limited ONLY to urls on the same subdomain as what you have in urls.txt
  - ignores any #fragments in URLs.
  - future todo: ingore URLs with different canonical
  - crawl better than BeautifulSoup

CRUX.py
  This file lets you quickly run google page speed insights for a list of URLs using the Google API. See instructions in the file.

RUNLOCAL.py
  I needed a way to locally run my google cloud run functions - but to treat them as if they were an API. I figured this might be useful for others. 
