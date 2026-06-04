from core.collector import DataCollector
from core.processor import DataProcessor

collector = DataCollector()
processor = DataProcessor()

collector.add_text("سلام https://example.com test@mail.com")
collector.add_url("https://google.com")
collector.add_html("<b>Hello</b> https://site.com")

data = collector.get_all()

result = processor.process_batch(data)

for item in result:
    print(item)