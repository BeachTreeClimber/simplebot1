import json
import os
import re
import random
import shutil
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
from datetime import datetime
from rapidfuzz import process, fuzz

# ==========================
# Core bot logic (same as simplebot_fixed.py)
# ==========================


def resource_path(relative_path):
    """Path to a file bundled inside the app by PyInstaller (read-only)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def user_data_dir():
    """A writable, per-user folder that persists across rebuilds/reinstalls."""
    if not getattr(sys, "frozen", False):
        # Running as a plain script: just use the folder next to the script.
        return os.path.dirname(os.path.abspath(__file__))

    if sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~")

    path = os.path.join(base, "SimpleBot")
    os.makedirs(path, exist_ok=True)
    return path


KNOWLEDGE_FILE = os.path.join(user_data_dir(), "knowledge.json")
knowledge = {}


def load_knowledge():
    global knowledge

    if not os.path.exists(KNOWLEDGE_FILE):
        # First run: seed from the knowledge file bundled with the app, if present.
        seed_path = resource_path("knowledge_seed.json")
        if os.path.exists(seed_path):
            shutil.copyfile(seed_path, KNOWLEDGE_FILE)
        else:
            with open(KNOWLEDGE_FILE, "w") as f:
                json.dump({}, f, indent=4)

    try:
        with open(KNOWLEDGE_FILE, "r") as f:
            knowledge = json.load(f)
    except Exception:
        knowledge = {}


def save_knowledge():
    with open(KNOWLEDGE_FILE, "w") as f:
        json.dump(knowledge, f, indent=4)


def clean(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text


def predict_closest_phrase(phrase_map, input_phrase):
    choices = list(phrase_map.keys())
    best_match, score, index = process.extractOne(
        input_phrase,
        choices,
        scorer=fuzz.WRatio
    )
    mapped_value = phrase_map[best_match]
    return best_match, mapped_value, score


greetings = [
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening"
]

greeting_answers = [
    "Hello!", "Hi!", "Hey!", "Nice to see you.", "Hello there!"
]

jokes = [
    "Why did the computer get cold? Because it left its Windows open.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Why was the math book sad? It had too many problems.",
    "Why did the robot go on holiday? It needed to recharge.",
    "I told my computer I needed a break. It said no problem and froze."
]

facts = [
    "Honey never spoils.",
    "Octopuses have three hearts.",
    "The Eiffel Tower grows slightly taller in summer.",
    "Bananas are berries.",
    "A day on Venus is longer than a year on Venus."
]

HELP_TEXT = """Commands:
help, time, date, joke, fact, exit

You can also ask questions like:
what is the capital of australia
who invented minecraft
what is python

You can do maths:
2+2   12*8   45/9   5-2
or
five plus six   ten times twelve"""

number_words = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20
}


def convert_word_math(text):
    text = text.lower()
    for word, value in number_words.items():
        text = text.replace(word, str(value))
    text = text.replace("plus", "+")
    text = text.replace("minus", "-")
    text = text.replace("times", "*")
    text = text.replace("multiplied by", "*")
    text = text.replace("x", "*")
    text = text.replace("divided by", "/")
    text = text.replace("over", "/")
    return text


def do_math(text):
    expression = convert_word_math(text)
    expression = expression.replace(" ", "")

    if not re.fullmatch(r"[0-9+\-*/().]+", expression):
        return None

    try:
        answer = eval(expression, {"__builtins__": None}, {})
        if isinstance(answer, float) and answer.is_integer():
            answer = int(answer)
        return str(answer)
    except Exception:
        return None


def search_knowledge(question):
    q = clean(question)

    if not knowledge:
        return None

    phrase, value, confidence = predict_closest_phrase(knowledge, q)

    if confidence > 90.0:
        return value

    return None


# ==========================
# GUI Application
# ==========================

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleBot 3.0")
        self.root.geometry("480x600")
        self.root.minsize(360, 400)

        # Colors
        self.bg = "#f4f6f8"
        self.bot_color = "#e3ecf7"
        self.user_color = "#3a7ce8"
        self.root.configure(bg=self.bg)

        load_knowledge()

        # --- Header ---
        header = tk.Frame(root, bg="#3a7ce8", height=50)
        header.pack(fill="x", side="top")
        tk.Label(
            header, text="SimpleBot 3.0", bg="#3a7ce8", fg="white",
            font=("Segoe UI", 14, "bold"), pady=12
        ).pack()

        # --- Chat history ---
        self.chat_area = scrolledtext.ScrolledText(
            root, wrap="word", state="disabled", bg="white", fg="#1a1a1a",
            font=("Segoe UI", 10), borderwidth=0, padx=10, pady=10
        )
        self.chat_area.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.chat_area.tag_configure("bot", background=self.bot_color,
                                      foreground="#1a1a1a",
                                      lmargin1=6, lmargin2=6, rmargin=60,
                                      spacing3=8, justify="left")
        self.chat_area.tag_configure("user", background=self.user_color,
                                      foreground="white",
                                      lmargin1=60, lmargin2=60, rmargin=6,
                                      spacing3=8, justify="right")

        # --- Input row ---
        input_frame = tk.Frame(root, bg=self.bg)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.entry = tk.Entry(input_frame, font=("Segoe UI", 11),
                               bg="white", fg="#1a1a1a",
                               insertbackground="#1a1a1a")
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", lambda event: self.send())
        self.entry.focus()

        send_btn = tk.Button(
            input_frame, text="Send", command=self.send,
            bg="#3a7ce8", fg="white", activebackground="#2f66c2",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16
        )
        send_btn.pack(side="right")

        self.add_message(
            "Bot", f"Hi! I'm SimpleBot. {len(knowledge)} facts loaded. "
                   f"Type 'help' to see what I can do."
        )

    def add_message(self, sender, text):
        self.chat_area.configure(state="normal")
        tag = "user" if sender == "You" else "bot"
        self.chat_area.insert("end", f"{text}\n", tag)
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")

    def send(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.add_message("You", user_text)

        if clean(user_text) in ["exit", "quit", "bye"]:
            self.add_message("Bot", random.choice([
                "Goodbye!", "See you later!", "Bye!", "Have a great day!"
            ]))
            self.root.after(800, self.root.destroy)
            return

        response = self.get_response(user_text)
        if response is not None:
            self.add_message("Bot", response)

    def get_response(self, user_text):
        text = clean(user_text)

        if text in greetings:
            return random.choice(greeting_answers)

        if text == "help":
            return HELP_TEXT

        if text == "time":
            return datetime.now().strftime("%I:%M %p")

        if text == "date":
            return datetime.now().strftime("%A %d %B %Y")

        if text == "joke":
            return random.choice(jokes)

        if text == "fact":
            return random.choice(facts)

        math_answer = do_math(user_text)
        if math_answer is not None:
            return math_answer

        result = search_knowledge(user_text)
        if result is not None:
            return result

        return self.learn(user_text)

    def learn(self, question):
        teach = messagebox.askyesno(
            "I don't know that",
            f'I don\'t know how to answer:\n"{question}"\n\nWant to teach me?'
        )
        if not teach:
            return "Okay."

        answer_text = simpledialog.askstring("Teach me", "What's the answer?")
        if not answer_text:
            return "Okay, never mind."

        knowledge[clean(question)] = answer_text
        save_knowledge()
        return "Thanks! I've learned something new."


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
