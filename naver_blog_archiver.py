# naver_blog_archiver.py

import os, re, time, requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


class NaverBlogArchiver:
    def __init__(self):
        self.driver = self.init_driver()
        self.processed = self.load_log()

    def init_driver(self):
        options = Options()
        options.add_argument('--headless')  # GUI 안 띄움
        options.add_argument('--disable-gpu')
        return webdriver.Chrome(options=options)

    def login(self, user_id, user_pw):
        self.driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)
        self.driver.execute_script("document.getElementById('id').value = arguments[0]", user_id)
        self.driver.execute_script("document.getElementById('pw').value = arguments[0]", user_pw)
        self.driver.find_element(By.ID, "log.login").click()
        time.sleep(3)

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name)

    def download_image(self, img_url, save_folder):
        os.makedirs(save_folder, exist_ok=True)
        fname = os.path.basename(urlparse(img_url).path)
        local_path = os.path.join(save_folder, fname)
        try:
            with open(local_path, "wb") as f:
                f.write(requests.get(img_url).content)
            return f"images/{fname}"
        except:
            return img_url  # 실패 시 원본 링크 유지

    def normalize_url(self, url):
        if "PostView.naver" in url:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            blog_id = qs.get("blogId", [""])[0]
            log_no = qs.get("logNo", [""])[0]
            if blog_id and log_no:
                return f"https://blog.naver.com/{blog_id}/{log_no}"
        return url

    def process_post(self, url):
        url = self.normalize_url(url)
        print(f"Processing: {url}")
        self.driver.get(url)
        try:
            self.driver.switch_to.frame("mainFrame")
        except:
            print("[!] mainFrame이 존재하지 않아 스킵됨")
            return

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        try:
            title_tag = soup.select_one(".se-title-text, .pcol1")
            content_tag = soup.select_one(".se-main-container, #postViewArea")
            if not title_tag or not content_tag:
                print("본문을 찾을 수 없음")
                return
        except:
            print("파싱 오류")
            return

        title = self.sanitize_filename(title_tag.text.strip())
        content = content_tag
        date = time.strftime("%Y-%m-%d")  # 정확한 날짜 파싱 추가 가능
        category = "Uncategorized"  # 카테고리 추출 가능시 여기에 반영

        image_dir = f"archive/{category}/images"
        for img in content.find_all("img"):
            img_url = img.get("src")
            if img_url:
                img["src"] = self.download_image(img_url, image_dir)

        markdown = md(str(content))
        outdir = f"archive/{category}"
        os.makedirs(outdir, exist_ok=True)

        with open(f"{outdir}/{date}-{title}.md", "w", encoding="utf-8") as f:
            f.write(f"---\ntitle: \"{title}\"\ndate: {date}\ncategory: {category}\n---\n\n")
            f.write(markdown)

        self.log_processed(url)

    def log_processed(self, url):
        with open("processed.log", "a") as f:
            f.write(url + "\n")
        self.processed.add(url)

    def load_log(self):
        if not os.path.exists("processed.log"):
            return set()
        with open("processed.log") as f:
            return set(line.strip() for line in f)

    def process_from_file(self, file_path="input_links.txt"):
        with open(file_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
        for url in urls:
            if url not in self.processed:
                self.process_post(url)


# -------------------------- 실행 예시 --------------------------
if __name__ == "__main__":
    archiver = NaverBlogArchiver()
    # archiver.login("your_id", "your_pw")  # 공개글만 처리 시 생략
    archiver.process_from_file("input_links.txt")
    archiver.driver.quit()

