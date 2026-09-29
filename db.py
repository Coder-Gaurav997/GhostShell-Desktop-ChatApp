# db.py
import re
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{5,}$")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_valid_username(username):
    return bool(USERNAME_PATTERN.match(username))


def username_exists(username):
    result = supabase.table("users").select("username").eq("username", username).execute()
    return len(result.data) > 0


def create_username(username):
    try:
        supabase.table("users").insert({"username": username}).execute()
        return True
    except Exception:
        return False


def fetch_all_messages():
    result = supabase.table("messages").select("*").order("id").execute()
    return result.data


def fetch_messages_after(last_id):
    result = supabase.table("messages").select("*").gt("id", last_id).order("id").execute()
    return result.data


def send_message(username, nonce_hex, ciphertext_hex):
    supabase.table("messages").insert({
        "username": username,
        "nonce": nonce_hex,
        "ciphertext": ciphertext_hex,
    }).execute()


def delete_all_messages():
    supabase.rpc("delete_all_messages").execute()