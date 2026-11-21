import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/gifts")
async def get_gifts_api():
    result = []
    # این آدرس دقیق لیست کلکسیون‌های گت‌گمز هست
    url = "https://api.getgems.io/public-api/v1/nfts/collections"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                
                # دیتا معمولا داخل یه کلید به اسم items یا collections هست
                items = data.get('items', []) or data if isinstance(data, list) else []
                
                for item in items:
                    try:
                        metadata = item.get('metadata', {})
                        name = metadata.get('name', '')
                        
                        # ما فقط آیتم‌هایی رو می‌خوایم که اسم دارن
                        if not name: continue
                        
                        # لینک واقعی (فیلد address معمولا همون اسم کلکسیونه)
                        slug = item.get('address', '')
                        link = f"https://t.me/nft/{slug}" if slug else ""
                        
                        # قیمت
                        price_nano = item.get('floor_price', 0)
                        price = float(price_nano) / 1e9 if price_nano else 0
                        
                        # عکس
                        img_url = metadata.get('image', '')
                        
                        # رنگ
                        bg_color = metadata.get('background_color', '#1c1c1e')
                        if bg_color and not bg_color.startswith('#'):
                            bg_color = f"#{bg_color}"

                        result.append({
                            "name": name,
                            "price": round(price, 4),
                            "link": link,
                            "image_url": img_url,
                            "bg_color": bg_color
                        })
                    except:
                        continue
        except Exception as e:
            print(f"API Error: {e}")
            return {"status": "error", "message": str(e)}
                
    return {"status": "success", "data": result}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
