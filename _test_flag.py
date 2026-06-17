import asyncio
import sys
sys.path.insert(0, ".")

async def test():
    from core.utils import get_flag
    test_codes = ["IR", "US", "DE", "NL", "FI", "UN", "XX", "123"]

    for code in test_codes:
        flag = get_flag(code)
        print(f"{code} -> {flag}")

asyncio.run(test())
