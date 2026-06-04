from scraper.web_scraper import WebScraper


scraper = WebScraper()

count = scraper.run("v2ray_configs")

print("Configs found:", count)