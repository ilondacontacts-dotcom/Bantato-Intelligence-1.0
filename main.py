from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
import os, re, difflib, ast

BASE_DIR = "/storage/emulated/0/Documents/BantatoIntelligence-1.0"
DATA_FILE = os.path.join(BASE_DIR, "data.txt")
BANNED_FILE = os.path.join(BASE_DIR, "BannedWords.txt")
USERS_FILE = os.path.join(BASE_DIR, "users.txt")

if not os.path.isdir(BASE_DIR):
    os.makedirs(BASE_DIR, exist_ok=True)

for path in (DATA_FILE, BANNED_FILE, USERS_FILE):
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()

def load_ai_data():
    ai = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or "|" not in line:
                    continue
                k, v = line.split("|", 1)
                k = k.strip().lower()
                v = v.strip()
                if k:
                    ai[k] = v
    except:
        pass
    return ai

AI_DATA = load_ai_data()
AI_KEYS = list(AI_DATA.keys())

def load_banned():
    banned = []
    try:
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    banned.append(w)
    except:
        pass
    return banned

BANNED_LIST = load_banned()

def load_users():
    users = {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if "|" not in line:
                    continue
                uname, pwd = line.split("|", 1)
                users[uname] = pwd
    except:
        pass
    return users

USERS = load_users()

def save_user(username, password):
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username}|{password}\n")
    USERS[username] = password

def normalize(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s\^\+\-\*\/\%\(\)\.]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def find_response(user_text):
    norm = normalize(user_text)
    if norm in AI_DATA:
        return AI_DATA[norm]
    for key in sorted(AI_KEYS, key=len, reverse=True):
        if key in norm:
            return AI_DATA[key]
    match = difflib.get_close_matches(norm, AI_KEYS, n=1, cutoff=0.65)
    if match:
        return AI_DATA[match[0]]
    return None

def contains_banned(text):
    t = text.lower()
    for w in BANNED_LIST:
        if not w:
            continue
        if " " in w:
            if w in t:
                return True
        else:
            if re.search(r"\b" + re.escape(w) + r"\b", t):
                return True
    return False

def looks_like_math(s):
    return bool(re.fullmatch(r"[0-9\.\s\+\-\*\/\%\^\(\)]+", s))

def safe_eval(expr):
    expr = expr.replace("^", "**")
    try:
        node = ast.parse(expr, mode='eval')
    except:
        return None
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Call, ast.Name, ast.Attribute, ast.Import, ast.ImportFrom)):
            return None
    try:
        compiled = compile(node, "<string>", "eval")
        result = eval(compiled, {"__builtins__": {}}, {})
        return result
    except:
        return None

class ChatBubble(Label):
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.is_user = is_user
        self.size_hint_y = None
        self.halign = 'right' if is_user else 'left'
        self.valign = 'middle'
        self.padding = (dp(12), dp(8))
        self.markup = True
        self.color = (1,1,1,1) if is_user else (0,0,0,1)
        self.font_size = '16sp'
        self.bind(texture_size=self.update_height)
        with self.canvas.before:
            if self.is_user:
                Color(0.07, 0.5, 1, 1)
            else:
                Color(0.94, 0.94, 0.94, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[16])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_height(self, *args):
        max_w = Window.width * 0.78
        self.text_size = (max_w, None)
        self.texture_update()
        self.height = self.texture_size[1] + dp(24)

    def update_rect(self, *args):
        try:
            self.rect.pos = self.pos
            self.rect.size = self.size
        except:
            pass

class AIInterface(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll = ScrollView(size_hint=(1, 0.88), pos_hint={"x":0, "y":0.12})
        self.chat_box = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(10), spacing=dp(10))
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        self.scroll.add_widget(self.chat_box)
        self.add_widget(self.scroll)
        input_area = BoxLayout(size_hint=(1, 0.12), pos_hint={"x":0, "y":0})
        self.input = TextInput(hint_text="Type a message...", multiline=False, size_hint=(0.78, 1), padding=(dp(12), dp(12)))
        self.input.bind(on_text_validate=self.on_enter)
        send_btn = Button(text="Send", size_hint=(0.22, 1))
        send_btn.bind(on_release=self.on_send)
        input_area.add_widget(self.input)
        input_area.add_widget(send_btn)
        self.add_widget(input_area)
        auth_btn = Button(text="Login/SignUp", size_hint=(0.32, 0.06), pos_hint={"x":0.64, "y":0.92})
        auth_btn.bind(on_release=self.open_auth)
        self.add_widget(auth_btn)
        self.current_user = None
        self.add_ai("Welcome to Bantato Intelligence — say hi!")

    def add_user(self, text):
        bubble = ChatBubble(text, is_user=True, size_hint_x=None, width=Window.width * 0.78)
        wrapper = BoxLayout(size_hint_y=None, height=bubble.texture_size[1] + dp(30))
        wrapper.add_widget(BoxLayout(size_hint_x=0.18))
        wrapper.add_widget(bubble)
        self.chat_box.add_widget(wrapper)
        self.scroll.scroll_to(bubble)

    def add_ai(self, text):
        bubble = ChatBubble(text, is_user=False, size_hint_x=None, width=Window.width * 0.78)
        wrapper = BoxLayout(size_hint_y=None, height=bubble.texture_size[1] + dp(30))
        wrapper.add_widget(bubble)
        wrapper.add_widget(BoxLayout(size_hint_x=0.18))
        self.chat_box.add_widget(wrapper)
        self.scroll.scroll_to(bubble)

    def on_enter(self, instance):
        self.on_send(None)

    def on_send(self, instance):
        user_msg = self.input.text.strip()
        if not user_msg:
            return
        self.add_user(user_msg)
        self.input.text = ""
        self.handle_message(user_msg)

    def open_auth(self, instance):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        uname = TextInput(hint_text="Username", multiline=False)
        pwd = TextInput(hint_text="Password", multiline=False, password=True)
        btns = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        login_btn = Button(text="Login")
        signup_btn = Button(text="Sign Up")
        btns.add_widget(login_btn); btns.add_widget(signup_btn)
        layout.add_widget(uname); layout.add_widget(pwd); layout.add_widget(btns)
        popup = Popup(title="Login or Sign Up", content=layout, size_hint=(0.9, 0.45))

        def do_login(inst):
            username = uname.text.strip()
            password = pwd.text.strip()
            global USERS
            USERS = load_users()
            if username in USERS and USERS[username] == password:
                self.current_user = username
                popup.dismiss()
                self.add_ai(f"Logged in as {username}")
            else:
                self.add_ai("Login failed: invalid username or password.")

        def do_signup(inst):
            username = uname.text.strip()
            password = pwd.text.strip()
            if not username or not password:
                self.add_ai("Sign up failed: enter username and password.")
                return
            if "|" in username or "|" in password:
                self.add_ai("Character '|' is not allowed.")
                return
            global USERS
            USERS = load_users()
            if username in USERS:
                self.add_ai("Sign up failed: username already exists.")
                return
            try:
                save_user(username, password)
            except:
                return
            self.current_user = username
            popup.dismiss()
            self.add_ai(f"Account created and logged in as {username}")

        login_btn.bind(on_release=do_login)
        signup_btn.bind(on_release=do_signup)
        popup.open()

    def handle_message(self, msg):
        if contains_banned(msg):
            self.add_ai("I can't respond to that.")
            return
        stripped = msg.replace(" ", "")
        if looks_like_math(stripped):
            val = safe_eval(msg)
            if val is not None:
                if isinstance(val, float) and val.is_integer():
                    val = int(val)
                self.add_ai(str(val))
                return
        resp = find_response(msg)
        if resp:
            self.add_ai(resp)
            return
        self.add_ai("I don't have a matching answer. Please rephrase or ask something else.")

class BantatoApp(App):
    def build(self):
        return AIInterface()

if __name__ == "__main__":
    BantatoApp().run()
