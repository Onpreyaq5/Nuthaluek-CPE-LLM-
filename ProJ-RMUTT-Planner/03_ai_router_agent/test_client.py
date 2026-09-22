import httpx
import asyncio
import json

async def main():
    print("="*50)
    print("🤖 TEST 1: /classify (Intent & Slot Extraction)")
    print("="*50)
    
    payload_classify = {
        "student_id": "65010001",
        "message": "ลง CPE101 กับ MTH102 ชนไหมครับ",
        "session_id": "test_sess",
        "history": []
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://localhost:8100/classify", json=payload_classify)
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error connecting to server: {e}\nIs uvicorn running?")
            return

    print("\n" + "="*50)
    print("🌊 TEST 2: /chat (SSE Streaming Flow)")
    print("="*50)
    
    payload_chat = {
        "student_id": "65010001",
        "message": "จัดตารางเทอม 1/2569 ให้หน่อย อยากว่างวันศุกร์",
        "session_id": "test_sess",
        "history": []
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "http://localhost:8100/chat", json=payload_chat, timeout=15.0) as response:
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    print(f"\n[{line.replace('event: ', '').upper()}]")
                elif line.startswith("data:"):
                    data_str = line.replace('data: ', '')
                    try:
                        parsed = json.loads(data_str)
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except:
                        print(data_str)

if __name__ == "__main__":
    asyncio.run(main())
