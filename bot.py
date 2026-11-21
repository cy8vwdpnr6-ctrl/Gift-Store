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
gifts_lib = TelegramGifts()

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("از مینی‌اپ استفاده کن!")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        # ۱. گرفتن لیست گیفت‌های معمولی برای داشتن اسم‌ها
        regular_gifts = gifts_lib.get_regular_gifts()
        
        result = []
        seen = set()

        for gift in regular_gifts:
            try:
                # ۲. تلاش برای گرفتن نسخه آپگرید شده با همون اسم
                # طبق مستندات، پارامتر gift_type="upgraded" باید کار کنه
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    if name not in seen:
                        seen.add(name)
                        # ۳. قیمت رو از دیکشنری prices می‌خونیم
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        result.append({
                            "name": name,
                            "price": price,
                            "image_url": ""
                        })
            except Exception:
                # اگر برای یک گیفت خطا داد، ازش رد شو و برو بعدی
                continue
            
            if len(result) >= 600:
                break

        if not result:
            return {"status": "error", "message": "هیچ گیفت آپگرید شده‌ای پیدا نشد."}
            
        return {"status": "success", "data": result}
        
    except Exception as e:
        # این خطا رو برمی‌گردونیم تا توی مینی‌اپ ببینیم
        return {"status": "error", "message": f"خطای کلی: {str(e)}"}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
