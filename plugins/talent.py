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
    set_vip_channel, # <--- PERUBAHAN
    del_vip_channel, # <--- PERUBAHAN
    add_vip_purchase,
    check_vip_purchase
)

from hydrogram import filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
# <--- PERUBAHAN: Import tambahan ---
from hydrogram.enums import ChatMemberStatus
from hydrogram.errors import (
    PeerIdInvalid, UserIsBlocked, InputUserDeactivated, Forbidden, UserIsBot,
    UserNotParticipant, Unauthorized
)

# Biaya
RATE_COST = 10
VIP_COST = 2500 

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


# --- Perintah Talent (DIPERBARUI) ---

@Bot.on_message(filters.command("setvip") & filters.private)
async def set_vip_command(client: Bot, message: Message):
    """Talent mengatur channel VIP mereka."""
    user_id = message.from_user.id
    if not get_talent(user_id):
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
    
    if len(message.command) < 2:
        return await message.reply(
            "Gunakan format: /setvip (Chat ID Channel)\n\n"
            "**PENTING:**\n"
            "1. Channel Anda HARUS channel pribadi (Private).\n"
            "2. Bot ini HARUS menjadi **Admin** di channel tersebut dengan izin 'Undang Pengguna via Link'.\n"
            "3. Untuk mendapatkan Chat ID, gunakan bot seperti @RawDataBot (forward pesan dari channel Anda ke sana)."
        )
    
    try:
        chat_id_str = message.command[1]
        if not chat_id_str.startswith("-100"):
            return await message.reply("Chat ID tidak valid. Harus berupa ID channel pribadi (diawali -100).")
        
        chat_id = int(chat_id_str)
        
        # <--- PERUBAHAN: Validasi Bot adalah Admin ---
        try:
            chat = await client.get_chat(chat_id)
            member = await client.get_chat_member(chat_id, "me")
            
            if member.status != ChatMemberStatus.ADMINISTRATOR or not member.can_invite_users:
                return await message.reply("Gagal! Saya harus menjadi Admin di channel tersebut dan memiliki izin 'Undang Pengguna via Link'.")

        except (Unauthorized, UserNotParticipant):
            return await message.reply("Gagal mengakses channel. Pastikan saya telah ditambahkan ke channel tersebut dan menjadi admin.")
        except Exception as e:
            return await message.reply(f"Error saat memvalidasi channel: {e}")
        
        # Simpan jika validasi sukses
        set_vip_channel(user_id, chat_id, chat.title)
        await message.reply(f"✅ **Channel VIP Anda berhasil diatur!**\n\nNama Channel: {chat.title}\nMember sekarang bisa membeli akses ke channel ini.")
        
    except ValueError:
        return await message.reply("Chat ID harus berupa angka.")
    except Exception as e:
        await message.reply(f"Terjadi error tak terduga: {e}")


@Bot.on_message(filters.command("delvip") & filters.private)
async def del_vip_command(client: Bot, message: Message):
    """Talent menghapus channel VIP mereka."""
    user_id = message.from_user.id
    talent = get_talent(user_id)
    if not talent:
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
    
    if not talent.get('vip_chat_id'):
        return await message.reply("Anda belum mengatur channel VIP.")
        
    del_vip_channel(user_id)
    await message.reply("✅ **Channel VIP Anda telah dihapus.**\n\nMember tidak bisa lagi membelinya.")


# --- Perintah Pengguna (Diperbarui) ---

@Bot.on_message(filters.command("talent") & filters.private)
async def list_talents_command(client: Bot, message: Message):
    """Menampilkan daftar semua talent (dengan tombol VIP)."""
    talents = get_all_talents()
    if not talents:
        return await message.reply("Belum ada talent yang terdaftar.")

    text = "👑 **Daftar Talent** 👑\n\n"
    buttons = [] 
    
    for i, talent in enumerate(talents):
        talent_name = talent['name']
        talent_id = talent['_id']
        talent_link = f"[{talent_name}](tg://user?id={talent_id})"
        
        line = f"{i+1}. {talent_link} | `{talent_id}`"
        
        row_buttons = [] 
        
        # <--- PERUBAHAN: Cek 'vip_chat_id' ---
        if talent.get('vip_chat_id'): 
            vip_title = talent.get('vip_chat_title', 'VIP')
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
            buttons.append(row_buttons) 

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await message.reply(text, reply_markup=reply_markup, disable_web_page_preview=True) 


@Bot.on_message(filters.command("rate") & filters.private)
async def rate_talent_command(client: Bot, message: Message):
    # (Fungsi ini tidak berubah, dibiarkan apa adanya)
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
    # (Fungsi ini tidak berubah, dibiarkan apa adanya)
    user_id = message.from_user.id
    if user_id in ADMINS:
        balance_text = "∞ (Tidak Terbatas)"
    else:
        balance = get_coin_balance(user_id)
        balance_text = f"**{balance}**"
    await message.reply(f"Anda memiliki: {balance_text} 🪙 coin.")


# --- Callback Handler (DIPERBARUI) ---

@Bot.on_callback_query(filters.regex(r"^buy_vip_"))
async def handle_buy_vip_callback(client: Bot, query):
    """Menangani logika pembelian VIP (sekarang dengan link sekali pakai)."""
    
    user = query.from_user
    user_id = user.id
    
    try:
        talent_id = int(query.data.split("_")[2])
    except (ValueError, IndexError):
        return await query.answer("Error: Tombol tidak valid.", show_alert=True)
        
    talent = get_talent(talent_id)
    # <--- PERUBAHAN: Cek 'vip_chat_id' ---
    if not talent or not talent.get('vip_chat_id'):
        return await query.answer("Channel VIP talent ini tidak lagi tersedia.", show_alert=True)
    
    vip_chat_id = talent['vip_chat_id']
    talent_name = talent['name']
    
    # 1. Cek apakah user SUDAH BERGABUNG di channel
    try:
        member = await client.get_chat_member(vip_chat_id, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await query.answer(f"Anda sudah menjadi anggota di channel VIP {talent_name}.", show_alert=True)
    except UserNotParticipant:
        pass # User belum bergabung, lanjutkan proses pembelian
    except Exception as e:
        return await query.answer(f"Error saat cek keanggotaan: {e}", show_alert=True)

    # 2. Cek apakah user pernah membeli (untuk re-join gratis jika dia keluar)
    if check_vip_purchase(user_id, talent_id):
        await query.answer("Anda sudah pernah membeli akses ini. Link undangan baru (sekali pakai) dikirim ke PM Anda.", show_alert=False)
        # Lanjutkan ke proses pembuatan link di bawah, tapi lewati cek koin
    
    else:
        # 3. Cek apakah user adalah Admin (Admin gratis)
        is_admin = user_id in ADMINS
        
        if not is_admin:
            # 4. Cek koin (HANYA jika bukan admin & pembelian pertama)
            balance = get_coin_balance(user_id)
            if balance < VIP_COST:
                return await query.answer(f"Koin tidak cukup! Anda punya {balance} 🪙, butuh {VIP_COST} 🪙.", show_alert=True)
            
            # 5. Kurangi koin (HANYA jika bukan admin & pembelian pertama)
            update_coin_balance(user_id, balance - VIP_COST)
            
        # 6. Catat pembelian (HANYA untuk pembelian pertama)
        add_vip_purchase(user_id, talent_id) 
        await query.answer("Pembelian sukses! Link undangan (sekali pakai) dikirim ke PM Anda.", show_alert=True)
    

    # 7. Proses pembuatan link (Untuk pembelian baru ATAU re-join)
    try:
        # <--- PERUBAHAN UTAMA: Buat link sekali pakai ---
        link = await client.create_chat_invite_link(
            chat_id=vip_chat_id,
            member_limit=1 # Hanya untuk 1 pengguna
            # Anda juga bisa menambahkan `expire_date` jika mau
        )
        invite_link = link.invite_link
        
        # 8. Kirim link ke user
        await client.send_message(
            user_id, 
            f"🎉 Terima kasih! Ini adalah link undangan *sekali pakai* Anda untuk channel VIP **{talent_name}**:\n\n"
            f"{invite_link}\n\n"
            f"Link ini hanya bisa digunakan 1 kali. Mohon untuk tidak keluar dari channel."
        )
        
    except (UserIsBlocked, Forbidden):
        return await query.answer("Gagal mengirim PM. Apakah Anda memblokir bot?", show_alert=True)
    except Exception as e:
        return await query.answer(f"Gagal membuat link undangan: {e}", show_alert=True)

    # 9. Kirim notifikasi ke Talent (hanya jika pembelian pertama)
    if not check_vip_purchase(user_id, talent_id): # Cek lagi, karena sekarang sudah dicatat
        try:
            sender_link = f"[{user.first_name}](tg://user?id={user_id})"
            await client.send_message(
                talent_id,
                f"🎉 Kabar baik! {sender_link} baru saja membeli akses VIP Anda seharga {VIP_COST} 🪙!"
            )
        except Exception:
            pass # Gagal secara diam-diam
