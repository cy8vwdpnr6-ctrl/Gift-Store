import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from TelegramGifts import TelegramGifts

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# این کتابخانه دیتای واقعی تلگرام رو داره
gifts_lib = TelegramGifts(cache_mode="http", asset_mode="lazy")

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        result = []
        # گرفتن لیست پایه گیفت‌ها
        regular_gifts = gifts_lib.get_regular_gifts()
        
        # ما فقط 50 تا اول رو برمی‌داریم که سریع باشه
        for gift in regular_gifts[:50]:
            try:
                # گرفتن اطلاعات دقیق
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    
                    # 1. لینک از فیلد slug (دقیقا طبق مستندات تلگرام)
                    slug = info.get('slug', '')
                    link = f"https://t.me/nft/{slug}" if slug else ""
                    
                    # 2. عکس
                    links = info.get('links', {})
                    img_url = links.get('webp', '') or links.get('png', '')
                    
                    # 3. رنگ بک‌گراند از فیلد backdrop
                    backdrop = info.get('backdrop', {})
                    bg_color = ""
                    if isinstance(backdrop, dict):
                        c_from = backdrop.get('center_color') or backdrop.get('gradient_from')
                        c_to = backdrop.get('edge_color') or backdrop.get('gradient_to')
                        
                        if c_from:
                            bg_color = f"#{c_from:06x}" if isinstance(c_from, int) else c_from
                            if c_to:
                                c_to_hex = f"#{c_to:06x}" if isinstance(c_to, int) else c_to
                                bg_color = f"linear-gradient(135deg, {bg_color}, {c_to_hex})"

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
