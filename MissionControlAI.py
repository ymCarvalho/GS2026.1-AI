import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random
import threading
import time
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"  

LIMITS = {
    "temperatura":   {"min": -40,  "max": 85,   "unit": "°C"},
    "energia":       {"min": 20,   "max": 100,  "unit": "%"},
    "oxigenio":      {"min": 18,   "max": 23,   "unit": "%"},
    "pressao":       {"min": 95,   "max": 105,  "unit": "kPa"},
    "comunicacao":   {"min": 60,   "max": 100,  "unit": "%"},
    "velocidade":    {"min": 0,    "max": 28000,"unit": "km/h"},
}

SYSTEM_PROMPT = """Você é ARIA (Autonomous Response Intelligence for Astronautics), 
o sistema de IA de controle de missão espacial da FIAP Space Agency.

Sua função é analisar os dados de telemetria em tempo real e fornecer:
1. Diagnóstico preciso do estado atual da missão
2. Alertas imediatos para parâmetros críticos
3. Recomendações de ações corretivas específicas
4. Previsão de tendências nas próximas 2 horas

Parâmetros operacionais normais:
- Temperatura dos módulos: -40°C a 85°C
- Nível de energia: mínimo 20% (crítico abaixo de 15%)
- Oxigênio: 18% a 23%
- Pressão: 95 kPa a 105 kPa
- Sinal de comunicação: mínimo 60%
- Velocidade orbital: até 28.000 km/h

Responda de forma técnica, direta e em português. Use emojis de status (🟢 normal, 🟡 atenção, 🔴 crítico).
Seja conciso — máximo 200 palavras por análise."""


# PALETA —
C = {
    "bg":        "#0A0E1A",
    "panel":     "#111827",
    "border":    "#1E2A3A",
    "accent":    "#00D4FF",
    "accent2":   "#7C3AED",
    "ok":        "#10B981",
    "warn":      "#F59E0B",
    "crit":      "#EF4444",
    "text":      "#E2E8F0",
    "muted":     "#64748B",
    "text_dark": "#1E293B",
    "chat_user": "#7C3AED",
    "chat_aria": "#00D4FF",
    "chat_bg":   "#0D1525",
}

FONT_MONO  = ("Courier New", 10)
FONT_TITLE = ("Courier New", 13, "bold")
FONT_LABEL = ("Courier New", 9)
FONT_VALUE = ("Courier New", 14, "bold")
FONT_SMALL = ("Courier New", 8)
FONT_CHAT  = ("Courier New", 9)

# ──────────────────────────────────────────────
# GERADOR DE DADOS SIMULADOS
# ──────────────────────────────────────────────

class MissionData:
    def __init__(self):
        self.tick = 0
        self.mission_time = 0
        self.history = {k: [] for k in LIMITS}
        self.current = {}
        self.scenario = "normal"
        self._generate()

    def _generate(self):
        prev = self.current.copy() if self.current else {}

        def drift(key, base, spread, prev_val=None):
            if prev_val is None:
                prev_val = base
            delta = random.gauss(0, spread * 0.15)
            new_val = max(LIMITS[key]["min"] * 0.9,
                          min(LIMITS[key]["max"] * 1.15,
                              prev_val + delta))
            return round(new_val, 1)

        scenario_roll = random.random()
        if self.tick % 30 == 0:
            if scenario_roll < 0.6:
                self.scenario = "normal"
            elif scenario_roll < 0.8:
                self.scenario = "warning"
            else:
                self.scenario = "critical"

        t   = prev.get("temperatura", 22)
        en  = prev.get("energia",     85)
        ox  = prev.get("oxigenio",    20.9)
        pr  = prev.get("pressao",     101.3)
        com = prev.get("comunicacao", 95)
        vel = prev.get("velocidade",  7800)

        if self.scenario == "normal":
            self.current = {
                "temperatura":  drift("temperatura",  22,  5, t),
                "energia":      drift("energia",      85,  3, en),
                "oxigenio":     drift("oxigenio",     20.9, 0.3, ox),
                "pressao":      drift("pressao",      101.3, 1, pr),
                "comunicacao":  drift("comunicacao",  95, 3, com),
                "velocidade":   drift("velocidade",   7800, 50, vel),
            }
        elif self.scenario == "warning":
            self.current = {
                "temperatura":  random.uniform(80, 90),
                "energia":      random.uniform(22, 30),
                "oxigenio":     random.uniform(17, 18.5),
                "pressao":      random.uniform(106, 110),
                "comunicacao":  random.uniform(55, 68),
                "velocidade":   drift("velocidade", 7800, 50, vel),
            }
            self.current = {k: round(v, 1) for k, v in self.current.items()}
        else:
            self.current = {
                "temperatura":  random.uniform(88, 110),
                "energia":      random.uniform(8, 20),
                "oxigenio":     random.uniform(15, 17.5),
                "pressao":      random.uniform(112, 120),
                "comunicacao":  random.uniform(20, 55),
                "velocidade":   drift("velocidade", 7800, 50, vel),
            }
            self.current = {k: round(v, 1) for k, v in self.current.items()}

        self.mission_time += 1
        self.tick += 1

        for k in LIMITS:
            self.history[k].append(self.current[k])
            if len(self.history[k]) > 60:
                self.history[k].pop(0)

    def status(self, key):
        v = self.current[key]
        lo, hi = LIMITS[key]["min"], LIMITS[key]["max"]
        margin = (hi - lo) * 0.10
        if v < lo - margin or v > hi + margin:
            return "crit"
        if v < lo + margin or v > hi - margin:
            return "warn"
        return "ok"

    def build_telemetry_string(self):
        lines = []
        for k, v in self.current.items():
            s = self.status(k)
            tag = {"ok": "NOMINAL", "warn": "ATENÇÃO", "crit": "CRÍTICO"}[s]
            lines.append(f"{k.capitalize():15s}: {v:>8} {LIMITS[k]['unit']:5s} [{tag}]")
        return "\n".join(lines)

    def inject_critical(self):
        self.scenario = "critical"
        self.current = {
            "temperatura":  random.uniform(95, 115),
            "energia":      random.uniform(5, 15),
            "oxigenio":     random.uniform(13, 16),
            "pressao":      random.uniform(115, 125),
            "comunicacao":  random.uniform(10, 35),
            "velocidade":   random.uniform(7600, 8200),
        }
        self.current = {k: round(v, 1) for k, v in self.current.items()}


# ──────────────────────────────────────────────
# Inteface
# ──────────────────────────────────────────────

class GaugeCard(tk.Frame):
    def __init__(self, parent, label, unit, lo, hi, **kwargs):
        super().__init__(parent, bg=C["panel"], **kwargs)
        self.lo, self.hi = lo, hi
        self.unit = unit

        tk.Label(self, text=label.upper(), font=FONT_LABEL,
                 bg=C["panel"], fg=C["muted"]).pack(pady=(8, 0))

        self.val_var = tk.StringVar(value="---")
        self.val_lbl = tk.Label(self, textvariable=self.val_var,
                                font=FONT_VALUE, bg=C["panel"], fg=C["text"])
        self.val_lbl.pack()

        self.badge_var = tk.StringVar(value="")
        self.badge = tk.Label(self, textvariable=self.badge_var,
                              font=FONT_SMALL, bg=C["panel"], fg=C["muted"])
        self.badge.pack(pady=(0, 4))

        self.bar_canvas = tk.Canvas(self, height=8, bg=C["panel"],
                                    highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=10, pady=(0, 8))

        self.configure(highlightbackground=C["border"], highlightthickness=1,
                       relief="flat")

    def update(self, value, status):
        color = {"ok": C["ok"], "warn": C["warn"], "crit": C["crit"]}[status]
        badge_text = {"ok": "● NOMINAL", "warn": "● ATENÇÃO", "crit": "● CRÍTICO"}[status]
        badge_fg = {"ok": C["ok"], "warn": C["warn"], "crit": C["crit"]}[status]

        self.val_var.set(f"{value}")
        self.val_lbl.configure(fg=color)
        self.badge_var.set(f"{self.unit}  {badge_text}")
        self.badge.configure(fg=badge_fg)

        w = self.bar_canvas.winfo_width() or 180
        self.bar_canvas.delete("all")
        self.bar_canvas.create_rectangle(0, 0, w, 8, fill=C["border"], outline="")
        lo, hi = self.lo, self.hi
        pct = max(0, min(1, (value - lo) / (hi - lo))) if hi != lo else 0.5
        self.bar_canvas.create_rectangle(0, 0, int(w * pct), 8,
                                         fill=color, outline="")


# ──────────────────────────────────────────────
# JANELA PRINCIPAL
# ──────────────────────────────────────────────

class MissionControlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MISSION CONTROL AI — FIAP Space Agency")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.geometry("1200x860")
        self.minsize(1000, 720)

        self.data = MissionData()
        self.client = None
        self.api_key = tk.StringVar()
        self.auto_update = tk.BooleanVar(value=True)
        self.auto_interval = 5
        self._ai_running = False
        self._update_running = False
        self._chat_running = False

        # Histórico de conversa do chatbot
        self.chat_history = []

        self._build_ui()

        # ── Carrega chave do .env
        if OPENAI_API_KEY:
            self.api_key.set(OPENAI_API_KEY)
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self._start_auto_update()
            self._refresh_data()
            self._log("✅ API Key carregada do .env automaticamente. Sistema operacional.")
        else:
            self._ask_api_key()

    # ── UI BUILD ──────────────────────────────

    def _build_ui(self):
        # ── HEADER ──
        header = tk.Frame(self, bg=C["bg"], pady=6)
        header.pack(fill="x", padx=16)

        tk.Label(header, text="🛸  MISSION CONTROL AI",
                 font=("Courier New", 16, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(side="left")

        self.clock_var = tk.StringVar(value="T+00:00")
        tk.Label(header, textvariable=self.clock_var,
                 font=("Courier New", 12, "bold"),
                 bg=C["bg"], fg=C["accent2"]).pack(side="right", padx=8)

        self.status_bar_var = tk.StringVar(value="● SISTEMA INICIALIZANDO")
        tk.Label(header, textvariable=self.status_bar_var,
                 font=FONT_LABEL, bg=C["bg"], fg=C["muted"]).pack(side="right", padx=16)

        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.pack(fill="x", padx=0)

        # ── BODY ──
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # LEFT: gauges
        left = tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left, text="TELEMETRIA EM TEMPO REAL",
                 font=FONT_LABEL, bg=C["bg"], fg=C["muted"]).pack(anchor="w")

        gauge_grid = tk.Frame(left, bg=C["bg"])
        gauge_grid.pack(fill="both", expand=True)

        self.gauges = {}
        params = [
            ("temperatura", "Temperatura", LIMITS["temperatura"]["min"], LIMITS["temperatura"]["max"]),
            ("energia",     "Energia",     0, 100),
            ("oxigenio",    "Oxigênio",    14, 25),
            ("pressao",     "Pressão",     80, 120),
            ("comunicacao", "Comunicação", 0, 100),
            ("velocidade",  "Velocidade",  6000, 30000),
        ]
        for i, (key, label, lo, hi) in enumerate(params):
            row, col = divmod(i, 2)
            card = GaugeCard(gauge_grid, label,
                             LIMITS[key]["unit"], lo, hi,
                             width=200)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            gauge_grid.columnconfigure(col, weight=1)
            self.gauges[key] = card

        # RIGHT: IA output + chatbot + log
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        # ── Análise automática da IA ──
        ia_header = tk.Frame(right, bg=C["bg"])
        ia_header.pack(fill="x")
        tk.Label(ia_header, text="🤖  ANÁLISE AUTOMÁTICA — ARIA",
                 font=FONT_TITLE, bg=C["bg"], fg=C["accent"]).pack(side="left")
        self.ai_status = tk.Label(ia_header, text="",
                                   font=FONT_SMALL, bg=C["bg"], fg=C["muted"])
        self.ai_status.pack(side="right")

        self.ia_text = scrolledtext.ScrolledText(
            right, height=8, font=FONT_MONO,
            bg=C["panel"], fg=C["text"],
            insertbackground=C["accent"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled"
        )
        self.ia_text.pack(fill="both", expand=False, pady=(4, 6))

        sep2 = tk.Frame(right, bg=C["border"], height=1)
        sep2.pack(fill="x", pady=(0, 4))

        # ── CHATBOT ARIA ──
        chat_header = tk.Frame(right, bg=C["bg"])
        chat_header.pack(fill="x")
        tk.Label(chat_header, text="💬  CHATBOT ARIA — Pergunte sobre a missão",
                 font=FONT_LABEL, bg=C["bg"], fg=C["chat_aria"]).pack(side="left")
        tk.Button(chat_header, text="🗑 Limpar Chat",
                  command=self._clear_chat,
                  bg=C["border"], fg=C["muted"],
                  font=FONT_SMALL, relief="flat",
                  padx=6, pady=2, cursor="hand2",
                  activebackground=C["panel"],
                  activeforeground=C["text"]).pack(side="right")

        self.chat_text = scrolledtext.ScrolledText(
            right, height=9, font=FONT_CHAT,
            bg=C["chat_bg"], fg=C["text"],
            insertbackground=C["accent"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled"
        )
        self.chat_text.pack(fill="both", expand=True, pady=(4, 4))

        # Tags de cor para o chat
        self.chat_text.tag_config("user_label",  foreground=C["chat_user"], font=("Courier New", 9, "bold"))
        self.chat_text.tag_config("user_msg",    foreground=C["text"],      font=("Courier New", 9))
        self.chat_text.tag_config("aria_label",  foreground=C["chat_aria"], font=("Courier New", 9, "bold"))
        self.chat_text.tag_config("aria_msg",    foreground="#CBD5E1",      font=("Courier New", 9))
        self.chat_text.tag_config("aria_think",  foreground=C["muted"],     font=("Courier New", 9, "italic"))
        self.chat_text.tag_config("separator",   foreground=C["border"])

        # Campo de entrada do chat
        chat_input_frame = tk.Frame(right, bg=C["bg"])
        chat_input_frame.pack(fill="x", pady=(0, 4))

        self.chat_entry = tk.Entry(
            chat_input_frame,
            font=FONT_CHAT,
            bg=C["panel"], fg=C["text"],
            insertbackground=C["accent"],
            relief="flat", bd=6,
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())

        self.chat_send_btn = tk.Button(
            chat_input_frame,
            text="ENVIAR ▶",
            command=self._send_chat,
            bg=C["accent"], fg=C["bg"],
            font=("Courier New", 9, "bold"),
            relief="flat", padx=10, pady=4,
            cursor="hand2",
            activebackground=C["accent2"],
            activeforeground=C["text"]
        )
        self.chat_send_btn.pack(side="right")

        sep3 = tk.Frame(right, bg=C["border"], height=1)
        sep3.pack(fill="x", pady=(0, 4))

        # ── Log de eventos ──
        tk.Label(right, text="📋  LOG DE EVENTOS",
                 font=FONT_LABEL, bg=C["bg"], fg=C["muted"]).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            right, height=5, font=FONT_SMALL,
            bg=C["panel"], fg=C["muted"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled"
        )
        self.log_text.pack(fill="both", expand=False)

        # ── TOOLBAR ──
        toolbar = tk.Frame(self, bg=C["panel"], pady=6)
        toolbar.pack(fill="x", side="bottom")

        btn_style = dict(bg=C["accent2"], fg=C["text"],
                         font=FONT_LABEL, relief="flat",
                         padx=12, pady=4, cursor="hand2",
                         activebackground=C["accent"],
                         activeforeground=C["bg"])

        tk.Button(toolbar, text="▶  ANALISAR AGORA",
                  command=self._analyze_now, **btn_style).pack(side="left", padx=6)

        tk.Button(toolbar, text="⚠  SIMULAR CRISE",
                  command=self._inject_crisis,
                  bg=C["crit"], fg=C["text"],
                  font=FONT_LABEL, relief="flat",
                  padx=12, pady=4, cursor="hand2",
                  activebackground="#B91C1C",
                  activeforeground=C["text"]).pack(side="left", padx=0)

        tk.Button(toolbar, text="🔄  ATUALIZAR DADOS",
                  command=self._refresh_data, **btn_style).pack(side="left", padx=6)

        tk.Checkbutton(toolbar, text="Auto-update (5s)",
                       variable=self.auto_update,
                       bg=C["panel"], fg=C["muted"],
                       selectcolor=C["border"],
                       activebackground=C["panel"],
                       font=FONT_SMALL,
                       command=self._toggle_auto).pack(side="left", padx=8)

        tk.Label(toolbar,
                 text="FIAP Global Solution 2026.1 — Prompt & AI",
                 font=FONT_SMALL, bg=C["panel"], fg=C["muted"]).pack(side="right", padx=12)

    # ── API KEY DIALOG 

    def _ask_api_key(self):
        win = tk.Toplevel(self)
        win.title("Configurar OpenAI API Key")
        win.configure(bg=C["bg"])
        win.geometry("480x220")
        win.resizable(False, False)
        win.grab_set()
        win.lift()

        entry_var = tk.StringVar(value=self.api_key.get() or "")
        entry = tk.Entry(win, textvariable=entry_var, width=52,
                         font=FONT_MONO, bg=C["panel"], fg=C["accent"],
                         insertbackground=C["accent"],
                         show="*", relief="flat", bd=6)
        entry.pack(pady=12)

        def confirm():
            key = entry_var.get().strip()
            if not key:
                messagebox.showerror("Erro", "API Key não pode ser vazia.")
                return
            self.api_key.set(key)
            self.client = OpenAI(api_key=key)
            win.destroy()
            self._start_auto_update()
            self._refresh_data()
            self._log("✅ API Key configurada manualmente. Sistema operacional.")

        tk.Button(win, text="CONFIRMAR", command=confirm,
                  bg=C["accent"], fg=C["bg"],
                  font=("Courier New", 10, "bold"),
                  relief="flat", padx=16, pady=6,
                  cursor="hand2").pack()

    # ── DATA UPDATE ───────────────────────────

    def _refresh_data(self):
        self.data._generate()
        self._update_gauges()
        self._update_clock()
        self._check_auto_alerts()

    def _update_gauges(self):
        for key, gauge in self.gauges.items():
            val = self.data.current[key]
            st  = self.data.status(key)
            gauge.update(val, st)

    def _update_clock(self):
        h = self.data.mission_time // 60
        m = self.data.mission_time % 60
        self.clock_var.set(f"T+{h:02d}:{m:02d}")

    def _check_auto_alerts(self):
        crits = [k for k in LIMITS if self.data.status(k) == "crit"]
        warns = [k for k in LIMITS if self.data.status(k) == "warn"]
        if crits:
            self.status_bar_var.set(f"🔴  ALERTA CRÍTICO: {', '.join(crits).upper()}")
            for k in crits:
                self._log(f"🔴 CRÍTICO  | {k.upper():15s} = {self.data.current[k]} {LIMITS[k]['unit']}")
        elif warns:
            self.status_bar_var.set(f"🟡  ATENÇÃO: {', '.join(warns).upper()}")
            for k in warns:
                self._log(f"🟡 ATENÇÃO  | {k.upper():15s} = {self.data.current[k]} {LIMITS[k]['unit']}")
        else:
            self.status_bar_var.set("🟢  TODOS OS SISTEMAS NOMINAIS")

    # ── AI ANALYSIS (automática) ──────────────

    def _analyze_now(self):
        if self._ai_running:
            return
        if not self.client:
            messagebox.showwarning("API Key", "Configure a API Key primeiro.")
            self._ask_api_key()
            return
        threading.Thread(target=self._run_ai, daemon=True).start()

    def _run_ai(self):
        self._ai_running = True
        self.ai_status.configure(text="⟳ consultando ARIA...", fg=C["accent"])
        self._set_ia_text("⟳  Consultando ARIA — Aguarde...\n")

        telemetry = self.data.build_telemetry_string()
        scenario_hint = {
            "normal":   "A missão está operando normalmente.",
            "warning":  "Atenção: alguns parâmetros estão se aproximando dos limites.",
            "critical": "ALERTA CRÍTICO: múltiplos parâmetros fora dos limites operacionais.",
        }[self.data.scenario]

        user_msg = (
            f"=== TELEMETRIA DA MISSÃO — T+{self.data.mission_time:04d} min ===\n"
            f"{telemetry}\n\n"
            f"Contexto: {scenario_hint}\n\n"
            "Forneça: diagnóstico, alertas ativos, ações corretivas e previsão."
        )

        try:
            resp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                max_tokens=400,
                temperature=0.4,
            )
            answer = resp.choices[0].message.content.strip()
            ts = datetime.now().strftime("%H:%M:%S")
            output = f"[{ts}] — T+{self.data.mission_time:04d} min\n\n{answer}\n"
            self._set_ia_text(output)
            self._log(f"🤖 IA analisou cenário [{self.data.scenario.upper()}] às {ts}")
            self.ai_status.configure(text=f"✓ última análise {ts}", fg=C["ok"])
        except Exception as e:
            self._set_ia_text(f"⚠  Erro ao contatar a IA:\n{e}")
            self._log(f"⚠ Erro IA: {e}")
            self.ai_status.configure(text="⚠ erro", fg=C["crit"])
            messagebox.showerror("Erro OpenAI", str(e))
        finally:
            self._ai_running = False

    # ── CHATBOT ARIA ──────────────────────────

    def _send_chat(self):
        if self._chat_running:
            return

        question = self.chat_entry.get().strip()
        if not question:
            return

        if not self.client:
            messagebox.showwarning("API Key", "Configure a API Key primeiro.")
            self._ask_api_key()
            return

        # Limpa o campo de entrada imediatamente
        self.chat_entry.delete(0, "end")

        # Exibe mensagem do operador
        self._chat_append_user(question)

        # Roda a chamada de IA em thread separada
        threading.Thread(
            target=self._run_chat_ai,
            args=(question,),
            daemon=True
        ).start()

    def _run_chat_ai(self, question):
        self._chat_running = True
        self.after(0, lambda: self.chat_send_btn.configure(state="disabled", text="..."))

        # Monta o contexto com telemetria atual
        telemetry = self.data.build_telemetry_string()
        scenario_hint = {
            "normal":   "A missão está operando normalmente.",
            "warning":  "Atenção: alguns parâmetros estão se aproximando dos limites.",
            "critical": "ALERTA CRÍTICO: múltiplos parâmetros fora dos limites operacionais.",
        }[self.data.scenario]

        telemetry_context = (
            f"[TELEMETRIA ATUAL — T+{self.data.mission_time:04d} min]\n"
            f"{telemetry}\n"
            f"Cenário: {scenario_hint}"
        )

        # Histórico de conversa (máximo 10 turnos para não exceder tokens)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        history_tail = self.chat_history[-20:] if len(self.chat_history) > 20 else self.chat_history
        messages.extend(history_tail)

        # Pergunta do operador com contexto de telemetria embutido
        full_question = (
            f"{telemetry_context}\n\n"
            f"Pergunta do Operador: {question}"
        )
        messages.append({"role": "user", "content": full_question})

        # Indicador "pensando"
        self.after(0, lambda: self._chat_append_thinking())

        try:
            resp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=350,
                temperature=0.5,
            )
            answer = resp.choices[0].message.content.strip()

            # Atualiza histórico (sem o contexto de telemetria, apenas a pergunta limpa)
            self.chat_history.append({"role": "user",      "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})

            ts = datetime.now().strftime("%H:%M:%S")
            self.after(0, lambda a=answer, t=ts: self._chat_replace_thinking(a, t))
            self._log(f"💬 Chat — operador perguntou sobre a missão às {ts}")

        except Exception as e:
            self.after(0, lambda err=e: self._chat_replace_thinking(f"⚠ Erro: {err}", ""))
            self.after(0, lambda err=e: messagebox.showerror("Erro OpenAI", str(err)))
            self._log(f"⚠ Erro Chat IA: {e}")
        finally:
            self._chat_running = False
            self.after(0, lambda: self.chat_send_btn.configure(state="normal", text="ENVIAR ▶"))

    def _chat_append_user(self, message):
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", "OPERADOR › ", "user_label")
        self.chat_text.insert("end", f"{message}\n", "user_msg")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _chat_append_thinking(self):
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", "ARIA › ", "aria_label")
        self.chat_text.insert("end", "consultando dados da missão...\n", "aria_think")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")
        # Marca a posição do placeholder para substituição posterior
        self._thinking_line_index = self.chat_text.index("end-1c linestart")

    def _chat_replace_thinking(self, answer, timestamp):
        self.chat_text.configure(state="normal")

        # Remove a última linha (o "pensando...")
        last_line_start = self.chat_text.index("end-2l linestart")
        last_line_end   = self.chat_text.index("end-1c")
        self.chat_text.delete(last_line_start, last_line_end)

        # Insere a resposta real
        ts_label = f"  [{timestamp}]" if timestamp else ""
        self.chat_text.insert("end", "ARIA › ", "aria_label")
        self.chat_text.insert("end", f"{answer}{ts_label}\n", "aria_msg")
        self.chat_text.insert("end", "─" * 60 + "\n", "separator")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _clear_chat(self):
        self.chat_history.clear()
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
        self._log("🗑 Histórico do chat limpo.")

    # ── CRISIS INJECTION ─────────────────────

    def _inject_crisis(self):
        self.data.inject_critical()
        self._update_gauges()
        self._update_clock()
        self._check_auto_alerts()
        self._log("💥 CRISE SIMULADA INJETADA — todos os parâmetros em zona crítica")
        self._analyze_now()

    # ── AUTO UPDATE ───────────────────────────

    def _start_auto_update(self):
        if self._update_running:
            return
        self._update_running = True
        self._auto_loop()

    def _auto_loop(self):
        if not self._update_running:
            return
        if self.auto_update.get():
            self._refresh_data()
            if self.data.tick % 3 == 0 and self.client and not self._ai_running:
                threading.Thread(target=self._run_ai, daemon=True).start()
        self.after(self.auto_interval * 1000, self._auto_loop)

    def _toggle_auto(self):
        if self.auto_update.get():
            self._log("🔄 Auto-update ativado (5s)")
        else:
            self._log("⏸ Auto-update pausado")

    # ── HELPERS ───────────────────────────────

    def _set_ia_text(self, text):
        self.ia_text.configure(state="normal")
        self.ia_text.delete("1.0", "end")
        self.ia_text.insert("end", text)
        self.ia_text.configure(state="disabled")
        self.ia_text.see("end")

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}]  {msg}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def on_close(self):
        self._update_running = False
        self.destroy()


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = MissionControlApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()