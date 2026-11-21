import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from TelegramGifts import TelegramGifts

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

gifts_lib = TelegramGifts(cache_mode="http", asset_mode="lazy")

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("از مینی‌اپ استفاده کن!")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        regular_gifts = gifts_lib.get_regular_gifts()
        result = []
        seen = set()

        for gift in regular_gifts:
            try:
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    if name not in seen:
                        seen.add(name)
                        
                        # 1. قیمت
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        # 2. لینک واقعی از slug
                        # طبق مستندات تلگرام، slug برای ساخت لینک استفاده میشه
                        slug = info.get('slug', '')
                        if not slug:
                            # اگر slug نبود، از name استفاده میکنیم
                            slug = info.get('name', '').replace(" ", "").replace("'", "")
                        
                        gift_link = f"https://t.me/nft/{slug}" if slug else ""
                        
                        # 3. عکس
                        links = info.get('links', {})
                        img_url = links.get('webp', '') or links.get('png', '') or links.get('jpg', '')
                        
                        # 4. بک‌گراند واقعی از backdrop
                        # تلگرام رنگ‌ها رو در backdrop با center_color و edge_color میده
                        backdrop = info.get('backdrop', {})
                        bg_color = ""
                        
                        if isinstance(backdrop, dict):
                            c_from = backdrop.get('center_color') or backdrop.get('gradient_from')
                            c_to = backdrop.get('edge_color') or backdrop.get('gradient_to')
                            
                            if c_from:
                                # تبدیل عدد RGB به هگز
                                if isinstance(c_from, int):
                                    bg_color = f"#{c_from:06x}"
                                elif isinstance(c_from, str):
                                    bg_color = c_from if c_from.startswith('#') else f"#{c_from}"
                                    
                                if c_to:
                                    if isinstance(c_to, int):
                                        c_to_hex = f"#{c_to:06x}"
                                    elif isinstance(c_to, str):
                                        c_to_hex = c_to if c_to.startswith('#') else f"#{c_to}"
                                    else:
                                        c_to_hex = c_to
                                    bg_color = f"linear-gradient(135deg, {bg_color}, {c_to_hex})"

                        result.append({
                            "name": name,
                            "price": price,
                            "link": gift_link,
                            "image_url": img_url,
                            "bg_color": bg_color 
                        })
            except Exception as e:
                print(f"Error on {gift.full_name}: {e}")
                continue
            
            if len(result) >= 100:
                break

        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": f"خطای کلی: {str(e)}"}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
