#!/usr/bin/env python3
"""
Show the text that gpt-oss's `browser` tool would show the model for a URL.

Reproduces the page-processing pipeline from openai/gpt-oss
(gpt_oss/tools/simple_browser/, commit 5681a6b, Apache-2.0):
  page_contents.process_html  -> HTML to plaintext, links become 【id†text】
  simple_browser_tool.show_page -> 80-col wrap, "L{n}:" line numbers,
                                   ~1024-token "screens" (view_tokens)

Where the HTML comes from (--backend):
  direct  - fetch the page yourself (no API key). Closest to "what's in your HTML".
  exa     - same call gpt-oss's ExaBackend makes (needs EXA_API_KEY).
  youcom  - same call gpt-oss's YouComBackend makes (needs YDC_API_KEY).
Neither gpt-oss nor this script runs JavaScript, so content rendered client-side
won't appear with --backend direct. Exa/You.com use their own crawlers.

Install:  pip install aiohttp html2text lxml tiktoken
Usage:    python gpt_browser_view.py https://example.com
          python gpt_browser_view.py https://example.com --full
          EXA_API_KEY=... python gpt_browser_view.py https://example.com --backend exa
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import os
import re
import sys
import textwrap
from urllib.parse import unquote, urljoin, urlparse

import aiohttp
import html2text
import lxml.etree
import lxml.html
import tiktoken

ENC_NAME = "o200k_base"
VIEW_TOKENS = 1024
USER_AGENT = "gpt-oss/0.0.8"

# --------------------------------------------------------------------------
# Copied from gpt_oss/tools/simple_browser/page_contents.py
# --------------------------------------------------------------------------

HTML_SUP_RE = re.compile(r"<sup( [^>]*)?>([\w\-]+)</sup>")
HTML_SUB_RE = re.compile(r"<sub( [^>]*)?>([\w\-]+)</sub>")
HTML_TAGS_SEQ_RE = re.compile(r"(?<=\w)((<[^>]*>)+)(?=\w)")
WHITESPACE_ANCHOR_RE = re.compile(r"(【\@[^】]+】)(\s+)")
EMPTY_LINE_RE = re.compile(r"^\s+$", flags=re.MULTILINE)
EXTRA_NEWLINE_RE = re.compile(r"\n(\s*\n)+")


def get_domain(url: str) -> str:
    if "http" not in url:
        url = "http://" + url
    return urlparse(url).netloc


def multiple_replace(text: str, replacements: dict[str, str]) -> str:
    regex = re.compile("(%s)" % "|".join(map(re.escape, replacements.keys())))
    return regex.sub(lambda mo: replacements[mo.group(1)], text)


def _replace_special_chars(text: str) -> str:
    return multiple_replace(text, {"【": "〖", "】": "〗", "◼": "◾", "​": ""})


def merge_whitespace(text: str) -> str:
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text)


def arxiv_to_ar5iv(url: str) -> str:
    return re.sub(r"arxiv.org", r"ar5iv.org", url)


def _get_text(node) -> str:
    return merge_whitespace(" ".join(node.itertext()))


def replace_node_with_text(node, text: str) -> None:
    previous = node.getprevious()
    parent = node.getparent()
    tail = node.tail or ""
    if previous is None:
        parent.text = (parent.text or "") + text + tail
    else:
        previous.tail = (previous.tail or "") + text + tail
    parent.remove(node)


def _clean_links(root, cur_url: str) -> dict[str, str]:
    cur_domain = get_domain(cur_url)
    urls: dict[str, str] = {}
    urls_rev: dict[str, str] = {}
    for a in root.findall(".//a[@href]"):
        link = a.attrib["href"]
        if link.startswith(("mailto:", "javascript:")):
            continue
        text = _get_text(a).replace("†", "‡")
        if not re.sub(r"【\@([^】]+)】", "", text):  # Probably an image
            continue
        if link.startswith("#"):
            replace_node_with_text(a, text)
            continue
        try:
            link = urljoin(cur_url, link)
            domain = get_domain(link)
        except Exception:
            domain = ""
        if not domain:
            continue
        link = arxiv_to_ar5iv(link)
        if (link_id := urls_rev.get(link)) is None:
            link_id = f"{len(urls)}"
            urls[link_id] = link
            urls_rev[link] = link_id
        if domain == cur_domain:
            replacement = f"【{link_id}†{text}】"
        else:
            replacement = f"【{link_id}†{text}†{domain}】"
        replace_node_with_text(a, replacement)
    return urls


def replace_images(root) -> None:
    for cnt, img_tag in enumerate(root.findall(".//img")):
        image_name = img_tag.get("alt", img_tag.get("title"))
        replacement = f"[Image {cnt}: {image_name}]" if image_name else f"[Image {cnt}]"
        replace_node_with_text(img_tag, replacement)


def _remove_math(root) -> None:
    for node in root.findall(".//math"):
        node.getparent().remove(node)


def remove_unicode_smp(text: str) -> str:
    return re.sub(r"[\U00010000-\U0001FFFF]", "", text)


def html_to_text(html: str) -> str:
    html = re.sub(HTML_SUP_RE, r"^{\2}", html)
    html = re.sub(HTML_SUB_RE, r"_{\2}", html)
    html = re.sub(HTML_TAGS_SEQ_RE, r" \1", html)
    # gpt-oss monkey-patches html2text to skip markdown escaping
    orig_md, orig_md_section = html2text.utils.escape_md, html2text.utils.escape_md_section
    html2text.utils.escape_md = lambda text: text
    html2text.utils.escape_md_section = lambda text, snob=False: text
    try:
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.body_width = 0
        h.ignore_tables = True
        h.unicode_snob = True
        h.ignore_emphasis = True
        return h.handle(html).strip()
    finally:
        html2text.utils.escape_md = orig_md
        html2text.utils.escape_md_section = orig_md_section


def process_html(html: str, url: str, title: str | None, display_urls: bool = True):
    html = remove_unicode_smp(html)
    html = _replace_special_chars(html)
    root = lxml.html.fromstring(html)

    title_element = root.find(".//title")
    if title:
        final_title = title
    elif title_element is not None:
        final_title = title_element.text or ""
    elif url and (domain := get_domain(url)):
        final_title = domain
    else:
        final_title = ""

    urls = _clean_links(root, url)
    replace_images(root)
    _remove_math(root)
    clean_html = lxml.etree.tostring(root, encoding="UTF-8").decode()
    text = html_to_text(clean_html)
    text = re.sub(WHITESPACE_ANCHOR_RE, lambda m: m.group(2) + m.group(1), text)
    text = re.sub(EMPTY_LINE_RE, "", text)
    text = re.sub(EXTRA_NEWLINE_RE, "\n\n", text)

    if display_urls:
        text = f"\nURL: {url}\n" + text
    return final_title, text, urls


# --------------------------------------------------------------------------
# Copied from gpt_oss/tools/simple_browser/simple_browser_tool.py
# --------------------------------------------------------------------------


def wrap_lines(text: str, width: int = 80) -> list[str]:
    return list(
        itertools.chain.from_iterable(
            textwrap.wrap(line, width=width, replace_whitespace=False, drop_whitespace=False)
            if line
            else [""]
            for line in text.split("\n")
        )
    )


def join_lines(lines: list[str], add_line_numbers: bool = False, offset: int = 0) -> str:
    if add_line_numbers:
        return "\n".join(f"L{i + offset}: {line}" for i, line in enumerate(lines))
    return "\n".join(lines)


def maybe_truncate(text: str, num_chars: int = 1024) -> str:
    return text[: num_chars - 3] + "..." if len(text) > num_chars else text


class TokenCounter:
    """Equivalent of gpt-oss get_end_loc(): how many lines fit in view_tokens."""

    def __init__(self, enc_name: str):
        self.enc = tiktoken.get_encoding(enc_name)

    def end_loc(self, loc: int, lines: list[str], view_tokens: int) -> int:
        total = len(lines)
        txt = join_lines(lines[loc:], add_line_numbers=True, offset=loc)
        if len(txt) <= view_tokens:
            return total
        tokens = self.enc.encode(txt, disallowed_special=())
        if len(tokens) <= view_tokens:
            return total
        end_idx = len(self.enc.decode(tokens[:view_tokens]))
        return min(loc + txt[:end_idx].count("\n") + 1, total)


def render_screen(cursor: int, title: str, url: str, lines: list[str], loc: int, end: int) -> str:
    """Matches SimpleBrowserTool._make_response / show_page output."""
    header = title
    if domain := maybe_truncate(unquote(url)):
        header += f" ({domain})"
    header += f"\n**viewing lines [{loc} - {end - 1}] of {len(lines) - 1}**\n\n"
    body = join_lines(lines[loc:end], add_line_numbers=True, offset=loc)
    return f"[{cursor}] {header}{body}"


# --------------------------------------------------------------------------
# Fetching (backend.py equivalents)
# --------------------------------------------------------------------------


async def fetch_direct(session: aiohttp.ClientSession, url: str) -> tuple[str, str | None]:
    async with session.get(url, headers={"user-agent": USER_AGENT}) as resp:
        resp.raise_for_status()
        return await resp.text(errors="replace"), None


async def fetch_exa(session: aiohttp.ClientSession, url: str) -> tuple[str, str | None]:
    key = os.environ.get("EXA_API_KEY") or sys.exit("Set EXA_API_KEY for --backend exa")
    async with session.post(
        "https://api.exa.ai/contents",
        json={"urls": [url], "text": {"includeHtmlTags": True}},
        headers={"x-api-key": key, "user-agent": USER_AGENT},
    ) as resp:
        if resp.status != 200:
            sys.exit(f"Exa error {resp.status}: {await resp.text()}")
        results = (await resp.json()).get("results", [])
    if not results:
        sys.exit(f"Exa returned no contents for {url}")
    return results[0].get("text", ""), results[0].get("title", "")


async def fetch_youcom(session: aiohttp.ClientSession, url: str) -> tuple[str, str | None]:
    key = os.environ.get("YDC_API_KEY") or sys.exit("Set YDC_API_KEY for --backend youcom")
    async with session.post(
        "https://ydc-index.io/v1/contents",
        json={"urls": [url], "livecrawl_formats": "html"},
        headers={"x-api-key": key, "user-agent": USER_AGENT},
    ) as resp:
        if resp.status != 200:
            sys.exit(f"You.com error {resp.status}: {await resp.text()}")
        data = await resp.json()
    if not data or "html" not in data[0]:
        sys.exit(f"You.com returned no HTML for {url}")
    return data[0]["html"], data[0].get("title", "")


BACKENDS = {"direct": fetch_direct, "exa": fetch_exa, "youcom": fetch_youcom}


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("--backend", choices=BACKENDS, default="direct")
    p.add_argument("--full", action="store_true", help="print the whole page as one block instead of 1024-token screens")
    p.add_argument("--links", action="store_true", help="also print the link-id -> URL table the model can 'click'")
    args = p.parse_args()

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        html, title = await BACKENDS[args.backend](session, args.url)

    title, text, urls = process_html(html, args.url, title)
    lines = wrap_lines(text)

    if args.full:
        print(render_screen(0, title, args.url, lines, 0, len(lines)))
    else:
        # The model sees one screen per `open` call; it scrolls with open(loc=...).
        counter = TokenCounter(ENC_NAME)
        loc, screen = 0, 0
        while loc < len(lines):
            end = counter.end_loc(loc, lines, VIEW_TOKENS)
            if screen:
                print(f"\n{'=' * 30} next screen: open(loc={loc}) {'=' * 30}\n")
            print(render_screen(0, title, args.url, lines, loc, end))
            loc, screen = end, screen + 1

    if args.links:
        print("\n--- links ---")
        for link_id, link in urls.items():
            print(f"{link_id}: {link}")


if __name__ == "__main__":
    asyncio.run(main())
