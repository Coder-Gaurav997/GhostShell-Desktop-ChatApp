import sys
import os

def resource_path(relative_path):
    """Resolves asset paths correctly whether running as a normal script
    or as a PyInstaller-built exe (onefile or onedir)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path).replace("\\", "/")

MONO_FONT = resource_path(r"assets/mono.ttf")
ICON_PATH = resource_path(r"assets/icon.png")

from kivy.core.window import Window

# Mobile-proportioned desktop window: width:height = 0.45:1
Window.size = (360, 550)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.lang import Builder

import crypto
import db

import hashlib
from kivy.utils import escape_markup

# Tweak these two to reposition the trash icon within its slot.
# Negative Y moves it down, positive Y moves it up; same idea for X (left/right).
TRASH_ICON_OFFSET_X = -1
TRASH_ICON_OFFSET_Y = -1

USERNAME_COLORS = [
    "FF6B6B", "4ECDC4", "FFD93D", "1A8FE3",
    "FF922B", "C77DFF", "F72585", "06D6A0",
]


def get_color_for_username(username):
    """Deterministic color per username — same name always gets the same
    color, on every device, with no lookup table to keep in sync."""
    digest = hashlib.md5(username.encode()).hexdigest()
    return USERNAME_COLORS[int(digest, 16) % len(USERNAME_COLORS)]


Window.clearcolor = (0, 0, 0, 1)

KV = f"""
<TerminalLabel@Label>:
    markup: True
    color: 1, 1, 1, 1
    font_name: "{MONO_FONT}"
    text_size: self.width, None
    size_hint_y: None
    height: self.texture_size[1]
    halign: "left"
    valign: "top"

<TerminalInput@TextInput>:
    background_color: 0.08, 0.08, 0.08, 1
    foreground_color: 1, 1, 1, 1
    cursor_color: 1, 1, 1, 1
    hint_text: "Type Here..."
    hint_text_color: 0.5, 0.5, 0.5, 1
    font_name: "{MONO_FONT}"
    multiline: False
    padding: [10, 10]

<TerminalButton@Button>:
    background_color: 0, 0, 0, 1
    background_normal: ""
    color: 0.2, 1, 0.2, 1
    font_name: "{MONO_FONT}"

<Separator@Widget>:
    size_hint_y: None
    height: dp(2)
    canvas:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<PassphraseScreen>:
    name: "passphrase"
    BoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 10
        TerminalLabel:
            text: "> Enter Group Passphrase:"
        TerminalInput:
            id: passphrase_input
            password: True
            on_text_validate: root.check_passphrase(self.text)
        TerminalLabel:
            id: error_label
        TerminalButton:
            text: "[ Submit ]"
            size_hint_y: None
            height: 50
            on_release: root.check_passphrase(passphrase_input.text)

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 10
        TerminalLabel:
            text: "> Enter Your Username:"
        TerminalInput:
            id: username_input
            on_text_validate: root.try_login(self.text)
        TerminalLabel:
            id: error_label
        BoxLayout:
            size_hint_y: None
            height: 50
            spacing: 10
            TerminalButton:
                text: "[ Login ]"
                on_release: root.try_login(username_input.text)
            TerminalButton:
                text: "[ Sign Up ]"
                on_release: root.try_signup(username_input.text)

<LoadingScreen>:
    name: "loading"
    BoxLayout:
        orientation: "vertical"
        TerminalLabel:
            text: "Loading Messages..."

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: "vertical"
        padding: 10
        spacing: 5
        BoxLayout:
            id: header_row
            size_hint_y: None
            height: 40
            spacing: 8
            Label:
                id: header_label
                markup: True
                text: "[color=33FF33]GhostShell[/color]"
                color: 1, 1, 1, 1
                font_name: "{MONO_FONT}"
                font_size: "18sp"
                halign: "left"
                valign: "middle"
                text_size: self.size
            Widget:
                id: trash_slot
                size_hint_x: None
                width: 32
        Separator:
        ScrollView:
            id: scroll
            effect_cls: "ScrollEffect"
            do_scroll_x: False
            BoxLayout:
                id: log_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 4
        Separator:
        BoxLayout:
            size_hint_y: None
            height: 45
            spacing: 5
            TerminalInput:
                id: message_input
                on_text_validate: root.send_message(self.text)
            TerminalButton:
                text: "[ Send ]"
                size_hint_x: None
                width: 100
                on_release: root.send_message(message_input.text)
"""

Builder.load_string(KV)


class TrashIcon(ButtonBehavior, Widget):
    """A small red dustbin drawn with plain canvas shapes — no emoji/font
    glyph needed, so it renders identically on every platform."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (20, 20)
        with self.canvas:
            Color(0.9, 0.15, 0.15, 1)
            self.lid = Rectangle()
            self.handle = Rectangle()
            self.body = Rectangle()
            self.line1 = Line(width=1.2)
            self.line2 = Line(width=1.2)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        x, y = self.pos
        w, h = self.size

        self.lid.pos = (x + w * 0.1, y + h * 0.78)
        self.lid.size = (w * 0.8, h * 0.1)

        self.handle.pos = (x + w * 0.35, y + h * 0.88)
        self.handle.size = (w * 0.3, h * 0.08)

        self.body.pos = (x + w * 0.18, y + h * 0.08)
        self.body.size = (w * 0.64, h * 0.68)

        self.line1.points = [x + w * 0.38, y + h * 0.15, x + w * 0.38, y + h * 0.68]
        self.line2.points = [x + w * 0.62, y + h * 0.15, x + w * 0.62, y + h * 0.68]


class PassphraseScreen(Screen):
    def check_passphrase(self, passphrase):
        if not passphrase:
            return
        if crypto.verify_passphrase(passphrase):
            App.get_running_app().session_key = crypto.derive_key(passphrase)
            self.manager.current = "login"
        else:
            self.ids.error_label.text = "Wrong Passphrase! Try Again..."


class LoginScreen(Screen):
    def try_login(self, username):
        if not db.is_valid_username(username):
            self.ids.error_label.text = "invalid username format"
            return
        if db.username_exists(username):
            App.get_running_app().username = username
            self.manager.current = "loading"
            Clock.schedule_once(lambda dt: App.get_running_app().enter_chat(), 0.1)
        else:
            self.ids.error_label.text = "This Username Doesn't Exist!!"

    def try_signup(self, username):
        if not db.is_valid_username(username):
            self.ids.error_label.text = "invalid username format"
            return
        if db.username_exists(username):
            self.ids.error_label.text = "This Username Is Occupied!!"
            return
        if db.create_username(username):
            App.get_running_app().username = username
            self.manager.current = "loading"
            Clock.schedule_once(lambda dt: App.get_running_app().enter_chat(), 0.1)
        else:
            self.ids.error_label.text = "signup failed, try again"


class LoadingScreen(Screen):
    pass


class ChatScreen(Screen):
    def on_kv_post(self, base_widget):
        icon = TrashIcon()
        icon.bind(on_release=lambda *_: self.confirm_delete_all())
        slot = self.ids.trash_slot
        slot.add_widget(icon)

        def reposition(*args):
            icon.center_x = slot.center_x + TRASH_ICON_OFFSET_X
            icon.center_y = slot.center_y + TRASH_ICON_OFFSET_Y

        slot.bind(pos=reposition, size=reposition)
        reposition()

    def set_header(self, username):
        self.ids.header_label.text = f"[color=33FF33]GhostShell[/color]  [ {username} ]"

    def append_line(self, username, text, animate=True):
        color = get_color_for_username(username)
        prefix = f"[color={color}]{username}[/color]:  "

        msg_label = Label(
            markup=True,
            font_name=MONO_FONT,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        msg_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        msg_label.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1]))
        self.ids.log_box.add_widget(msg_label)

        if animate:
            msg_label.text = prefix
            self._type_message(msg_label, prefix, text)
        else:
            msg_label.text = prefix + escape_markup(text)

        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0)

    def _type_message(self, label, prefix, raw_text, index=0, speed=0.02):
        if index <= len(raw_text):
            label.text = prefix + escape_markup(raw_text[:index])
            self._scroll_to_bottom()
            Clock.schedule_once(
                lambda dt: self._type_message(label, prefix, raw_text, index + 1, speed),
                speed,
            )

    def _scroll_to_bottom(self):
        self.ids.scroll.scroll_y = 0

    def send_message(self, text):
        text = text.strip()
        if not text:
            return
        app = App.get_running_app()
        nonce_hex, ciphertext_hex = crypto.encrypt_message(app.session_key, text)

        self.append_line(app.username, text)
        self.ids.message_input.text = ""

        try:
            db.send_message(app.username, nonce_hex, ciphertext_hex)
        except Exception:
            self.append_line("system", "Failed To Send - Check Your Connection")

    def confirm_delete_all(self):
        content = BoxLayout(orientation="vertical", padding=15, spacing=12)
        content.add_widget(Label(
            text="Delete ALL messages for everyone?\nThis cannot be undone.",
            color=(1, 1, 1, 1),
            font_name=MONO_FONT,
            halign="center",
        ))
        btn_row = BoxLayout(size_hint_y=None, height=45, spacing=10)
        yes_btn = Button(
            text="[ Yes, Delete ]", background_color=(0, 0, 0, 1),
            background_normal="", color=(1, 0.2, 0.2, 1), font_name=MONO_FONT,
        )
        no_btn = Button(
            text="[ Cancel ]", background_color=(0, 0, 0, 1),
            background_normal="", color=(0.2, 1, 0.2, 1), font_name=MONO_FONT,
        )
        btn_row.add_widget(yes_btn)
        btn_row.add_widget(no_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title="", separator_height=0, content=content,
            size_hint=(0.8, 0.3), background_color=(0, 0, 0, 0.95),
        )
        yes_btn.bind(on_release=lambda *_: self._do_delete_all(popup))
        no_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def _do_delete_all(self, popup):
        popup.dismiss()
        try:
            db.delete_all_messages()
        except Exception as e:
            print("Delete failed:", e)
            return
        self.ids.log_box.clear_widgets()
        App.get_running_app().last_seen_id = 0


class ChatApp(App):
    title = "GhostShell"
    icon = ICON_PATH

    session_key = None
    username = None

    def build(self):
        sm = ScreenManager()
        sm.add_widget(PassphraseScreen())
        sm.add_widget(LoginScreen())
        sm.add_widget(LoadingScreen())
        sm.add_widget(ChatScreen())
        return sm

    def enter_chat(self):
        chat_screen = self.root.get_screen("chat")
        chat_screen.set_header(self.username)

        rows = db.fetch_all_messages()
        self.last_seen_id = 0
        for row in rows:
            self._render_row(chat_screen, row, animate=False)
            self.last_seen_id = row["id"]

        Clock.schedule_interval(self._poll_new_messages, 1.5)
        self.root.current = "chat"

    def _poll_new_messages(self, dt):
        chat_screen = self.root.get_screen("chat")
        try:
            new_rows = db.fetch_messages_after(self.last_seen_id)
        except Exception:
            return
        for row in new_rows:
            self.last_seen_id = row["id"]
            if row["username"] == self.username:
                continue
            self._render_row(chat_screen, row)

    def _render_row(self, chat_screen, row, animate=True):
        try:
            text = crypto.decrypt_message(self.session_key, row["nonce"], row["ciphertext"])
        except Exception:
            text = "[unreadable message]"
        chat_screen.append_line(row["username"], text, animate=animate)


if __name__ == "__main__":
    ChatApp().run()