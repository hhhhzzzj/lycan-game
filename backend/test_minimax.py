import asyncio
import os
from openai import AsyncOpenAI

async def test():
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("SKIP: set MINIMAX_API_KEY to run this connectivity check")
        return

    c = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.minimax.chat/v1"
    )
    try:
        r = await asyncio.wait_for(
            c.chat.completions.create(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=20,
            ),
            timeout=30.0,
        )
        print("SUCCESS:", r.choices[0].message.content)
    except Exception as e:
        print(f"ERROR type={type(e).__name__}: {e}")

asyncio.run(test())
