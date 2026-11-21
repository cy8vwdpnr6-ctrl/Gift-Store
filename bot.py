import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from TelegramGifts import TelegramGifts

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

gifts_lib = TelegramGifts(cache_mode="http", asset_mode="lazy")

# لیست رنگ‌های شیک برای گیفت‌ها
COLORS = [
    "linear-gradient(135deg, #4c1d95, #7e22ce)", # بنفش
    "linear-gradient(135deg, #0f172a, #1e293b)", # آبی تیره
    "linear-gradient(135deg, #064e3b, #10b981)", # سبز
    "linear-gradient(135deg, #7f1d1d, #ef4444)", # قرمز
    "linear-gradient(135deg, #78350f, #f59e0b)", # نارنجی
    "linear-gradient(135deg, #831843, #ec4899)", # صورتی
]

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        result = []
        regular_gifts = gifts_lib.get_regular_gifts()
        
        for i, gift in enumerate(regular_gifts[:50]):
            try:
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    
                    # 🔴 1. ساخت لینک با اسم گیفت (چون slug نداریم)
                    clean_name = name.replace(" ", "").replace("'", "").replace("-", "")
                    link = f"https://t.me/nft/{clean_name}"
                    
                    # 2. عکس
                    links = info.get('links', {})
                    img_url = links.get('webp', '') or links.get('png', '')
                    
                    # 🔴 3. استفاده از رنگ‌های آماده به جای رنگ خالی
                    bg_color = COLORS[i % len(COLORS)]

                    # 4. قیمت
                    prices = info.get('prices', {})
                    price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0

                    result.append({
                        "name": name,
                        "price": price,
                        "link": link,
                        "image_url": img_url,
                        "bg_color": bg_color 
                    })
            except Exception as e:
                print(f"Error {gift.full_name}: {e}")
                continue
                
        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
