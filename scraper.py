from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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
    "-l",
    "--log",
    help="save file to the specified file path",
    action="store_true",
)

args = parser.parse_args()

save_dump = []
SAVE_PATH = f"contact__{str(datetime.now())}.json"

# parser = argparse.ArgumentParser()
# parser.add_argument("url", required=True, help="URL to scrape")


class Scraper:
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
        headers = {"User-Agent": "curl/8.0", "Accept": "*/*"}

        try:
            res = requests.get(self.url, headers=headers)
        except requests.exceptions.ConnectionError:
            print(f"[Error]: Couldn't connect to {self.url}")
            return

        if 'id="root"' in res.text:
            self.is_react = True
            return

        sitemap_res = requests.get(
            f"{self.url.rstrip('/')}/sitemap.xml", headers=headers
        )

        # if sitemap_res.status_code == 301:
        #     sitemap_res = requests.get(f"{}")

        if sitemap_res.status_code == 200:
            self.sitemap_exists = True

        if self.sitemap_exists:
            # match strings containing the `about` in their paths
            self.about_urls = re.findall(
                "(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\/\S*(?:about|contact)\S*",
                sitemap_res.text,
            )

        print(res.status_code)
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
            # print(match)
            for m in match:
                if m not in self.emails:
                    self.emails.append(m)

        phone_pattern = re.compile(r"\b(?:\+?977|01)[\d\-\.\s]{5,}\d\b")
        phone_matches = phone_pattern.findall(text)
        print(phone_matches)
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
            print(self.about_urls)
            for url in self.about_urls:
                self._match_email_pattern(url)

        email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        )

        match = re.findall(
            email_pattern, self.content
        )

        if match is not None:
            print(match)
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

    def handle_react(self):
        """
        due to react's CSR, body isn't loaded fully, and thus requests.get() cannot fetch the
        required text. This method accounts for this.
        """
        if self.is_react:
            options = Options()
            options.headless = True  # Run in headless mode
            driver = webdriver.Firefox(options=options)
            try:
                driver.get(self.url)
                time.sleep(10)
                # driver.implicitly_wait(10)
                # Get all visible text from the page
                page_text = driver.find_element(By.TAG_NAME, "body").text
                print(page_text)

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
        self.handle_react()

        # !Debug
        print(f"DEBUG: {self.get_emails()}")
        print(f"DEBUG: Sitemap {self.sitemap_exists}")


class KeywordsExtractor:
    def __init__(self, keywords):
        self.keywords = keywords
        self.url = f"https://google.com/maps/search/{urllib.parse.quote_plus(self.keywords, safe='')}?hl=en"
        self.driver = webdriver.Firefox()
        self.webaddresses = []

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
            print("Element found and loaded.")

            website_elements = self.driver.find_elements(
                By.XPATH, "//a[@data-value = 'Website']"
            )

            for elem in website_elements:
                # print(elem.get_attribute("href"))
                self.webaddresses.append(elem.get_attribute("href"))

        except TimeoutException:
            print("Website Element not found within the specified time.")

    def get_webaddresses(self):
        return self.webaddresses

    def run(self):
        self.open()
        self.find_websites()
        # !Debug
        print(self.webaddresses)


if __name__ == "__main__":
    if args.url:
        scraper = Scraper(args.url)
        scraper.run()
        scraper.update_save()
        if args.log:
            with open(SAVE_PATH, "w") as fp:
                json.dump(save_dump, fp)

    elif args.keywords:
        kwex = KeywordsExtractor(args.keywords)
        kwex.run()

        for wa in kwex.webaddresses:
            scraper = Scraper(wa)
            scraper.run()
            scraper.update_save()
            if args.log:
                with open(SAVE_PATH, "w") as fp:
                    json.dump(save_dump, fp)

    else:
        print("Usage: Provide a URL with the -u flag or keywords with the -k flag")
