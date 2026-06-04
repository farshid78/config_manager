from core.parser import DataParser

parser = DataParser()

text = """
سلام
وبسایت: https://example.com
ایمیل: test@mail.com
"""

result = parser.extract_all(text)

print(result)