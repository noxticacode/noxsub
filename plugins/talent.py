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
    add_coins
)

from hydrogram import filters
from hydrogram.types import Message
from hydrogram.errors import PeerIdInvalid, UserIsBlocked, InputUserDeactivated

# Biaya untuk memberikan 1 🍓
RATE_COST = 10

# --- Perintah Admin ---

@Bot.on_message(filters.command("addtalent") & filters.user(ADMINS))
async def add_talent_command(client: Bot, message: Message):
    """Menambahkan user sebagai talent. Format: /addtalent (user_id)"""
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
        name = user.first_name
    except (PeerIdInvalid, ValueError):
        return await message.reply(f"User ID {user_id} tidak ditemukan.")
    except Exception as e:
        return await message.reply(f"Terjadi error saat mengambil data user: {e}")

    add_talent(user_id, name)
    await message.reply(f"✅ Sukses! **{name}** (`{user_id}`) telah ditambahkan sebagai talent.")


@Bot.on_message(filters.command("deltalent") & filters.user(ADMINS))
async def del_talent_command(client: Bot, message: Message):
    """Menghapus talent. Format: /deltalent (user_id)"""
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
    """Mentransfer koin ke user. Format: /tfcoin (user_id) (jumlah)"""
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
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
        await message.reply("(Notifikasi ke user gagal: Bot mungkin diblokir atau user tidak aktif.)")
    except Exception:
        pass


# --- Perintah Pengguna ---

@Bot.on_message(filters.command("talent") & filters.private)
async def list_talents_command(client: Bot, message: Message):
    """Menampilkan daftar semua talent."""
    talents = get_all_talents()
    if not talents:
        return await message.reply("Belum ada talent yang terdaftar.")

    text = "👑 **Daftar Talent** 👑\n\n"
    for i, talent in enumerate(talents):
        talent_name = talent['name']
        talent_id = talent['_id']
        talent_link = f"[{talent_name}](tg://user?id={talent_id})"
        
        text += f"{i+1}. {talent_link} | `{talent_id}`"
        
        if talent['strawberries'] > 0:
            text += f" | 🍓{talent['strawberries']}"
        text += "\n"

    await message.reply(text, disable_web_page_preview=True) 


@Bot.on_message(filters.command("rate") & filters.private)
async def rate_talent_command(client: Bot, message: Message):
    """Memberikan 🍓 ke talent. Format: /rate (user_id_talent)"""
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
    """Cek saldo koin pribadi."""
    user_id = message.from_user.id
    if user_id in ADMINS:
        balance_text = "∞ (Tidak Terbatas)"
    else:
        # <--- PERUBAHAN DI SINI: user_D diubah menjadi user_id ---
        balance = get_coin_balance(user_id) 
        balance_text = f"**{balance}**"

    await message.reply(f"Anda memiliki: {balance_text} 🪙 coin.")
