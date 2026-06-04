from core.deduplicator import Deduplicator

dedup = Deduplicator()

data = [
    "test",
    "test",
    "hello",
    "hello",
    "world"
]

result = dedup.remove_duplicates(data)

print(result)