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
    set_vip_channel,
    del_vip_channel,
    add_vip_purchase,
    check_vip_purchase,
    # --- Import BARU ---
    set_talent_bio,
    get_top_talents,
    revoke_vip_purchase
)

from hydrogram import filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from hydrogram.enums import ChatMemberStatus
from hydrogram.errors import (
    PeerIdInvalid, UserIsBlocked, InputUserDeactivated, Forbidden, UserIsBot,
    UserNotParticipant, Unauthorized, ChatAdminRequired
)

# Biaya
RATE_COST = 10
VIP_COST = 2500 
# Batas Karakter Bio
BIO_LIMIT = 150

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

# --- Perintah Admin BARU ---

@Bot.on_message(filters.command("revokevip") & filters.user(ADMINS))
async def revoke_vip_command(client: Bot, message: Message):
    """Admin mencabut akses VIP member dari channel talent."""
    if len(message.command) < 3:
        return await message.reply("Gunakan format: /revokevip (talent_id) (user_id_member)")
        
    try:
        talent_id = int(message.command[1])
        member_id = int(message.command[2])
    except ValueError:
        return await message.reply("ID Talent atau ID Member tidak valid.")
        
    talent = get_talent(talent_id)
    if not talent or not talent.get('vip_chat_id'):
        return await message.reply("Talent ini tidak ditemukan atau belum mengatur channel VIP.")
        
    vip_chat_id = talent['vip_chat_id']
    
    # Langkah 1: Hapus dari database
    if not revoke_vip_purchase(member_id, talent_id):
        await message.reply("Gagal: Member tersebut tidak ditemukan di database pembelian. Mungkin sudah dicabut?")
    else:
        await message.reply("✅ Catatan pembelian member dari database telah dihapus.")
        
    # Langkah 2: Tendang (Kick) dari channel
    try:
        # Menggunakan ban_chat_member + unban_chat_member = Kick
        await client.ban_chat_member(vip_chat_id, member_id)
        await client.unban_chat_member(vip_chat_id, member_id)
        await message.reply(f"✅ Member `{member_id}` telah berhasil dikeluarkan dari channel VIP `{vip_chat_id}`.")
    except UserNotParticipant:
        await message.reply("Info: Member tersebut sudah tidak ada di dalam channel.")
    except ChatAdminRequired:
        await message.reply("Gagal: Saya tidak memiliki hak admin untuk menendang member di channel tersebut.")
    except Exception as e:
        await message.reply(f"Gagal menendang member: {e}")


# --- Perintah Talent ---

@Bot.on_message(filters.command("setvip") & filters.private)
async def set_vip_command(client: Bot, message: Message):
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
        try:
            chat = await client.get_chat(chat_id)
            member = await client.get_chat_member(chat_id, "me")
            if member.status != ChatMemberStatus.ADMINISTRATOR or not (member.privileges and member.privileges.can_invite_users):
                return await message.reply("Gagal! Saya harus menjadi Admin di channel tersebut dan memiliki izin 'Undang Pengguna via Link'.")
        except (Unauthorized, UserNotParticipant):
            return await message.reply("Gagal mengakses channel. Pastikan saya telah ditambahkan ke channel tersebut dan menjadi admin.")
        except Exception as e:
            return await message.reply(f"Error saat memvalidasi channel: {e}")
        set_vip_channel(user_id, chat_id, chat.title)
        await message.reply(f"✅ **Channel VIP Anda berhasil diatur!**\n\nNama Channel: {chat.title}\nMember sekarang bisa membeli akses ke channel ini.")
    except ValueError:
        return await message.reply("Chat ID harus berupa angka.")
    except Exception as e:
        await message.reply(f"Terjadi error tak terduga: {e}")


@Bot.on_message(filters.command("delvip") & filters.private)
async def del_vip_command(client: Bot, message: Message):
    user_id = message.from_user.id
    talent = get_talent(user_id)
    if not talent:
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
    if not talent.get('vip_chat_id'):
        return await message.reply("Anda belum mengatur channel VIP.")
    del_vip_channel(user_id)
    await message.reply("✅ **Channel VIP Anda telah dihapus.**\n\nMember tidak bisa lagi membelinya.")

# --- Perintah Talent BARU ---

@Bot.on_message(filters.command("setbio") & filters.private)
async def set_bio_command(client: Bot, message: Message):
    """Talent mengatur bio profil mereka."""
    user_id = message.from_user.id
    if not get_talent(user_id):
        return await message.reply("Perintah ini hanya untuk Talent yang terdaftar.")
        
    try:
        bio = message.text.split(None, 1)[1]
    except IndexError:
        return await message.reply(f"Gunakan format: /setbio (deskripsi singkat Anda)\n\nContoh:\n/setbio Hai, aku Lily! Cek VIP-ku ya.")
        
    if len(bio) > BIO_LIMIT:
        return await message.reply(f"Bio terlalu panjang. Maksimal {BIO_LIMIT} karakter. (Anda: {len(bio)})")
        
    set_talent_bio(user_id, bio)
    await message.reply(f"✅ **Bio Anda berhasil diperbarui!**\n\nBio baru: *{bio}*")


# --- Perintah Pengguna ---

@Bot.on_message(filters.command("talent") & filters.private)
async def list_talents_command(client: Bot, message: Message):
    """Menampilkan daftar semua talent (dengan bio)."""
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
        
        # Tambahkan status VIP
        if talent.get('vip_chat_id'): 
            line += " | ⭐️ **VIP**"
            row_buttons.append(
                InlineKeyboardButton(
                    f"Beli VIP {talent_name} ⭐️ ({VIP_COST} 🪙)", 
                    callback_data=f"buy_vip_{talent_id}"
                )
            )
        
        # Tambahkan status 🍓
        if talent['strawberries'] > 0:
            line += f" | 🍓{talent['strawberries']}"
            
        text += line + "\n"
        
        # <--- PERUBAHAN: Tampilkan Bio ---
        if talent.get('bio'):
            text += f"   └─ *\"{talent.get('bio')}\"*\n"
        # ---------------------------------
            
        if row_buttons:
            buttons.append(row_buttons) 

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await message.reply(text, reply_markup=reply_markup, disable_web_page_preview=True) 

# --- Perintah Pengguna BARU ---

@Bot.on_message(filters.command("toptalent") & filters.private)
async def top_talents_command(client: Bot, message: Message):
    """Menampilkan papan peringkat talent."""
    top_list = get_top_talents(limit=10) # Ambil 10 teratas
    
    if not top_list:
        return await message.reply("Belum ada talent yang memiliki 🍓.")
        
    text = "🏆 **Papan Peringkat Talent Teratas** 🏆\nBerdasarkan jumlah 🍓 yang diterima\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, talent in enumerate(top_list):
        talent_name = talent['name']
        talent_id = talent['_id']
        talent_link = f"[{talent_name}](tg://user?id={talent_id})"
        
        emoji = medals[i] if i < 3 else f"**{i+1}.**"
        
        text += f"{emoji} {talent_link} — **{talent['strawberries']}** 🍓\n"
        
    await message.reply(text, disable_web_page_preview=True)

# -----------------------------------

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


# --- Callback Handler ---

@Bot.on_callback_query(filters.regex(r"^buy_vip_"))
async def handle_buy_vip_callback(client: Bot, query):
    user = query.from_user
    user_id = user.id
    try:
        talent_id = int(query.data.split("_")[2])
    except (ValueError, IndexError):
        return await query.answer("Error: Tombol tidak valid.", show_alert=True)
    talent = get_talent(talent_id)
    if not talent or not talent.get('vip_chat_id'):
        return await query.answer("Channel VIP talent ini tidak lagi tersedia.", show_alert=True)
    vip_chat_id = talent['vip_chat_id']
    talent_name = talent['name']
    try:
        member = await client.get_chat_member(vip_chat_id, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await query.answer(f"Anda sudah menjadi anggota di channel VIP {talent_name}.", show_alert=True)
    except UserNotParticipant:
        pass 
    except Exception as e:
        return await query.answer(f"Error saat cek keanggotaan: {e}", show_alert=True)
    has_purchased_before = check_vip_purchase(user_id, talent_id)
    if not has_purchased_before:
        is_admin = user_id in ADMINS
        if not is_admin:
            balance = get_coin_balance(user_id)
            if balance < VIP_COST:
                return await query.answer(f"Koin tidak cukup! Anda punya {balance} 🪙, butuh {VIP_COST} 🪙.", show_alert=True)
            update_coin_balance(user_id, balance - VIP_COST)
        add_vip_purchase(user_id, talent_id) 
        await query.answer("Pembelian sukses! Link undangan (sekali pakai) dikirim ke PM Anda.", show_alert=True)
    else:
        await query.answer("Anda sudah pernah membeli akses ini. Link undangan baru (sekali pakai) dikirim ke PM Anda.", show_alert=False)
    try:
        link = await client.create_chat_invite_link(
            chat_id=vip_chat_id,
            member_limit=1 
        )
        invite_link = link.invite_link
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
    if not has_purchased_before:
        try:
            sender_link = f"[{user.first_name}](tg://user?id={user_id})"
            await client.send_message(
                talent_id,
                f"🎉 Kabar baik! {sender_link} baru saja membeli akses VIP Anda seharga {VIP_COST} 🪙!"
            )
        except Exception:
            pass 
        try:
            buyer_link = f"[{user.first_name}](tg://user?id={user_id})"
            talent_link = f"[{talent['name']}](tg://user?id={talent_id})"
            notif_text = (
                f"🔔 **Notifikasi Pembelian VIP** 🔔\n\n"
                f"👤 **Pembeli:** {buyer_link} (`{user_id}`)\n"
                f"⭐️ **Talent:** {talent_link} (`{talent_id}`)\n"
                f"💰 **Harga:** {VIP_COST} 🪙"
            )
            for admin_id in ADMINS:
                try:
                    await client.send_message(admin_id, notif_text, disable_web_page_preview=True)
                except Exception:
                    pass 
        except Exception:
            pass
