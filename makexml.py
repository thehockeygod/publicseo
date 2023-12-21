#requires a .txt file called urls.txt with one home page (or crawl start page) per line
#This file will crawl every URL in urls.txt recusively looking for only URLs on the same subdomain, and make an XML sitemap of them.

import os
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree

def extract_domain(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"

def create_sitemap(root_url, all_links):
    root = Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    for link in all_links:
        url_elem = SubElement(root, "url")
        loc_elem = SubElement(url_elem, "loc")
        loc_elem.text = link

    tree = ElementTree(root)
    filename = f"sitemap_{root_url.replace('://', '_').replace('/', '_')}.xml"
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"Sitemap created for {root_url}")

def crawl_and_create_sitemap(root_url_list_file):
    with open(root_url_list_file, "r") as file:
        root_urls = file.read().splitlines()

    for root_url in root_urls:
        domain = extract_domain(root_url)
        all_links = set()
        crawl_recursive(root_url, domain, all_links)
        create_sitemap(root_url, list(all_links))

def crawl_recursive(url, domain, all_links, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()

    if url in visited_urls or not url.startswith(domain):
        return

    try:
        print(f"Crawling {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = {urljoin(url, a.get("href")) for a in soup.find_all("a", href=True)}

        all_links.update(links)
        visited_urls.add(url)

        for link in links:
            if link.startswith(domain) and link not in visited_urls:
                crawl_recursive(link, domain, all_links, visited_urls)
    except Exception as e:
        print(f"Error processing {url}: {e}")

if __name__ == "__main__":
    root_url_list_file = "urls.txt"
    crawl_and_create_sitemap(root_url_list_file)
