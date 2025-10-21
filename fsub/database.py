from pymongo import MongoClient, DESCENDING
from fsub.config import DATABASE_URL, DATABASE_NAME

dbclient = MongoClient(DATABASE_URL)
database = dbclient[DATABASE_NAME]

# Koleksi yang sudah ada
user_data = database['users']
talent_data = database['talents']
coin_data = database['user_coins']
vip_purchases = database['vip_purchases']


# --- Fungsi User (Sudah Ada) ---

def check_user(user_id : int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)

def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})
    return

def full_user():
    user_docs = user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
    return user_ids

def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})
    return

# --- Fungsi Talent (Diperbarui) ---

def add_talent(user_id: int, name: str):
    """Menambahkan talent baru ke database."""
    if not talent_data.find_one({'_id': user_id}):
        # <--- PERUBAHAN: Menambahkan field 'bio' ---
        talent_data.insert_one({
            '_id': user_id, 
            'name': name, 
            'strawberries': 0, 
            'vip_chat_id': None,  
            'vip_chat_title': None,
            'bio': None # Bio default-nya kosong
        })
        return True
    return False 

def del_talent(user_id: int):
    """Menghapus talent dari database."""
    result = talent_data.delete_one({'_id': user_id})
    vip_purchases.delete_many({'talent_id': user_id})
    return result.deleted_count > 0

def get_talent(user_id: int):
    """Mengambil data satu talent."""
    return talent_data.find_one({'_id': user_id})

def get_all_talents():
    """Mengambil daftar semua talent (diurutkan berdasarkan nama)."""
    return list(talent_data.find().sort("name", 1)) 

def give_strawberry(user_id: int):
    """Menambahkan 1 🍓 ke talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$inc': {'strawberries': 1}}
    )
    return

# --- Fungsi Bio & Papan Peringkat (BARU) ---

def set_talent_bio(user_id: int, bio: str):
    """Mengatur atau memperbarui bio talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$set': {'bio': bio}}
    )

def get_top_talents(limit: int = 10):
    """Mengambil daftar talent teratas berdasarkan 🍓."""
    # Mengurutkan berdasarkan 'strawberries' secara descending (-1)
    return list(talent_data.find().sort("strawberries", DESCENDING).limit(limit))


# --- Fungsi VIP (Diperbarui) ---

def set_vip_channel(user_id: int, chat_id: int, chat_title: str):
    """Mengatur atau memperbarui channel VIP talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$set': {'vip_chat_id': chat_id, 'vip_chat_title': chat_title}}
    )

def del_vip_channel(user_id: int):
    """Menghapus channel VIP talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$set': {'vip_chat_id': None, 'vip_chat_title': None}}
    )

def add_vip_purchase(user_id: int, talent_id: int):
    """Mencatat bahwa user telah membeli akses VIP talent."""
    vip_purchases.update_one(
        {'user_id': user_id, 'talent_id': talent_id},
        {'$set': {'user_id': user_id, 'talent_id': talent_id}},
        upsert=True 
    )

def check_vip_purchase(user_id: int, talent_id: int):
    """Memeriksa apakah user sudah pernah membeli VIP talent."""
    found = vip_purchases.find_one({'user_id': user_id, 'talent_id': talent_id})
    return bool(found)

def revoke_vip_purchase(user_id: int, talent_id: int):
    """Menghapus catatan pembelian VIP."""
    result = vip_purchases.delete_one({'user_id': user_id, 'talent_id': talent_id})
    return result.deleted_count > 0


# --- Fungsi Koin (Sudah Ada) ---

def get_coin_balance(user_id: int):
    user = coin_data.find_one({'_id': user_id})
    if user:
        return user.get('coins', 0)
    return 0

def update_coin_balance(user_id: int, new_balance: int):
    coin_data.update_one(
        {'_id': user_id},
        {'$set': {'coins': new_balance}},
        upsert=True 
    )
    return

def add_coins(user_id: int, amount: int):
    coin_data.update_one(
        {'_id': user_id},
        {'$inc': {'coins': amount}},
        upsert=True 
    )
    return
