import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
import uuid
import customtkinter as ctk
import requests
from fpdf import FPDF
from tkinter import filedialog, messagebox

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2"
HISTORY_FILE = Path.home() / ".assistente_history.json"
OLD_HISTORY_FILE = Path("history.json")
MAX_SAVED_SESSIONS = None
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "1").lower() in {"1", "true", "yes"}
WEB_SEARCH_API_URL = os.getenv("WEB_SEARCH_API_URL", "https://html.duckduckgo.com/html/")
MODEL_EXTENSIONS = [".bin", ".gguf"]

STRINGS = {
    "pt": {
        "app_title": "Assistente Pessoal",
        "subtitle": "Conversa local com Llama 3 usando modelo local",
        "footer": "Dica: Enter envia a mensagem.",
        "start_title": "Escolha seu idioma",
        "start_subtitle": "Bem-vindo ao seu assistente pessoal. Insira seu nome, por gentileza.",
        "language_pt": "PT-BR",
        "language_en": "EN",
        "name_placeholder": "Digite seu nome",
        "continue": "Continuar",
        "question_title": "O que deseja fazer hoje?",
        "study": "Estudar",
        "code": "Programar",
        "chat": "Conversar",
        "new_chat": "Nova conversa",
        "history_tab": "Histórico",
        "chat_tab": "Chat",
        "history_title": "Conversas recentes",
        "history_empty": "Ainda não há conversas salvas.",
        "open": "Abrir",
        "clear": "Limpar",
        "delete": "Excluir",
        "delete_confirm": "Deseja realmente excluir este histórico?",
        "settings_title": "Configurações",
        "language_label": "Idioma",
        "theme_label": "Tema",
        "theme_dark": "Escuro",
        "theme_light": "Claro",
        "web_search_label": "Busca na internet",
        "on": "Ligada",
        "off": "Desligada",
        "save": "Salvar",
        "save_pdf": "Salvar em PDF",
        "send": "Enviar",
        "thinking": "Pensando...",
        "ollama_missing": "Ollama não parece estar aberto. Abra o Ollama e certifique-se de ter baixado um modelo Llama 3.",
        "conversation_cleared": "Conversa limpa.",
        "ready": "Pronto. Escreva uma mensagem para começar.",
        "session_label": "Sessão atual",
        "name_label": "Nome",
        "mode_label": "Modo",
        "mode_study": "Estudo",
        "mode_code": "Programação",
        "mode_chat": "Conversa",
        "load_error": "Não foi possível carregar o histórico.",
        "choose_language_name_mode": "Escolha um idioma, digite seu nome e selecione um modo antes de conversar.",
        "history_saved": "Histórico salvo com sucesso.",
        "pdf_install_fpdf": "Para salvar como PDF, instale a biblioteca fpdf:\npip install fpdf",
        "pdf_saved": "PDF salvo em:\n{path}",
        "pdf_error": "Não foi possível salvar o PDF: {error}",
        "model_error": "Erro ao conversar com o modelo: {error}\n\nVerifique se o Ollama está aberto e se o modelo existe.",
        "local_model_missing_cpp": "O modelo local existe, mas o pacote llama-cpp-python não está instalado.",
        "local_model_failed": "Falha ao carregar o modelo local. Verifique se llama3.2.bin está correto.",
        "save_history_error": "Não foi possível salvar o histórico: {error}",
    },
    "en": {
        "app_title": "Personal Assistant",
        "subtitle": "Local chat with Llama 3 using a local model",
        "footer": "Tip: Press Enter to send a message.",
        "start_title": "Choose your language",
        "start_subtitle": "Welcome to your personal assistant. Please enter your name.",
        "language_pt": "PT-BR",
        "language_en": "EN",
        "name_placeholder": "Enter your name",
        "continue": "Continue",
        "question_title": "What do you want to do today?",
        "study": "Study",
        "code": "Coding",
        "chat": "Chat",
        "new_chat": "New chat",
        "history_tab": "History",
        "chat_tab": "Chat",
        "history_title": "Recent conversations",
        "history_empty": "No saved conversations yet.",
        "open": "Open",
        "clear": "Clear",
        "delete": "Delete",
        "delete_confirm": "Do you really want to delete this history?",
        "settings_title": "Settings",
        "language_label": "Language",
        "theme_label": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "web_search_label": "Web search",
        "on": "On",
        "off": "Off",
        "save": "Save",
        "send": "Send",
        "thinking": "Thinking...",
        "ollama_missing": "Ollama does not seem to be running. Open Ollama and make sure a Llama 3 model is installed.",
        "conversation_cleared": "Conversation cleared.",
        "ready": "Ready. Write a message to begin.",
        "session_label": "Current session",
        "name_label": "Name",
        "mode_label": "Mode",
        "mode_study": "Study",
        "mode_code": "Coding",
        "mode_chat": "Chat",
        "load_error": "Could not load history.",
        "choose_language_name_mode": "Choose a language, enter your name, and select a mode before chatting.",
        "history_saved": "History saved successfully.",
        "pdf_install_fpdf": "To save as PDF, install the fpdf library:\npip install fpdf",
        "pdf_saved": "PDF saved to:\n{path}",
        "pdf_error": "Could not save the PDF: {error}",
        "model_error": "Error talking to the model: {error}\n\nCheck that Ollama is running and that the model is available.",
        "local_model_missing_cpp": "The local model exists, but llama-cpp-python is not installed.",
        "local_model_failed": "Failed to load the local model. Check that llama3.2.bin is valid.",
        "save_history_error": "Could not save history: {error}",
    },
}

MODE_PROFILES = {
    "pt": {
        "study": {
            "title": "Estudo",
            "temperature": 0.2,
            "prompt": (
                "Você é um tutor paciente, claro e didático em português do Brasil. "
                "Explique passo a passo, com exemplos simples, e faça perguntas curtas quando isso ajudar o aluno. "
                "Priorize precisão, organização e linguagem amigável."
            ),
        },
        "code": {
            "title": "Programação",
            "temperature": 0.1,
            "prompt": (
                "Você é um assistente especialista em programação em português do Brasil. "
                "Explique conceitos com clareza, revise código, sugira melhorias e mostre exemplos práticos. "
                "Quando fizer sentido, use blocos de código e seja objetivo."
            ),
        },
        "chat": {
            "title": "Conversa",
            "temperature": 0.7,
            "prompt": (
                "Você é um assistente pessoal simpático, natural e conversacional em português do Brasil. "
                "Responda com empatia, clareza e ritmo leve, como uma conversa útil do dia a dia."
            ),
        },
    },
    "en": {
        "study": {
            "title": "Study",
            "temperature": 0.2,
            "prompt": (
                "You are a patient, clear, and helpful tutor in English. "
                "Explain step by step with simple examples and ask short guiding questions when useful. "
                "Prioritize accuracy, structure, and friendly language."
            ),
        },
        "code": {
            "title": "Coding",
            "temperature": 0.1,
            "prompt": (
                "You are an expert coding assistant in English. "
                "Explain concepts clearly, review code, suggest improvements, and provide practical examples. "
                "Use code blocks when appropriate and stay concise."
            ),
        },
        "chat": {
            "title": "Chat",
            "temperature": 0.7,
            "prompt": (
                "You are a friendly, natural, and conversational personal assistant in English. "
                "Reply with empathy, clarity, and a light everyday tone."
            ),
        },
    },
}

LANGUAGE_FLAGS = {
    "pt": "🇧🇷 🇵🇹",
    "en": "🇺🇸",
}


class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.language = None
        self.user_name = ""
        self.mode = None
        self.session_id = None
        self.current_session = None
        self.theme = "dark"
        self.web_search_enabled = ENABLE_WEB_SEARCH
        self.default_mode = "chat"
        self.history_sessions = self.load_sessions()
        self.llama_class = Llama
        self.llama_model = None
        self.local_model_path = self.find_local_model_file()

        self.title(STRINGS["pt"]["app_title"])
        self.geometry("900x600")

        self.show_start_screen()

    def show_start_screen(self):
        self.clear_window()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        title_label = ctk.CTkLabel(
            frame,
            text=STRINGS["pt"]["start_title"],
            font=("Arial", 24, "bold"),
        )
        title_label.pack(pady=20)

        subtitle_label = ctk.CTkLabel(
            frame, text=STRINGS["pt"]["start_subtitle"], font=("Arial", 12)
        )
        subtitle_label.pack(pady=10)

        name_entry = ctk.CTkEntry(
            frame,
            placeholder_text=STRINGS["pt"]["name_placeholder"],
            width=300,
            font=("Arial", 12),
        )
        name_entry.pack(pady=10)

        lang_frame = ctk.CTkFrame(frame)
        lang_frame.pack(pady=10)

        def continue_app():
            name = name_entry.get().strip()
            if name:
                self.user_name = name
                self.language = "pt"
                self.show_mode_selection()
            else:
                messagebox.showwarning("Warning", "Please enter your name")

        continue_button = ctk.CTkButton(
            frame,
            text=STRINGS["pt"]["continue"],
            command=continue_app,
            width=300,
            font=("Arial", 12),
        )
        continue_button.pack(pady=20)

        lang_btn_pt = ctk.CTkButton(
            lang_frame,
            text=STRINGS["pt"]["language_pt"],
            width=100,
            font=("Arial", 10),
        )
        lang_btn_pt.grid(row=0, column=0, padx=5)

        lang_btn_en = ctk.CTkButton(
            lang_frame,
            text=STRINGS["pt"]["language_en"],
            width=100,
            font=("Arial", 10),
        )
        lang_btn_en.grid(row=0, column=1, padx=5)

    def show_mode_selection(self):
        self.clear_window()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        title_label = ctk.CTkLabel(
            frame,
            text=STRINGS[self.language]["question_title"],
            font=("Arial", 20, "bold"),
        )
        title_label.pack(pady=20)

        def select_mode(mode):
            self.mode = mode
            self.session_id = str(uuid.uuid4())
            self.current_session = {
                "id": self.session_id,
                "user_name": self.user_name,
                "language": self.language,
                "mode": mode,
                "messages": [],
                "created_at": datetime.now().isoformat(),
            }
            self.show_chat_screen()

        for mode in ["study", "code", "chat"]:
            btn = ctk.CTkButton(
                frame,
                text=MODE_PROFILES[self.language][mode]["title"],
                command=lambda m=mode: select_mode(m),
                width=200,
                height=50,
                font=("Arial", 14),
            )
            btn.pack(pady=10)

    def show_chat_screen(self):
        self.clear_window()

        top_frame = ctk.CTkFrame(self, height=60)
        top_frame.pack(fill="x", padx=10, pady=10)
        top_frame.pack_propagate(False)

        info_label = ctk.CTkLabel(
            top_frame,
            text=f"{self.user_name} | {MODE_PROFILES[self.language][self.mode]['title']}",
            font=("Arial", 12),
        )
        info_label.pack(side="left", padx=10)

        button_frame = ctk.CTkFrame(top_frame)
        button_frame.pack(side="right", padx=10)

        def clear_chat():
            self.current_session["messages"] = []
            self.update_display()

        clear_btn = ctk.CTkButton(
            button_frame,
            text=STRINGS[self.language]["clear"],
            command=clear_chat,
            width=80,
            font=("Arial", 10),
        )
        clear_btn.pack(side="left", padx=5)

        new_chat_btn = ctk.CTkButton(
            button_frame,
            text=STRINGS[self.language]["new_chat"],
            command=self.show_mode_selection,
            width=80,
            font=("Arial", 10),
        )
        new_chat_btn.pack(side="left", padx=5)

        self.text_display = ctk.CTkTextbox(self, wrap="word")
        self.text_display.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_display.configure(state="disabled")

        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)

        self.input_field = ctk.CTkEntry(
            input_frame, placeholder_text="Type your message...", font=("Arial", 12)
        )
        self.input_field.pack(side="left", fill="both", expand=True, padx=5)

        def send_message(event=None):
            message = self.input_field.get().strip()
            if message:
                self.input_field.delete(0, "end")
                self.current_session["messages"].append(
                    {"role": "user", "content": message}
                )
                self.update_display()
                threading.Thread(target=self.get_response, daemon=True).start()
            return "break"

        self.input_field.bind("<Return>", send_message)

        send_btn = ctk.CTkButton(
            input_frame,
            text=STRINGS[self.language]["send"],
            command=lambda: send_message(),
            width=80,
            font=("Arial", 10),
        )
        send_btn.pack(side="right", padx=5)

        self.update_display()

    def update_display(self):
        self.text_display.configure(state="normal")
        self.text_display.delete("1.0", "end")

        for msg in self.current_session["messages"]:
            role = "You" if msg["role"] == "user" else "Assistant"
            self.text_display.insert("end", f"{role}: {msg['content']}\n\n")

        self.text_display.configure(state="disabled")
        self.text_display.see("end")

    def get_response(self):
        messages = self.current_session["messages"]
        if not messages:
            return

        try:
            response = self.get_local_model_response(messages)

            if response:
                self.current_session["messages"].append(
                    {"role": "assistant", "content": response}
                )
                self.update_display()
                self.save_session()
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.current_session["messages"].append(
                {"role": "assistant", "content": error_msg}
            )
            self.update_display()

    def find_local_model_file(self):
        base_dir = (
            Path(sys._MEIPASS)
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        for ext in MODEL_EXTENSIONS:
            for model_file in base_dir.glob(f"*{ext}"):
                return model_file
        return None

    def load_local_llama_model(self):
        if self.llama_model is not None:
            return self.llama_model
        if self.llama_class is None:
            return None
        if self.local_model_path is None:
            return None
        try:
            self.llama_model = self.llama_class(
                model_path=str(self.local_model_path), n_ctx=2048
            )
            return self.llama_model
        except Exception as e:
            self.llama_model = None
            return None

    def get_local_model_response(self, messages):
        model = self.load_local_llama_model()
        if model is None:
            return "Local model not available"

        system_prompt = MODE_PROFILES[self.language][self.mode]["prompt"]
        user_message = messages[-1]["content"] if messages else ""

        try:
            result = model.create_completion(
                prompt=f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:",
                max_tokens=512,
                temperature=MODE_PROFILES[self.language][self.mode]["temperature"],
            )
            return result.get("choices", [{}])[0].get("text", "").strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def save_session(self):
        try:
            sessions = self.load_sessions()
            sessions.append(self.current_session)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def load_sessions(self):
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            pass
        return []

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()
