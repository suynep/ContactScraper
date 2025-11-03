from selenium import webdriver
from colorama import init, Fore, Style
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import argparse
import re
import requests
import time
from datetime import datetime
import urllib.parse
from selenium.webdriver.firefox.options import Options
import json
from pprint import pprint

init() # initialize colorama

parser = argparse.ArgumentParser(
    prog="scraper.py",
    description="Scrape URLs and Extract contact info",
    epilog="Contact me @ suyash@vrittechnologies.com",
    formatter_class=argparse.RawTextHelpFormatter,
)


parser.add_argument("-u", "--url", help="URL to scrape from", metavar="QUERY", type=str)
parser.add_argument(
    "-k",
    "--keywords",
    help="keywords to search in google maps",
    metavar="KEYWORDS",
    type=str,
)

parser.add_argument(
    "-n",
    "--number",
    help="number of websites scrape from google maps. Defaults to 4",
    metavar="NUMBER",
    type=int,
)

parser.add_argument(
    "-l",
    "--log",
    help="save file to the specified file path",
    action="store_true",
)

args = parser.parse_args()

save_dump = []

# parser = argparse.ArgumentParser()
# parser.add_argument("url", required=True, help="URL to scrape")


class Scraper:
    SAVE_PATH = f"contact_{str(datetime.now())}.json"
    REACT_POINTERS = [
        'id="root"',
        "id='root'",
        "[data-reactroot]",
        "[data-reactid]",
        "[data-react-root]",
        "react",
    ]

    def __init__(self, url):
        self.url = url
        self.content = ""
        self.sitemap_exists = False
        self.captcha_exists = False
        self.emails = []
        self.is_react = False  # requires explicit handling
        self.contact_details = {}
        self.phone_numbers = []
        # Optionally, self.about_urls : list[str]

    def get(self):
        print(Fore.BLUE + "*****-*****-*****" + Style.RESET_ALL)
        print(Fore.GREEN + f"\nGetting Details of: {self.url}")
        print(Fore.BLUE + "*****-*****-*****" + Style.RESET_ALL)
        headers = {"User-Agent": "curl/8.0", "Accept": "*/*"}

        try:
            res = requests.get(self.url, headers=headers)
        except requests.exceptions.ConnectionError:
            print(f"[Error]: Couldn't connect to {self.url}")
            return

        sitemap_res = requests.get(
            f"{self.url.rstrip('/')}/sitemap.xml", headers=headers
        )

        if sitemap_res.status_code == 200:
            self.sitemap_exists = True

        if self.sitemap_exists:
            # match strings containing the `about` in their paths
            self.about_urls = re.findall(
                r"(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(?:/[a-zA-Z0-9._~:/?#\[\]@!$&()*+,;=-]*)?(?:about|contact)(?:/[a-zA-Z0-9._~:/?#\[\]@!$&()*+,;=-]*)?",
                sitemap_res.text,
            )

            self.about_urls = list(set(self.about_urls)) # prevents duplication

        for pointer in Scraper.REACT_POINTERS:
            if pointer in res.text:
                self.is_react = True
                return

        print(f"DEBUG: {self.url} returned {res.status_code}")
        if res.status_code == 200:
            if "captcha" in res.text:
                self.captcha_exists = True

            if not self.captcha_exists:
                self.content = res.text
            else:
                print("Captcha Exists, cannot proceed")

    def _match_email_pattern(self, url):
        """
        Rudimentary RegEx matcher for emails
        :param: `url` represents the URL of the Web page from where we are to extract emails
        """
        match = None
        try:
            res = requests.get(url)
        except requests.exceptions.ConnectionError:
            print(f"[Error]: Couldn't connect to {self.url}")
            return

        if res.status_code == 200:
            text = res.text
            # match = re.findall("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
            email_pattern = re.compile(
                r"[a-zA-Z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                re.IGNORECASE,
            )

            match = email_pattern.findall(text)

        else:
            return

        if match is not None:
            for m in match:
                if m not in self.emails:
                    self.emails.append(m)

        phone_pattern = re.compile(r"\b(?:\+?977|01)[\d\-\.\s]{5,}\d\b")
        phone_matches = phone_pattern.findall(text)
        # !DEBUG
        pprint(f"DEBUG: {phone_matches}")

        for p in phone_matches:
            # normalize: remove non-digit characters
            normalized = re.sub(r"\D", "", p)
            if (
                len(normalized) >= 7
                and len(normalized) <= 15
                and normalized[0] in {"0", "9", "4"}
                and normalized not in self.phone_numbers
            ):
                self.phone_numbers.append(normalized)

    def extract_email(self):
        """
        Extract email from the Response text
        !IMPORTANT: use `self.get()` before this function
        """
        if self.sitemap_exists:
            print("DEBUG: Sitemap Exists, fetching about/contact pages...")
            for url in self.about_urls:
                if self.is_react:
                    self.handle_react(url)
                self._match_email_pattern(url)

        email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        )

        match = re.findall(email_pattern, self.content)

        if match is not None:
            print(f"DEBUG: Matches\n{match}")
            for m in match:
                if m not in self.emails:
                    self.emails.append(m)

        phone_pattern = re.compile(r"\b(?:\+?977|01)[\d\-\.\s]{5,}\d\b")
        phone_matches = phone_pattern.findall(self.content)
        for p in phone_matches:
            # normalize: remove non-digit characters
            normalized = re.sub(r"\D", "", p)
            if (
                len(normalized) >= 7
                and len(normalized) <= 15
                and normalized[0] in {"0", "9", "4"}
                and normalized not in self.phone_numbers
            ):
                self.phone_numbers.append(normalized)

    def handle_popup(self):
        """
        Some websites load a popup on load
        This obstructs our ability to scrape for contact details
        Thus, handled separately
        """
        pass

    def handle_hyperlinks(self):
        """
        Hyperlinks like "Contact Us", "About Us" etc. may exist,
        despite the site not having sitemap.xml
        """
        pass

    def handle_react(self, url):
        """
        due to react's CSR, body isn't loaded fully, and thus requests.get() cannot fetch the
        required text. This method accounts for this.
        """
        if self.is_react:
            options = Options()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
            try:
                driver.get(url)
                time.sleep(10)
                # driver.implicitly_wait(10)
                # Get all visible text from the page
                page_text = driver.find_element(By.TAG_NAME, "body").text
                # print(page_text)

                # Optional: also extract all hrefs for mailto links
                all_links = [
                    link.get_attribute("href")
                    for link in driver.find_elements(By.TAG_NAME, "a")
                ]
            finally:
                driver.quit()

            email_pattern = re.compile(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE
            )
            # Find emails in page text
            emails_from_text = email_pattern.findall(page_text)
            # Find emails in mailto links
            emails_from_links = [
                m.group(0)
                for link in all_links
                if link
                for m in email_pattern.finditer(link)
            ]
            # Combine and deduplicate
            all_emails = list(set(emails_from_text + emails_from_links))
            for email in all_emails:
                if email not in self.emails:
                    self.emails.append(email)

            phone_pattern = re.compile(r"\b(?:\+?977|01)[\d\-\.\s]{5,}\d\b")
            phone_matches = phone_pattern.findall(page_text)
            for p in phone_matches:
                # normalize: remove non-digit characters
                normalized = re.sub(r"\D", "", p)
                if (
                    len(normalized) >= 7
                    and len(normalized) <= 15
                    and normalized[0] in {"0", "9", "4"}
                    and normalized not in self.phone_numbers
                ):
                    self.phone_numbers.append(normalized)

    def get_emails(self):
        return self.emails

    def update_save(self):
        self.contact_details["website"] = self.url

        if self.emails:
            self.contact_details["emails"] = self.emails
        else:
            self.contact_details["emails"] = "Emails Not Found"

        if self.phone_numbers:
            self.contact_details["numbers"] = self.phone_numbers
        else:
            self.contact_details["numbers"] = "Phone Numbers not found"

        save_dump.append(self.contact_details)

    def run(self):
        self.get()
        self.extract_email()
        self.handle_react(self.url)

        # !Debug
        print(f"DEBUG: {self.get_emails()}")
        print(f"DEBUG: Sitemap {self.sitemap_exists}")


class KeywordsExtractor:
    def __init__(self, keywords, n=4):
        self.keywords = keywords
        self.url = f"https://google.com/maps/search/{urllib.parse.quote_plus(self.keywords, safe='')}?hl=en"
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)
        self.webaddresses = []
        self.num = n # no. of websites to scrape from maps

    def open(self):
        self.driver.get(self.url)
        self.driver.maximize_window()

    def find_websites(self):
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[@data-value = 'Website']")
                )
            )
            print("DEBUG: Element found and loaded.")
            
            scrollable_div = self.driver.find_element(By.XPATH, '//div[@role="feed"]')
            seen_urls = set()  # Track unique URLs
            
            while len(seen_urls) < self.num:
                # Find all website elements
                elements = self.driver.find_elements(
                    By.XPATH, "//a[@data-value = 'Website']"
                )
                
                # Extract unique URLs
                for ele in elements:
                    if len(seen_urls) >= self.num:
                        break
                    url = ele.get_attribute("href")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                
                print(f"INFO: Found {len(seen_urls)} unique websites so far...")
                
                # If we haven't reached the target, scroll more
                if len(seen_urls) < self.num:
                    # Get current scroll position
                    current_scroll = self.driver.execute_script(
                        "return arguments[0].scrollTop", scrollable_div
                    )
                    
                    # Scroll down
                    self.driver.execute_script(
                        "arguments[0].scrollTop += 500", scrollable_div
                    )
                    
                    # Wait for new content to load
                    time.sleep(1)
                    
                    # Check if we've reached the bottom (no new scroll happened)
                    new_scroll = self.driver.execute_script(
                        "return arguments[0].scrollTop", scrollable_div
                    )
                    
                    if current_scroll == new_scroll:
                        print("INFO: Reached end of scrollable content.")
                        break
            
            # Add the URLs to webaddresses
            self.webaddresses.extend(list(seen_urls)[:self.num])
            print(f"INFO: Collected {len(self.webaddresses)} website URLs.")
            
        except TimeoutException:
            print("ERROR: Website Element not found within the specified time.")
        finally:
            self.driver.quit()

    def get_webaddresses(self):
        return self.webaddresses

    def run(self):
        self.open()
        self.find_websites()
        # !Debug
        print(f"DEBUG: {self.webaddresses}")


if __name__ == "__main__":
    if args.url:
        scraper = Scraper(args.url)
        scraper.run()
        scraper.update_save()
        if args.log:
            with open(Scraper.SAVE_PATH, "w") as fp:
                json.dump(save_dump, fp)
            print(f"\nINFO: Details saved at {Scraper.SAVE_PATH}")

    elif args.keywords:
        kwex = KeywordsExtractor(args.keywords)
        if args.number:
            kwex = KeywordsExtractor(args.keywords, n=args.number)
        kwex.run()

        for wa in kwex.webaddresses:
            scraper = Scraper(wa)
            scraper.run()
            scraper.update_save()

        helper_file_name = args.keywords.replace(" ", "_")
        SAVE_PATH = f"contact_[{helper_file_name}]_{str(datetime.now())}.json"

        if args.log:
            with open(SAVE_PATH, "w") as fp:
                json.dump(save_dump, fp)
            print(f"\nINFO: Details saved at {SAVE_PATH}")

    else:
        print("Usage: Provide a URL with the -u flag or keywords with the -k flag")
