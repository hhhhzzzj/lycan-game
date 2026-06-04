"""测试三家 LLM API 联通性"""
import asyncio
import json
from pathlib import Path

# 读取配置
cfg_path = Path(__file__).parent / "config" / "players.json"
players = json.load(open(cfg_path, "r", encoding="utf-8"))["players"]

# 每家取一个代表测试
providers_to_test = {}
for p in players:
    key = p["base_url"]
    if key not in providers_to_test:
        providers_to_test[key] = p


async def test_one(p):
    from game.llm.adapters import create_adapter

    name = f'{p["seat_id"]}号 {p["player_name"]} ({p["model_name"]})'
    try:
        adapter = create_adapter(
            provider=p.get("provider", "openai"),
            model=p["model_name"],
            api_key=p["api_key"],
            base_url=p.get("base_url"),
        )
        resp = await asyncio.wait_for(
            adapter.call(
                "你是 API 连通性测试助手。请输出合法 JSON。",
                '{"thinking":"简短思考","action":"你好，连接正常","target_seat":null}',
            ),
            timeout=120.0,
        )
        text = resp.action or ""
        if not text.strip():
            print(f"  ❌ {name}: HTTP成功但返回内容为空")
            return False
        print(f"  ✅ {name}: {text[:60]}")
        return True
    except Exception as e:
        import traceback
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def main():
    print("🔍 测试三家 API 联通性...\n")
    results = []
    for p in providers_to_test.values():
        r = await test_one(p)
        results.append(r)
    
    ok = sum(results)
    total = len(results)
    print(f"\n{'='*50}")
    if ok == total:
        print(f"✅ 全部通过 ({ok}/{total})，可以开跑！")
    else:
        print(f"⚠️  {ok}/{total} 通过，请检查失败的 key")


if __name__ == "__main__":
    asyncio.run(main())
