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
                        
                        # 2. لینک (slug)
                        slug = info.get('slug', '')
                        if not slug:
                            slug = name.lower().replace(" ", "").replace("'", "")
                        gift_link = f"https://t.me/nft/{slug}"
                        
                        # 3. عکس
                        links = info.get('links', {})
                        img_url = links.get('webp', '') or links.get('png', '') or links.get('jpg', '')
                        
                        # 4. بک‌گراند
                        backdrop = info.get('backdrop', {})
                        bg_color = ""
                        
                        if isinstance(backdrop, dict):
                            c_from = backdrop.get('gradient_from') or backdrop.get('center_color')
                            c_to = backdrop.get('gradient_to') or backdrop.get('edge_color')
                            
                            if c_from:
                                if isinstance(c_from, int):
                                    bg_color = f"#{c_from:06x}"
                                elif isinstance(c_from, str) and not c_from.startswith('#'):
                                    bg_color = f"#{c_from}"
                                elif isinstance(c_from, str):
                                    bg_color = c_from
                                    
                                if c_to:
                                    if isinstance(c_to, int):
                                        c_to_hex = f"#{c_to:06x}"
                                    elif isinstance(c_to, str) and not c_to.startswith('#'):
                                        c_to_hex = f"#{c_to}"
                                    else:
                                        c_to_hex = c_to
                                    bg_color = f"linear-gradient(135deg, {bg_color}, {c_to_hex})"
                        
                        if not bg_color:
                            bg_color = info.get('background_color', '') or info.get('bg_color', '')
                            if bg_color and not str(bg_color).startswith('#'):
                                bg_color = f"#{bg_color}"

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
