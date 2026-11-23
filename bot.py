import os
import asyncio
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import random
import string
from datetime import datetime, timezone

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ⚠️ توکن‌ها باید از محیط (Environment Variables) خونده بشن
PORTALS_TOKEN = os.getenv("PORTALS_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_KV_NAMESPACE_ID = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID", "")

BOT_USERNAME = "NftsHubbot"  # یوزرنیم ربات خودت
INVITE_REWARD = 0.5           # پاداش هر دعوت به تون
MIN_DEPOSIT_FOR_WITHDRAW = 1.0  # حداقل شارژ برای برداشت

COLOR_MAP = {
    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000", "Gold": "#FFD700"
}

# =========================================================
# Cloudflare KV Helper
# =========================================================
async def save_to_kv(key: str, value: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, content=value)
        return response.status_code == 200

async def get_from_kv(key: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None

async def delete_from_kv(key: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        await client.delete(url, headers=headers)

# =========================================================
# ذخیره و بازیابی اطلاعات کاربر
# =========================================================
async def get_user_data(user_id: str) -> dict:
    raw = await get_from_kv(f"user_data_{user_id}")
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {
        "user_id": user_id,
        "balance": 0.0,
        "total_deposited": 0.0,   # مجموع شارژ تون
        "total_purchases": 0,     # تعداد خرید موفق
        "invited_by": None,
        "invited_users": [],      # لیست آیدی کاربرانی که این شخص دعوت کرده
        "rewards_earned": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

async def save_user_data(user_id: str, data: dict):
    await save_to_kv(f"user_data_{user_id}", json.dumps(data))

# =========================================================
# تلگرام
# =========================================================
async def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not YOUR_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print(f"❌ Telegram: {e}")

FIXED_END_TIME = "2026-11-28T23:59:59+00:00"

# =========================================================
# API گیت‌ها
# =========================================================
@app.get("/api/gifts")
async def get_gifts_api(offset: int = 0, limit: int = 50):
    try:
        import aportalsmp
        result = []
        seen_links = set()
        listings = await aportalsmp.search(
            authData=PORTALS_TOKEN, gift_name="", limit=limit, offset=offset, sort="price_asc"
        )
        for gift in listings:
            name = getattr(gift, 'name', 'Unknown')
            price = getattr(gift, 'price', 0)
            tg_id = getattr(gift, 'tg_id', '')
            clean_name = name.replace(" ", "").replace("'", "")
            link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else f"https://t.me/nft/{clean_name}"
            if link in seen_links: continue
            seen_links.add(link)
            img_url = getattr(gift, 'photo_url', '') or ""
            color_name = getattr(gift, 'backdrop', '')
            bg_color = COLOR_MAP.get(color_name, "#1c1c1e")
            result.append({
                "name": name, "price": price, "link": link, "image_url": img_url, "bg_color": bg_color
            })
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"خطا: {str(e)}"}

@app.get("/api/timer")
async def get_timer():
    end_time = datetime.fromisoformat(FIXED_END_TIME)
    now = datetime.now(timezone.utc)
    remaining = max(0, (end_time - now).total_seconds())
    return {"status": "success", "end_time": FIXED_END_TIME, "remaining_seconds": int(remaining)}

# =========================================================
# ورود به مینی‌اپ + مدیریت دعوت
# =========================================================
@app.post("/api/webapp/login")
async def webapp_login(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        username = data.get("username", "No Username")
        first_name = data.get("first_name", "")
        start_param = data.get("start_param", None)
        platform = data.get("platform", "unknown")
        version = data.get("version", "unknown")

        if not user_id or user_id == "Unknown":
            raise HTTPException(status_code=400, detail="user_id required")

        client_ip = request.headers.get("x-forwarded-for", request.client.host)
        if "," in client_ip: client_ip = client_ip.split(",")[0].strip()

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        user_data = await get_user_data(user_id)
        is_new_user = user_data["created_at"] == user_data.get("created_at") and len(user_data["invited_users"]) == 0 and user_data["balance"] == 0

        # 🎯 منطق دعوت
        if start_param and start_param.startswith("ref_"):
            referrer_id = start_param.replace("ref_", "")
            if referrer_id != user_id and user_data["invited_by"] is None:
                # ثبت دعوت
                user_data["invited_by"] = referrer_id
                await save_user_data(user_id, user_data)

                # پاداش به دعوت‌کننده
                referrer_data = await get_user_data(referrer_id)
                if user_id not in referrer_data["invited_users"]:
                    referrer_data["invited_users"].append(user_id)
                    referrer_data["balance"] += INVITE_REWARD
                    referrer_data["rewards_earned"] += INVITE_REWARD
                    await save_user_data(referrer_id, referrer_data)

                    # اطلاع‌رسانی
                    await send_telegram_message(
                        f"🎁 <b>پاداش دعوت جدید!</b>\n\n"
                        f"👤 کاربر @{username} (<code>{user_id}</code>) با لینک شما وارد شد.\n"
                        f"💰 <b>+{INVITE_REWARD} TON</b> به موجودی شما اضافه شد.\n"
                        f"📊 موجودی جدید دعوت‌کننده: <b>{referrer_data['balance']:.2f} TON</b>"
                    )
        elif start_param and start_param.isdigit() and start_param != user_id:
            # پشتیبانی از لینک با آیدی مستقیم
            referrer_id = start_param
            if user_data["invited_by"] is None:
                user_data["invited_by"] = referrer_id
                await save_user_data(user_id, user_data)

                referrer_data = await get_user_data(referrer_id)
                if user_id not in referrer_data["invited_users"]:
                    referrer_data["invited_users"].append(user_id)
                    referrer_data["balance"] += INVITE_REWARD
                    referrer_data["rewards_earned"] += INVITE_REWARD
                    await save_user_data(referrer_id, referrer_data)

        # پیام ورود
        message_text = (
            f"🚪 <b>ورود / استارت</b>\n\n"
            f"👤 <b>نام:</b> {first_name}\n"
            f"🆔 <b>آیدی:</b> <code>{user_id}</code>\n"
            f"📱 <b>یوزرنیم:</b> @{username}\n"
            f"🌐 <b>آی‌پی:</b> <code>{client_ip}</code>\n"
            f"📟 <b>دستگاه:</b> {platform} ({version})\n"
            f"🔗 <b>start_param:</b> {start_param or 'ندارد'}\n"
            f"⏰ <b>زمان:</b> {now_str}\n"
            f"💰 <b>موجودی:</b> {user_data['balance']:.2f} TON"
        )
        await send_telegram_message(message_text)

        return {
            "status": "success",
            "balance": user_data["balance"],
            "can_withdraw": check_can_withdraw(user_data),
            "user_data": user_data
        }
    except Exception as e:
        print(f"❌ خطا: {e}")
        return {"status": "error", "message": str(e)}

def check_can_withdraw(user_data: dict) -> bool:
    return (user_data["balance"] >= MIN_DEPOSIT_FOR_WITHDRAW) or (user_data["total_purchases"] > 0) or (user_data["total_deposited"] >= MIN_DEPOSIT_FOR_WITHDRAW)

# =========================================================
# دریافت موجودی کاربر
# =========================================================
@app.get("/api/user/balance")
async def get_balance(user_id: str):
    data = await get_user_data(user_id)
    return {"status": "success", "balance": data["balance"], "can_withdraw": check_can_withdraw(data), "user_data": data}

# =========================================================
# ثبت تراکنش (شارژ / خرید)
# =========================================================
@app.post("/api/transaction/record")
async def record_transaction(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        amount = float(data.get("amount", 0))
        tx_type = data.get("type", "deposit")  # deposit / purchase
        description = data.get("description", "")
        tx_hash = data.get("tx_hash", "")

        if not user_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid data")

        user_data = await get_user_data(user_id)

        if tx_type == "deposit":
            user_data["balance"] += amount
            user_data["total_deposited"] += amount
        elif tx_type == "purchase":
            user_data["total_purchases"] += 1
            # خرید از موجودی کم نمی‌شه، چون کاربر مستقیم از کیف پولش می‌ده

        await save_user_data(user_id, user_data)

        await send_telegram_message(
            f"💸 <b>تراکنش جدید</b>\n\n"
            f"👤 کاربر: <code>{user_id}</code>\n"
            f"📊 نوع: {tx_type}\n"
            f"💵 مبلغ: {amount} TON\n"
            f"📝 توضیح: {description}\n"
            f"🔗 هش: <code>{tx_hash[:20] if tx_hash else 'N/A'}</code>\n"
            f"💰 موجودی جدید: <b>{user_data['balance']:.2f} TON</b>"
        )

        return {"status": "success", "balance": user_data["balance"], "can_withdraw": check_can_withdraw(user_data)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# درخواست برداشت
# =========================================================
@app.post("/api/withdraw")
async def request_withdraw(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        amount = float(data.get("amount", 0))
        wallet_address = data.get("wallet_address", "")

        user_data = await get_user_data(user_id)

        # ✅ چک شرط برداشت
        if not check_can_withdraw(user_data):
            return {
                "status": "error",
                "code": "NOT_ELIGIBLE",
                "message": "To withdraw, you must have at least one TON in your balance (charged/deposited) or have made at least one purchase."
            }

        if amount <= 0:
            return {"status": "error", "message": "Invalid amount"}
        if user_data["balance"] < amount:
            return {"status": "error", "message": "Insufficient balance"}

        user_data["balance"] -= amount
        await save_user_data(user_id, user_data)

        await send_telegram_message(
            f"🔴 <b>درخواست برداشت</b>\n\n"
            f"👤 کاربر: <code>{user_id}</code>\n"
            f"💵 مبلغ: {amount} TON\n"
            f"👛 کیف پول: <code>{wallet_address}</code>"
        )

        return {"status": "success", "message": "Withdrawal request submitted", "new_balance": user_data["balance"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/invite/check")
async def check_invite(code: str):
    value = await get_from_kv(code)
    return {"status": "success", "valid": bool(value), "invited_by": value or None}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
