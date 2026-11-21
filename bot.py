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
                        
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        slug = info.get('slug', '')
                        gift_link = f"https://t.me/nft/{slug}" if slug else ""
                        
                        img_url = info.get('links', {}).get('webp', '')
                        
                        # 🔴 استخراج رنگ پس‌زمینه
                        # تلگرام معمولاً اینو به صورت هگز (مثل #ff0000) میده
                        bg_color = info.get('background_color', '') or info.get('bg_color', '')
                        
                        result.append({
                            "name": name,
                            "price": price,
                            "link": gift_link,
                            "image_url": img_url,
                            "bg_color": bg_color # ارسال رنگ به فرانت‌اند
                        })
            except Exception:
                continue
            
            if len(result) >= 600:
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
