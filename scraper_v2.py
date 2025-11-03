#!/usr/bin/env python3
"""
Google Maps Website Scraper
Extracts emails and Nepali phone numbers from business websites.
"""

import argparse
import json
import re
import time
from datetime import datetime
from pprint import pprint
from typing import List, Set, Dict, Optional
import urllib.parse
import requests
from colorama import init, Fore, Style
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

init()  # Initialize colorama


# ==============================
# Configuration & Constants
# ==============================

class Patterns:
    EMAIL = re.compile(
        r"[a-zA-Z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE
    )
    EMAIL_STRICT = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE
    )
    PHONE_NP = re.compile(r"\b(?:\+?977|01)[\d\-\.\s]{5,}\d\b")
    ABOUT_PAGE = re.compile(
        r"(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        r"(?:/[^\s]*?)?(?:about|contact|reach-us|team|info)[^\s<>\"]*",
        re.IGNORECASE
    )


REACT_INDICATORS = [
    'id="root"', 'id=\'root\'', '[data-reactroot]', '[data-reactid]',
    '[data-react-root]', 'react'
]

HEADERS = {"User-Agent": "curl/8.0", "Accept": "*/*"}
ALT_HEADERS = {
    "User-Agent": "PostmanRuntime/7.49.0",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

EDU_PATHS = [
    # Segregations
    "/college", "/school", "/hss",
    # Contact
    "/contact", "/contact-us", "/contact/", "/reach-us", "/get-in-touch",
    # About
    "/about", "/about-us", "/about/", "/who-we-are", "/mission-vision",
    # Admissions
    "/admissions", "/admission", "/apply", "/apply-now", "/enroll",
    # Academics
    "/academics", "/programs", "/courses", "/departments", "/faculty",
    # Campus
    "/student-life", "/campus-life", "/housing", "/events",
    # Legal
    "/privacy-policy", "/sitemap", "/sitemap.xml",
]


# ==============================
# Utility Functions
# ==============================

def log_info(msg: str):
    print(Fore.CYAN + f"[INFO] {msg}" + Style.RESET_ALL)

def log_debug(msg: str):
    print(Fore.YELLOW + f"[DEBUG] {msg}" + Style.RESET_ALL)

def log_error(msg: str):
    print(Fore.RED + f"[ERROR] {msg}" + Style.RESET_ALL)

def normalize_phone(phone: str) -> Optional[str]:
    digits = re.sub(r"\D", "", phone)
    if 9 <= len(digits) <= 15 and digits[0] in "09456":
        return digits
    return None


# ==============================
# Core Scraper Module
# ==============================

class ContactScraper:
    def __init__(self, url: str, use_headless: bool = True):
        self.url = url.rstrip("/")
        self.content = ""
        self.is_react = False
        self.has_sitemap = False
        self.captcha_detected = False
        self.emails: Set[str] = set()
        self.phones: Set[str] = set()
        self.about_pages: List[str] = []
        self.options = Options()
        self.seen_links = []
        if use_headless:
            self.options.add_argument("--headless")

    def fetch_page(self) -> bool:
        try:
            response = requests.get(self.url, headers=HEADERS, timeout=10)
            if response.status_code in [400, 401, 403, 404, 405, 408, 409]:
                headers = {
                    "User-Agent": "PostmanRuntime/7.49.0",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                }
                response = requests.get(self.url, headers=headers, timeout=10)
            if response.status_code != 200:
                log_error(f"{self.url} returned {response.status_code}")
                # return False

            self.content = response.text
            self.is_react = any(ind in self.content for ind in REACT_INDICATORS)
            # self.captcha_detected = "captcha" in self.content.lower()

            if self.captcha_detected:
                log_error("CAPTCHA detected. Skipping content scraping.")
                return False

            self._check_sitemap()
            return True

        except requests.RequestException as e:
            log_error(f"Failed to fetch {self.url}: {e}")
            return False

    def fetch_common_paths(self):
        for edu_path in EDU_PATHS:
            try:
                response = requests.get(f"{self.url}{edu_path}")
                log_info(f"Checking {self.url}{edu_path}")
                if response.status_code != 200:
                    log_error(f"{self.url} returned {response.status_code}")
                    continue

                self.extract_from_text(response.text)
                self.handle_hyperlinks(response.text)

            except requests.RequestException:
                log_error(f"Failed to fetch {self.url}: e")

    def _check_sitemap(self):
        sitemap_urls = [f"{self.url}/sitemap.xml", f"{self.url}/sitemap"]
        try:
            for sm_url in sitemap_urls:
                res = requests.get(sm_url, headers=HEADERS, timeout=5)

                if res.status_code in [400, 401, 403, 404, 405, 408, 409]:
                    res = requests.get(self.url, headers=ALT_HEADERS, timeout=10)

                if res.status_code == 200:
                    self.has_sitemap = True
                    ###
                    for url in set(Patterns.ABOUT_PAGE.findall(res.text)):
                        pprint(url)
                        self.about_pages.append(url)
                    self.about_pages = list(set(self.about_pages))
                    # self.about_pages = list(set(Patterns.ABOUT_PAGE.findall(res.text)))
                    log_debug(f"Found {len(self.about_pages)} about/contact pages in sitemap")
        except requests.RequestException:
            pass

    def extract_from_text(self, text: str):
        # Emails
        for email in Patterns.EMAIL_STRICT.findall(text):
            self.emails.add(email.lower())

        # Phones
        for match in Patterns.PHONE_NP.finditer(text):
            if norm := normalize_phone(match.group()):
                self.phones.add(norm)

    def scrape_static(self):
        if not self.content:
            return

        self.extract_from_text(self.content)
        self.handle_hyperlinks(self.content)

        if self.has_sitemap:
            for page in self.about_pages[:5]:  # limit to avoid spam
                try:
                    res = requests.get(page, headers=HEADERS, timeout=10)
                    if res.status_code == 200:
                        self.extract_from_text(res.text)
                except:
                    continue

    def scrape_dynamic(self, url):
        if not self.is_react:
            return

        driver = None
        try:
            driver = webdriver.Firefox(options=self.options)
            driver.get(url)
            time.sleep(8)

            body_text = driver.find_element(By.TAG_NAME, "body").text
            self.extract_from_text(body_text)
            html_content = driver.page_source
            self.handle_hyperlinks(html_content)

            # Extract mailto: links
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                if href.startswith("mailto:"):
                    email = href[7:].split("?")[0]
                    if Patterns.EMAIL_STRICT.match(email):
                        self.emails.add(email.lower())

        except Exception as e:
            log_error(f"Selenium failed for {url}: {e}")
        finally:
            if driver:
                driver.quit()

    def handle_hyperlinks(self, html: str):
        """
        Hyperlinks like "Contact Us", "About Us" etc. may exist,
        despite the site not having sitemap.xml
        """
        parser = BeautifulSoup(html, 'html.parser')
        links = parser("a")
        if links is not None:
            for link in links:
                if "href" in list(link.attrs.keys()):
                    href = str(link['href'])
                    if href not in self.seen_links and (href.startswith("https") or href.startswith("http")):
                        self.seen_links.append(href)
                        keywords = ['about', 'contact']
                        for k in keywords:
                            if k in href.lower():
                                log_debug(f"Found {k} Hyperlink at {href}")
                                res = requests.get(f"{href}")
                                if res.status_code == 200:
                                    self.extract_from_text(res.text)
                                else:
                                    log_error(f"{href} returned {res.status_code}")


    def run(self) -> Dict:
        log_info(f"Scraping: {self.url}")
        if not self.fetch_page():
            return {"website": self.url, "emails": [], "numbers": []}

        self.scrape_static()
        if self.is_react:
            self.scrape_dynamic(self.url)

        self.fetch_common_paths()

        return {
            "website": self.url,
            "emails": sorted(self.emails) or "Not found",
            "numbers": sorted(self.phones) or "Not found"
        }


# ==============================
# Google Maps URL Extractor
# ==============================

class MapsScraper:
    def __init__(self, keywords: str, limit: int = 4):
        self.keywords = keywords
        self.limit = limit
        self.search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(keywords)}?hl=en"
        self.websites: Set[str] = set()

    def run(self) -> List[str]:
        driver = None
        try:
            options = Options()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
            driver.get(self.search_url)
            driver.maximize_window()

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//a[@data-value='Website']"))
            )

            feed = driver.find_element(By.XPATH, '//div[@role="feed"]')
            last_height = driver.execute_script("return arguments[0].scrollTop", feed)

            while len(self.websites) < self.limit:
                elements = driver.find_elements(By.XPATH, "//a[@data-value='Website']")
                for el in elements:
                    url = el.get_attribute("href")
                    if url and url.startswith("http"):
                        self.websites.add(url)
                    if len(self.websites) >= self.limit:
                        break

                # Scroll
                driver.execute_script("arguments[0].scrollTop += 600", feed)
                time.sleep(1.2)

                new_height = driver.execute_script("return arguments[0].scrollTop", feed)
                if new_height == last_height:
                    log_info("No more results. End of scroll.")
                    break
                last_height = new_height

            log_info(f"Collected {len(self.websites)} websites from Maps.")
            return list(self.websites)[:self.limit]

        except TimeoutException:
            log_error("Website links not found in Google Maps.")
            return []
        except Exception as e:
            log_error(f"Maps scraping failed: {e}")
            return []
        finally:
            if driver:
                driver.quit()


# ==============================
# CLI & Main Runner
# ==============================

def save_results(data: List[Dict], filename: str):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log_info(f"Results saved to {filename}")
    except Exception as e:
        log_error(f"Failed to save file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape contact info from websites or Google Maps",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Example: python scraper.py -k 'restaurants in Kathmandu' -n 6 -l"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--url", help="Single website URL to scrape")
    group.add_argument("-k", "--keywords", help="Keywords to search in Google Maps")
    parser.add_argument("-n", "--number", type=int, default=4, help="Number of sites to scrape (default: 4)")
    parser.add_argument("-l", "--log", action="store_true", help="Save output to JSON file")

    args = parser.parse_args()

    results = []

    if args.url:
        scraper = ContactScraper(args.url)
        result = scraper.run()
        results.append(result)
        pprint(result)

    elif args.keywords:
        maps = MapsScraper(args.keywords, limit=args.number)
        websites = maps.run()

        if not websites:
            log_error("No websites found.")
            return

        for site in websites:
            
            scraper = ContactScraper(site)
            result = scraper.run()
            results.append(result)
            pprint(result)
            # time.sleep(1)  # Be respectful

    if args.log and results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        keyword_part = args.keywords.replace(" ", "_") if args.keywords else "single"
        filename = f"contacts_[{keyword_part}]_{timestamp}.json"
        save_results(results, filename)


if __name__ == "__main__":
    main()
