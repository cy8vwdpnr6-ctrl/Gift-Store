import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔴 توکنی که از مرورگر کپی کردی رو اینجا بذار
PORTALS_TOKEN = "tma query_id=... (توکن خودت رو اینجا بذار)"

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        import aportalsmp  # اینجا import میکنیم که اگه نبود، کرش نکنه
        
        # جستجوی امن‌تر با پارامترهای استاندارد
        listings = await aportalsmp.search(
            authData=PORTALS_TOKEN,
            gift_name="",  # همه گیفت‌ها
            limit=50,
            sort="price_asc"
        )
        
        result = []
        for gift in listings:
            # استفاده از getattr برای جلوگیری از خطای فیلدهای ناموجود
            name = getattr(gift, 'name', 'Unknown')
            price = getattr(gift, 'price', 0)
            
            # ساخت لینک واقعی با tg_id
            tg_id = getattr(gift, 'tg_id', '')
            clean_name = name.replace(" ", "").replace("'", "")
            link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else ""
            
            img_url = getattr(gift, 'photo_url', '')
            bg_color = getattr(gift, 'backdrop', '') or "#1c1c1e"
            
            result.append({
                "name": name,
                "price": price,
                "link": link,
                "image_url": img_url,
                "bg_color": bg_color
            })
            
        return {"status": "success", "data": result}
        
    except ImportError as e:
        return {"status": "error", "message": f"کتابخانه نصب نیست: {str(e)}"}
    except Exception as e:
        # برگرداندن خطای دقیق به جای کرش کردن
        return {"status": "error", "message": f"خطا در ارتباط با پورتالز: {str(e)}"}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
