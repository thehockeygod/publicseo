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

FANOUT.py
  Uses Gemini API. Enter a query and it will show you the query fanout and citations.  Useful for a quick check, or as part of an automated routine.


GPT_BROWSER_VIEW.py
  Shows the text that OpenAI's gpt-oss browser tool would see on your page. Uses the same HTML-to-text code from their GitHub repo, so you can check what the model actually reads.
  - Outputs the page in 1024-token "screens," the same way the model reads it
  - Links show as 【id†text】 and images as [Image N: alt text]. Images with no alt text are just [Image N]
  - --full prints the whole page in one block, --links lists the link IDs the model can "click"
  - Fetches your page directly by default. Use --backend exa or --backend youcom (needs an API key) to make the exact API call gpt-oss uses
  - Doesn't run JavaScript, so content rendered client-side won't show up
  - pip install aiohttp html2text lxml tiktoken
