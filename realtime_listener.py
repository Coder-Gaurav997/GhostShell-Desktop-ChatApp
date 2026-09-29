import asyncio
import threading
from kivy.clock import Clock
from supabase import acreate_client
from config import SUPABASE_URL, SUPABASE_KEY


class RealtimeListener:
    """Runs the Supabase realtime subscription on a background thread with
    its own event loop, and hands new rows back to the Kivy main thread."""

    def __init__(self, on_new_message):
        self.on_new_message = on_new_message

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._subscribe())
        loop.run_forever()

    async def _subscribe(self):
        client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
        channel = client.channel("messages-realtime")
        channel.on_postgres_changes(
            "INSERT", schema="public", table="messages",
            callback=self._handle_event,
        )
        await channel.subscribe()

    def _handle_event(self, payload):
        # Confirm this matches your installed version — print(payload) if in doubt.
        record = payload.data.get("record")
        if record:
            Clock.schedule_once(lambda dt: self.on_new_message(record))