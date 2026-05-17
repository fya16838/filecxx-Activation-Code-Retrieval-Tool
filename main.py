import re
import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from html.parser import HTMLParser
import urllib.request
import ssl

URL = "https://filecxx.com/zh_CN/activation_code.html"
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".filecxx_cache.json")

# ── daisyUI 配色 ──────────────────────────────────────────
COLORS = {
    "primary":    "#6419e6",
    "primary_fg": "#ffffff",
    "secondary":  "#d926a9",
    "accent":     "#1fb2a6",
    "neutral":    "#2a303c",
    "neutral_fg": "#a6adbb",
    "base_100":   "#ffffff",
    "base_200":   "#f2f2f3",
    "base_300":   "#e5e6e7",
    "success":    "#36d399",
    "warning":    "#fbbd23",
    "error":      "#f87272",
    "info":       "#3abff8",
    "info_text":  "#1d4ed8",
    "success_text": "#15803d",
    "muted":      "#8b919b",
}


class CodeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_codes = False
        self.codes_text = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "pre" and attrs.get("id") == "codes":
            self.in_codes = True

    def handle_endtag(self, tag):
        if tag == "pre" and self.in_codes:
            self.in_codes = False

    def handle_data(self, data):
        if self.in_codes:
            self.codes_text += data


def fetch_codes():
    """从 filecxx.com 抓取激活码（线程安全）"""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode("utf-8")
    parser = CodeParser()
    parser.feed(html)
    lines = [l.strip() for l in parser.codes_text.split("\n") if l.strip()]
    entries = []
    for i in range(0, len(lines) - 1, 2):
        m = re.match(
            r"(\d{4}-\d{2}-\d{2})\s*\d{2}:\d{2}:\d{2}\s*-\s*"
            r"(\d{4}-\d{2}-\d{2})\s*\d{2}:\d{2}:\d{2}",
            lines[i],
        )
        if not m:
            continue
        start = datetime.strptime(m.group(1), "%Y-%m-%d")
        end = datetime.strptime(m.group(2), "%Y-%m-%d")
        entries.append((start, end, lines[i + 1].strip()))
    return entries


def save_cache(entries):
    """将激活码缓存到本地 JSON 文件"""
    try:
        data = [(s.isoformat(), e.isoformat(), c) for s, e, c in entries]
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass  # 缓存失败不影响主流程


def load_cache():
    """从本地 JSON 文件加载缓存的激活码"""
    try:
        if not os.path.exists(CACHE_FILE):
            return []
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [(datetime.fromisoformat(s), datetime.fromisoformat(e), c) for s, e, c in data]
    except Exception:
        return []


class DaisyUIApp:
    def __init__(self, root, entries):
        self.root = root
        self.root.title("文件蜈蚣激活码")
        self.root.geometry("960x620")
        self.root.minsize(760, 440)
        self.root.configure(bg=COLORS["base_200"])

        self._setup_styles()
        self._build_ui()
        self._populate(entries)

    # ── 样式 ───────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        self.font_default = ("Segoe UI", 11)
        self.font_small   = ("Segoe UI", 10)
        self.font_bold    = ("Segoe UI", 11, "bold")
        self.font_title   = ("Segoe UI", 16, "bold")

        style.configure(".", font=self.font_default, background=COLORS["base_200"])

        style.configure(
            "Treeview",
            background=COLORS["base_100"],
            foreground="#1f2937",
            rowheight=44,
            fieldbackground=COLORS["base_100"],
            borderwidth=0,
            font=self.font_default,
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["neutral"],
            foreground="#e5e7eb",
            font=self.font_bold,
            padding=(16, 10),
            borderwidth=0,
        )
        style.map(
            "Treeview.Heading",
            background=[("active", COLORS["neutral"])],
        )
        style.map(
            "Treeview",
            background=[("selected", COLORS["primary"])],
            foreground=[("selected", COLORS["primary_fg"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=COLORS["base_300"],
            troughcolor=COLORS["base_200"],
            borderwidth=0,
            arrowsize=14,
        )

    # ── 界面结构 ───────────────────────────────────────────
    def _build_ui(self):
        self.header = tk.Frame(self.root, bg=COLORS["neutral"], height=56)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        inner = tk.Frame(self.header, bg=COLORS["neutral"])
        inner.pack(fill="both", padx=24)

        tk.Label(
            inner, text="文件蜈蚣激活码管理",
            fg="#e5e7eb", bg=COLORS["neutral"],
            font=self.font_title,
        ).pack(side="left", pady=12)

        body = tk.Frame(self.root, bg=COLORS["base_200"])
        body.pack(fill="both", expand=True, padx=24, pady=(16, 0))

        table_card = tk.Frame(body, bg=COLORS["base_100"], highlightthickness=0)
        table_card.pack(side="left", fill="both", expand=True)

        self._build_table_header(table_card)

        self.tree = ttk.Treeview(
            table_card,
            columns=("start", "end", "status", "code"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("start", text="开始日期")
        self.tree.heading("end", text="结束日期")
        self.tree.heading("status", text="状态")
        self.tree.heading("code", text="激活码")

        self.tree.column("start", width=108, anchor="center")
        self.tree.column("end", width=108, anchor="center")
        self.tree.column("status", width=88, anchor="center")
        self.tree.column("code", width=480)

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.tag_configure("active_row", background="#f0fdf4")
        self.tree.tag_configure("upcoming_row", background="#eff6ff")

        sidebar = tk.Frame(body, bg=COLORS["base_200"], width=210)
        sidebar.pack(side="right", fill="y", padx=(16, 0))
        sidebar.pack_propagate(False)

        self.card_active = self._make_card(sidebar, "生效中", "0", COLORS["success"])
        self.card_active.pack(fill="x", pady=(0, 12))

        self.card_upcoming = self._make_card(sidebar, "待生效", "0", COLORS["info"])
        self.card_upcoming.pack(fill="x")

        tk.Label(
            sidebar, text="点击任意行\n复制激活码到剪贴板",
            fg=COLORS["muted"], bg=COLORS["base_200"],
            font=self.font_small, justify="center",
        ).pack(pady=(16, 12), anchor="center")

        self.refresh_btn = tk.Frame(
            sidebar, bg=COLORS["primary"], cursor="hand2",
        )
        self.refresh_btn.pack(fill="x")
        self.refresh_btn_label = tk.Label(
            self.refresh_btn, text="⟳刷新激活码",
            fg=COLORS["primary_fg"], bg=COLORS["primary"],
            font=self.font_bold, padx=16, pady=10,
        )
        self.refresh_btn_label.pack()
        self.refresh_btn_label.bind("<Button-1>", lambda e: self._refresh())
        self._bind_hover(self.refresh_btn_label, COLORS["primary"], "#4f14cc")

        self.status_bar = tk.Frame(self.root, bg=COLORS["base_300"], height=28)
        self.status_bar.pack(fill="x", side="bottom", pady=(16, 0))
        self.status_bar.pack_propagate(False)
        self.status_label = tk.Label(
            self.status_bar, text="就绪",
            fg="#6b7280", bg=COLORS["base_300"],
            font=self.font_small, anchor="w",
        )
        self.status_label.pack(side="left", padx=16, pady=4)

    def _build_table_header(self, parent):
        bar = tk.Frame(parent, bg=COLORS["neutral"])
        bar.pack(fill="x")
        cols = [
            ("开始日期", 108), ("结束日期", 108),
            ("状态", 88), ("激活码", 500),
        ]
        x_offset = 0
        for text, width in cols:
            lbl = tk.Label(
                bar, text=text,
                fg="#e5e7eb", bg=COLORS["neutral"],
                font=self.font_bold,
            )
            lbl.place(x=x_offset + 8, y=6, width=width - 16, height=22)
            x_offset += width

    def _make_card(self, parent, title, count, color):
        card = tk.Frame(
            parent,
            bg=COLORS["base_100"],
            highlightthickness=0,
            padx=16, pady=12,
        )
        tk.Label(
            card, text=title,
            fg=COLORS["muted"], bg=COLORS["base_100"],
            font=self.font_small,
        ).pack(anchor="center")

        num = tk.Label(
            card, text=count,
            fg=color, bg=COLORS["base_100"],
            font=("Segoe UI", 22, "bold"),
        )
        num.pack(anchor="center")
        card._num_label = num
        return card

    def _bind_hover(self, widget, normal, hover):
        widget.bind("<Enter>", lambda e: widget.configure(bg=hover))
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal))

    # ── 刷新（异步） ───────────────────────────────────────
    def _refresh(self):
        self.refresh_btn_label.config(text="⟳ 刷新中...", fg="#d1d5db")
        self.refresh_btn_label.update()

        def _do_fetch():
            try:
                entries = fetch_codes()
                self.root.after(0, self._on_refresh_done, entries)
            except Exception as exc:
                self.root.after(0, self._on_refresh_error, str(exc))

        threading.Thread(target=_do_fetch, daemon=True).start()

    def _on_refresh_done(self, entries):
        save_cache(entries)
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._populate(entries)
        self.refresh_btn_label.config(text="⟳刷新激活码", fg=COLORS["primary_fg"])
        self._show_toast("✓ 激活码已刷新")

    def _on_refresh_error(self, error_msg):
        messagebox.showerror("刷新失败", f"获取激活码失败:\n{error_msg}")
        self.refresh_btn_label.config(text="⟳刷新激活码", fg=COLORS["primary_fg"])

    def _background_refresh(self):
        """启动时后台静默刷新"""
        def _do_fetch():
            try:
                entries = fetch_codes()
                self.root.after(0, self._on_bg_refresh_done, entries)
            except Exception:
                pass  # 静默失败，已有缓存兜底

        threading.Thread(target=_do_fetch, daemon=True).start()

    def _on_bg_refresh_done(self, entries):
        save_cache(entries)
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._populate(entries)
        self._show_toast("✓ 激活码已刷新")

    # ── 数据填充 ───────────────────────────────────────────
    def _populate(self, entries):
        now = datetime.now()
        valid = []
        for start, end, code in entries:
            if end < now:
                continue
            if start <= now <= end:
                status = "生效中"
            else:
                status = "待生效"
            days_left = (end - now).days
            valid.append((start, end, status, days_left, code))

        valid.sort(key=lambda x: x[0])

        active_count = sum(1 for v in valid if v[2] == "生效中")
        upcoming_count = sum(1 for v in valid if v[2] == "待生效")

        self.card_active._num_label.config(text=str(active_count))
        self.card_upcoming._num_label.config(text=str(upcoming_count))

        for start, end, status, days_left, code in valid:
            tag = "active_row" if status == "生效中" else "upcoming_row"
            self.tree.insert(
                "", "end",
                values=(
                    start.strftime("%Y-%m-%d"),
                    end.strftime("%Y-%m-%d"),
                    f"● {status}",
                    code,
                ),
                tags=(tag,),
            )

        self.status_label.config(
            text=f"共 {len(valid)} 个有效激活码  |  "
                 f"{active_count} 个生效中  |  "
                 f"{upcoming_count} 个待生效  |  "
                 f"更新时间: {now.strftime('%Y-%m-%d %H:%M')}"
        )

    # ── 交互 ───────────────────────────────────────────────
    def _on_click(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        code = self.tree.item(sel[0], "values")[3]
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.root.update()
        self._show_toast("✓ 激活码已复制到剪贴板")

    def _show_toast(self, msg):
        toast = tk.Toplevel(self.root)
        toast.wm_overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=COLORS["neutral"])

        x = self.root.winfo_rootx() + self.root.winfo_width() // 2 - 140
        y = self.root.winfo_rooty() + self.root.winfo_height() - 80
        toast.wm_geometry(f"280x38+{x}+{y}")

        inner = tk.Frame(toast, bg=COLORS["neutral"], padx=16, pady=8)
        inner.pack(fill="both", expand=True)

        tk.Label(
            inner, text=msg,
            fg="#e5e7eb", bg=COLORS["neutral"],
            font=self.font_default,
        ).pack()

        # 淡出动画（非阻塞）
        self._fade_out(toast, [1.0, 0.85, 0.7, 0.55, 0.4, 0.25, 0.1])

    def _fade_out(self, toast, alphas):
        if not alphas:
            toast.destroy()
            return
        toast.attributes("-alpha", alphas[0])
        toast.after(30, lambda: self._fade_out(toast, alphas[1:]))


def main():
    # 先加载缓存，立即显示界面
    entries = load_cache()
    root = tk.Tk()
    app = DaisyUIApp(root, entries if entries else [])

    # 后台静默刷新
    app._background_refresh()

    root.mainloop()


if __name__ == "__main__":
    main()
