from core.collector import DataCollector

collector = DataCollector()

collector.add_text("سلام دنیا")
collector.add_url("https://example.com")
collector.add_html("<h1>Hello</h1>")

print(collector.get_all())