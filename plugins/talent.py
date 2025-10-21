import asyncio
from fsub import Bot
from fsub.config import ADMINS 
from fsub.database import (
    add_talent,
    del_talent,
    get_talent,
    get_all_talents,
    give_strawberry,
    get_coin_balance,
    update_coin_balance,
    add_coins,
    # Fungsi VIP Baru
    set_vip_link,
    del_vip_link,
    add_vip_purchase,
    check_vip_purchase
)

from hydrogram import filters
# <--- PERUBAHAN: Import tombol ---
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from hydrogram.errors import PeerIdInvalid, UserIsBlocked, InputUserDeactivated, Forbidden, UserIsBot

# Biaya
RATE_COST = 10
VIP_COST = 2500 # <--- HARGA VIP BARU

# --- Perintah Admin ---

@Bot.on_message(filters.command("addtalent") & filters.user(ADMINS))
async def add_talent_command(client: Bot, message: Message):
    if len(message.command) < 2:
        return await message.reply("Gunakan format: /addtalent (user_id)")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply("User ID tidak valid. Harap masukkan angka.")
    if get_talent(user_id):
        return await message.reply("Talent ini sudah terdaftar.")
    try:
        user = await client.get_users(user_id)
        if user.is_bot:
             return await message.reply("Bot tidak bisa menjadi talent.")
        name = user.first_name
    except (PeerIdInvalid, ValueError):
        return await message.reply(f"User ID {user_id} tidak ditemukan.")
    except Exception as e:
        return await message.reply(f"Terjadi error saat mengambil data user: {e}")
    add_talent(user_id, name)
    await message.reply(f"✅ Sukses! **{name}** (`{user_id}`) telah ditambahkan sebagai talent.")


@Bot.on_message(filters.command("deltalent") & filters.user(ADMINS))
async def del_talent_command(client: Bot, message: Message):
    if len(message.command) < 2:
        return await message.reply("Gunakan format: /deltalent (user_id)")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply("User ID tidak valid.")
    if not get_talent(user_id):
        return await message.reply("Talent ini tidak ada di database.")
    if del_talent(user_id):
        await message.reply(f"✅ Sukses! Talent dengan ID `{user_id}` telah dihapus.")
    else:
        await message.reply("Gagal menghapus talent dari database.")


@Bot.on_message(filters.command("tfcoin") & filters.user(ADMINS))
async def transfer_coin_command(client: Bot, message: Message):
    if len(message.command) < 3:
        return await message.reply("Gunakan format: /tfcoin (user_id) (jumlah)")
    try:
        user_id = int(message.command[1])
        amount = int(message.command[2])
    except ValueError:
        return await message.reply("User ID atau jumlah tidak valid.")
    if amount <= 0:
        return await message.reply("Jumlah harus angka positif.")
    add_coins(user_id, amount)
    await message.reply(f"✅ Sukses mentransfer {amount} 🪙 coin ke user `{user_id}`.")
    try:
        await client.send_message(
            user_id,
            f"🎉 Selamat! Anda telah menerima **{amount} 🪙 coin** dari Admin."
        )
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid, Forbidden):
        await message.reply("(Notifikasi ke user gagal: Bot mungkin diblokir atau user tidak aktif.)")
    except Exception:
        pass


# --- Perintah Talent (BARU) ---

@Bot.on_message(filters.command("setvip") & filters.private)
async def set_vip_command(client: Bot, message: Message):
    """Talent mengatur link VIP mereka."""
    user_id = message.from_user.id
    if not get_talent(user_id):
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
    
    if len(message.command) < 2:
        return await message.reply("Gunakan format: /setvip (link)\n\nContoh:\n/setvip https://t.me/+linkprivasiAnda")
    
    link = message.command[1]
    if not (link.startswith("http://") or link.startswith("https://")):
        return await message.reply("Link tidak valid. Pastikan link diawali dengan http:// atau https://")
    
    set_vip_link(user_id, link)
    await message.reply("✅ **Link VIP Anda berhasil diatur!**\n\nMember sekarang bisa membeli akses ke link ini melalui daftar /talent.")


@Bot.on_message(filters.command("delvip") & filters.private)
async def del_vip_command(client: Bot, message: Message):
    """Talent menghapus link VIP mereka."""
    user_id = message.from_user.id
    if not get_talent(user_id):
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
    
    del_vip_link(user_id)
    await message.reply("✅ **Link VIP Anda telah dihapus.**\n\nMember tidak bisa lagi membelinya.")


# --- Perintah Pengguna (Diperbarui) ---

@Bot.on_message(filters.command("talent") & filters.private)
async def list_talents_command(client: Bot, message: Message):
    """Menampilkan daftar semua talent (dengan tombol VIP)."""
    talents = get_all_talents()
    if not talents:
        return await message.reply("Belum ada talent yang terdaftar.")

    text = "👑 **Daftar Talent** 👑\n\n"
    buttons = [] # List untuk semua baris tombol
    
    for i, talent in enumerate(talents):
        talent_name = talent['name']
        talent_id = talent['_id']
        talent_link = f"[{talent_name}](tg://user?id={talent_id})"
        
        line = f"{i+1}. {talent_link} | `{talent_id}`"
        
        row_buttons = [] # List untuk tombol di baris ini
        if talent.get('vip_link'): # Cek apakah talent punya link VIP
            line += " | ⭐️ **VIP**"
            row_buttons.append(
                InlineKeyboardButton(
                    f"Beli VIP {talent_name} ⭐️ ({VIP_COST} 🪙)", 
                    callback_data=f"buy_vip_{talent_id}"
                )
            )
        
        if talent['strawberries'] > 0:
            line += f" | 🍓{talent['strawberries']}"
            
        text += line + "\n"
        if row_buttons:
            buttons.append(row_buttons) # Tambahkan baris tombol

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await message.reply(text, reply_markup=reply_markup, disable_web_page_preview=True) 


@Bot.on_message(filters.command("rate") & filters.private)
async def rate_talent_command(client: Bot, message: Message):
    if len(message.command) < 2:
        return await message.reply(f"Gunakan format: /rate (user_id_talent)\nBiaya: {RATE_COST} 🪙 coin.")
    try:
        talent_id = int(message.command[1])
    except ValueError:
        return await message.reply("User ID talent tidak valid.")
    user = message.from_user 
    user_id = user.id
    if user_id == talent_id:
        return await message.reply("Anda tidak bisa me-rate diri sendiri.")
    talent = get_talent(talent_id)
    if not talent:
        return await message.reply("User ID tersebut bukan talent terdaftar.")
    is_admin = user_id in ADMINS
    final_balance_text = ""
    if not is_admin:
        balance = get_coin_balance(user_id)
        if balance < RATE_COST:
            return await message.reply(f"Coin Anda tidak cukup. Anda memiliki {balance} 🪙, dibutuhkan {RATE_COST} 🪙.")
        new_balance = balance - RATE_COST
        update_coin_balance(user_id, new_balance)
        final_balance_text = f"Sisa coin Anda: {new_balance} 🪙."
    else:
        final_balance_text = "Sisa coin Anda: ∞ (Tidak Terbatas)."
    try:
        give_strawberry(talent_id) 
        await message.reply(f"✅ Berhasil! Anda memberikan 1 🍓 ke **{talent['name']}**.\n{final_balance_text}")
        try:
            sender_name = user.first_name
            sender_id = user.id
            sender_link = f"[{sender_name}](tg://user?id={sender_id})"
            await client.send_message(
                talent_id,
                f"🎉 Selamat! Anda baru saja menerima 1 🍓 dari {sender_link}.",
                disable_web_page_preview=True 
            )
        except Exception:
            pass 
    except Exception as e:
        await message.reply(f"Terjadi error saat memproses rating: {e}")
        if not is_admin:
            add_coins(user_id, RATE_COST)


@Bot.on_message(filters.command("mycoins") & filters.private)
async def my_coins_command(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id in ADMINS:
        balance_text = "∞ (Tidak Terbatas)"
    else:
        balance = get_coin_balance(user_id)
        balance_text = f"**{balance}**"
    await message.reply(f"Anda memiliki: {balance_text} 🪙 coin.")


# --- Callback Handler (BARU) ---

@Bot.on_callback_query(filters.regex(r"^buy_vip_"))
async def handle_buy_vip_callback(client: Bot, query):
    """Menangani logika pembelian VIP saat tombol ditekan."""
    
    user = query.from_user
    user_id = user.id
    
    try:
        talent_id = int(query.data.split("_")[2])
    except (ValueError, IndexError):
        return await query.answer("Error: Tombol tidak valid.", show_alert=True)
        
    talent = get_talent(talent_id)
    if not talent or not talent.get('vip_link'):
        return await query.answer("Link VIP talent ini tidak lagi tersedia atau sudah dihapus.", show_alert=True)
    
    talent_link = talent['vip_link']
    talent_name = talent['name']
    
    # 1. Cek apakah user sudah pernah membeli
    if check_vip_purchase(user_id, talent_id):
        await query.answer("Anda sudah membeli akses ini. Link dikirim (lagi) ke PM Anda.", show_alert=False)
        try:
            return await client.send_message(user_id, f"Anda sudah memiliki akses VIP **{talent_name}**:\n{talent_link}\n\nMohon untuk tidak menyebarkannya.")
        except (UserIsBlocked, Forbidden):
            return await query.answer("Gagal mengirim PM. Apakah Anda memblokir bot?", show_alert=True)

    # 2. Cek apakah user adalah Admin (Admin gratis)
    is_admin = user_id in ADMINS
    
    if not is_admin:
        # 3. Cek koin (HANYA jika bukan admin)
        balance = get_coin_balance(user_id)
        if balance < VIP_COST:
            return await query.answer(f"Koin tidak cukup! Anda punya {balance} 🪙, butuh {VIP_COST} 🪙.", show_alert=True)
        
        # 4. Kurangi koin (HANYA jika bukan admin)
        update_coin_balance(user_id, balance - VIP_COST)

    # 5. Proses pembelian (Admin dan User)
    add_vip_purchase(user_id, talent_id) # Catat pembelian
    
    await query.answer("Pembelian sukses! Link dikirim ke PM Anda.", show_alert=True)
    
    # 6. Kirim link ke user
    try:
        await client.send_message(user_id, f"🎉 Terima kasih! Ini adalah link VIP eksklusif untuk **{talent_name}**:\n\n{talent_link}\n\nMohon untuk tidak menyebarkannya.")
    except (UserIsBlocked, Forbidden):
        # Jika gagal kirim PM, pembelian tetap tercatat, tapi user harus "unblock"
        pass 
        
    # 7. Kirim notifikasi ke Talent
    try:
        sender_link = f"[{user.first_name}](tg://user?id={user_id})"
        await client.send_message(
            talent_id,
            f"🎉 Kabar baik! {sender_link} baru saja membeli akses VIP Anda seharga {VIP_COST} 🪙!"
        )
    except Exception:
        pass # Gagal secara diam-diam jika talent blokir bot
