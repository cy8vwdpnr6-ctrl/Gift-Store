import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/gifts")
async def get_gifts_api():
    result = []
    # اسم گیفت‌هایی که توی عکس دیدم
    gift_names = [
        "UFC Strike", "Khabib's Papakha", "Westside Sign", "Low Rider"
    ]
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        for name in gift_names:
            try:
                # API فرگمنت برای گرفتن لیست گیفت‌ها
                # اسم رو به فرمت slug تبدیل میکنیم
                slug = name.lower().replace(" ", "-").replace("'", "")
                url = f"https://api.fragment-api.com/v1/gifts?collection={slug}"
                
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    gifts = data.get('gifts', [])
                    
                    if gifts:
                        # اولین گیفت موجود رو برمیداریم
                        first_gift = gifts[0]
                        
                        # لینک واقعی از فیلد slug گرفته میشه
                        # slug دقیقا همون Name-Number هست
                        item_slug = first_gift.get('slug', '')
                        real_link = f"https://t.me/nft/{item_slug}" if item_slug else ""
                        
                        result.append({
                            "name": name,
                            "price": first_gift.get('price', 0),
                            "link": real_link,
                            "image_url": first_gift.get('image_url', ''),
                            "bg_color": first_gift.get('background_color', '#1c1c1e')
                        })
            except Exception as e:
                print(f"Error {name}: {e}")
                continue
                
    return {"status": "success", "data": result}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
