from pymongo import MongoClient
from fsub.config import DATABASE_URL, DATABASE_NAME

dbclient = MongoClient(DATABASE_URL)
database = dbclient[DATABASE_NAME]

# Koleksi yang sudah ada
user_data = database['users']
talent_data = database['talents']
coin_data = database['user_coins']

# --- KOLEKSI BARU UNTUK VIP ---
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
        # <--- PERUBAHAN: Menambahkan field 'vip_link' ---
        talent_data.insert_one({
            '_id': user_id, 
            'name': name, 
            'strawberries': 0, 
            'vip_link': None  # Link VIP default-nya kosong
        })
        return True
    return False 

def del_talent(user_id: int):
    """Menghapus talent dari database."""
    result = talent_data.delete_one({'_id': user_id})
    # Juga hapus data pembelian VIP terkait (opsional tapi bersih)
    vip_purchases.delete_many({'talent_id': user_id})
    return result.deleted_count > 0

def get_talent(user_id: int):
    """Mengambil data satu talent."""
    return talent_data.find_one({'_id': user_id})

def get_all_talents():
    """Mengambil daftar semua talent."""
    return list(talent_data.find().sort("name", 1)) 

def give_strawberry(user_id: int):
    """Menambahkan 1 🍓 ke talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$inc': {'strawberries': 1}}
    )
    return

# --- Fungsi VIP (BARU) ---

def set_vip_link(user_id: int, link: str):
    """Mengatur atau memperbarui link VIP talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$set': {'vip_link': link}}
    )

def del_vip_link(user_id: int):
    """Menghapus link VIP talent."""
    talent_data.update_one(
        {'_id': user_id},
        {'$set': {'vip_link': None}}
    )

def add_vip_purchase(user_id: int, talent_id: int):
    """Mencatat bahwa user telah membeli akses VIP talent."""
    vip_purchases.update_one(
        {'user_id': user_id, 'talent_id': talent_id},
        {'$set': {'user_id': user_id, 'talent_id': talent_id}},
        upsert=True # Buat baru jika belum ada
    )

def check_vip_purchase(user_id: int, talent_id: int):
    """Memeriksa apakah user sudah pernah membeli VIP talent."""
    found = vip_purchases.find_one({'user_id': user_id, 'talent_id': talent_id})
    return bool(found)


# --- Fungsi Koin (Sudah Ada) ---

def get_coin_balance(user_id: int):
    """Mendapatkan saldo koin pengguna."""
    user = coin_data.find_one({'_id': user_id})
    if user:
        return user.get('coins', 0)
    return 0

def update_coin_balance(user_id: int, new_balance: int):
    """Mengatur saldo koin pengguna ke jumlah tertentu."""
    coin_data.update_one(
        {'_id': user_id},
        {'$set': {'coins': new_balance}},
        upsert=True 
    )
    return

def add_coins(user_id: int, amount: int):
    """Menambahkan (atau mengurangi) koin dari saldo pengguna."""
    coin_data.update_one(
        {'_id': user_id},
        {'$inc': {'coins': amount}},
        upsert=True 
    )
    return
