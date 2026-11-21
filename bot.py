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
                # گرفتن اطلاعات کامل گیفت (شامل مدل آپگرید شده)
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    if name not in seen:
                        seen.add(name)
                        
                        # 1. استخراج قیمت
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        # 2. استخراج لینک تلگرام
                        # کتابخانه معمولاً لینک رو در فیلد name یا slug یا id ذخیره میکنه
                        slug = info.get('slug', '') or info.get('name', '')
                        # اگر slug خالی بود، از اسم گیفت برای لینک استفاده میکنیم
                        if not slug:
                            slug = gift.full_name
                        gift_link = f"https://t.me/nft/{slug}"
                        
                        # 3. استخراج عکس (اولویت با وب‌پی یا عکس اصلی)
                        links = info.get('links', {})
                        img_url = links.get('webp', '') or links.get('png', '') or links.get('jpg', '')
                        
                        # 4. استخراج رنگ پس‌زمینه
                        # تلگرام رنگ رو معمولاً در فیلد background_color یا background ذخیره میکنه
                        bg_color = info.get('background_color', '') or info.get('background', '')
                        
                        # اگر رنگ به صورت "center" یا "none" بود، خالی می‌کنیم تا فرانت‌اند رنگ پیش‌فرض خودش رو بذاره
                        if bg_color in ['center', 'none', 'transparent', '']:
                            bg_color = ''
                        elif not bg_color.startswith('#') and bg_color:
                            # اگر کد رنگ بدون # بود، اضافه میکنیم
                            bg_color = f"#{bg_color}"
                        
                        # 🔴 پرینت برای دیباگ (در بخش Logs در Railway اینها رو می‌بینی)
                        print(f"--- DEBUG: {name} ---")
                        print(f"Link: {gift_link}")
                        print(f"BgColor: {bg_color}")
                        print(f"Image: {img_url}")
                        print(f"-----------------------")

                        result.append({
                            "name": name,
                            "price": price,
                            "link": gift_link,
                            "image_url": img_url,
                            "bg_color": bg_color 
                        })
            except Exception as e:
                # در صورت خطا در یک گیفت، بقیه ادامه پیدا کنند
                print(f"Error processing gift {gift.full_name}: {e}")
                continue
            
            # محدودیت 600 تایی برای جلوگیری از کرش کردن سرور
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
