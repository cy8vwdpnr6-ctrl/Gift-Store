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

# 🔴 اینجا حالت کش رو روی HTTP تنظیم کردیم که به git نیاز نداشته باشه
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
                        
                        # 🔴 استخراج شماره و لینک عکس
                        # کتابخانه معمولاً شماره سریال و آیدی مدل رو داره
                        serial_num = info.get('slug', '') or info.get('id', '')
                        
                        # برای عکس، از لینک مستقیم CDN تلگرام یا فایل لوکال استفاده می‌کنیم
                        # فعلاً یه لینک پیش‌فرض می‌ذاریم، بعدا درستش می‌کنیم
                        img_url = info.get('sticker', {}).get('thumb_url', '') 
                        
                        result.append({
                            "name": name,
                            "price": price,
                            "serial": f"#{serial_num}" if serial_num else "#000",
                            "image_url": img_url
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
