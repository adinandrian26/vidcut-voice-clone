"""VidCut Desktop — software voice clone (bukan web).

Jendela Tkinter yang berbicara ke layanan Voice Clone (lokal
http://localhost:8520 maupun server GPU di cloud). Jalankan backend
dulu, atau pakai Jalankan_VidCut.bat yang menyalakan keduanya.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__:
    from . import vc_client
else:  # dijalankan langsung sebagai file .py
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from desktop import vc_client

CONFIG_PATH = Path.home() / ".vidcut_desktop.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("VidCut Desktop — Voice Clone")
        self.geometry("640x720")
        cfg = load_config()
        self._busy = False
        self._last_audio: bytes = b""
        self._last_format = "mp3"

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="URL layanan").pack(anchor="w")
        self.url_var = tk.StringVar(
            value=cfg.get("url", vc_client.DEFAULT_URL))
        ttk.Entry(frm, textvariable=self.url_var).pack(fill="x")

        ttk.Label(frm, text="Kunci akses (kosongkan bila lokal tanpa kunci)").pack(
            anchor="w", pady=(8, 0))
        self.key_var = tk.StringVar(value=cfg.get("api_key", ""))
        ttk.Entry(frm, textvariable=self.key_var, show="*").pack(fill="x")

        ttk.Label(frm, text="Teks (Bahasa Indonesia)").pack(
            anchor="w", pady=(8, 0))
        self.text = tk.Text(frm, height=6)
        self.text.pack(fill="x")

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Bahasa:").pack(side="left")
        self.lang_var = tk.StringVar(value="id")
        ttk.Combobox(row, textvariable=self.lang_var, values=["id", "en"],
                     width=5, state="readonly").pack(side="left", padx=6)

        ttk.Label(frm, text="Sampel suara").pack(anchor="w", pady=(8, 0))
        self.src_var = tk.StringVar(value="file")
        src = ttk.Frame(frm)
        src.pack(fill="x")
        ttk.Radiobutton(src, text="File audio", variable=self.src_var,
                        value="file").pack(side="left")
        ttk.Radiobutton(src, text="YouTube", variable=self.src_var,
                        value="youtube").pack(side="left", padx=12)
        self.file_var = tk.StringVar(value="")
        file_row = ttk.Frame(frm)
        file_row.pack(fill="x", pady=4)
        ttk.Entry(file_row, textvariable=self.file_var,
                  state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Pilih file...",
                   command=self._pilih_file).pack(side="left", padx=6)
        self.yt_var = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.yt_var).pack(fill="x")
        ttk.Label(frm, text="Link YouTube ditempel di kolom atas bila "
                            "memilih YouTube.").pack(anchor="w")

        self.consent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm, text="Saya memiliki izin menggunakan suara ini.",
            variable=self.consent_var).pack(anchor="w", pady=(8, 0))

        self.btn = ttk.Button(frm, text="Generate suara",
                              command=self._generate)
        self.btn.pack(fill="x", pady=10)
        self.prog = ttk.Progressbar(frm, maximum=100)
        self.prog.pack(fill="x")
        self.status_var = tk.StringVar(value="Siap.")
        ttk.Label(frm, textvariable=self.status_var).pack(anchor="w")

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=10)
        self.play_btn = ttk.Button(btns, text="Putar hasil",
                                   command=self._play, state="disabled")
        self.play_btn.pack(side="left", expand=True, fill="x", padx=2)
        self.save_btn = ttk.Button(btns, text="Simpan MP3...",
                                   command=self._save, state="disabled")
        self.save_btn.pack(side="left", expand=True, fill="x", padx=2)

    # -- aksi UI --
    def _pilih_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.ogg *.flac")])
        if path:
            self.file_var.set(path)
            self.src_var.set("file")

    def _set_status(self, text: str, progress: int | None = None) -> None:
        self.status_var.set(text)
        if progress is not None:
            self.prog["value"] = progress

    def _generate(self) -> None:
        if self._busy:
            return
        url = self.url_var.get()
        key = self.key_var.get()
        text = self.text.get("1.0", "end")
        save_config({"url": url, "api_key": key})
        try:
            vc_client.normalize_url(url)
            if self.src_var.get() == "file":
                vc_client.validate_inputs(text, self.consent_var.get(),
                                          file_path=self.file_var.get())
            else:
                vc_client.validate_inputs(text, self.consent_var.get(),
                                          youtube_url=self.yt_var.get())
        except ValueError as exc:
            messagebox.showerror("VidCut", str(exc))
            return
        self._busy = True
        self.btn.config(state="disabled")
        self.play_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        threading.Thread(target=self._run_job,
                         args=(url, key, text), daemon=True).start()

    def _run_job(self, url: str, key: str, text: str) -> None:
        jid = ""
        try:
            self.after(0, self._set_status, "Menghubungi layanan...", 2)
            vc_client.health(url)
            self.after(0, self._set_status, "Mengirim job...", 5)
            if self.src_var.get() == "file":
                jid = vc_client.create_job_upload(
                    url, key, text, self.lang_var.get(),
                    self.file_var.get())
            else:
                jid = vc_client.create_job_link(
                    url, key, text, self.lang_var.get(),
                    self.yt_var.get())

            def on_progress(done: int, stage: str, detail: str) -> None:
                self.after(0, self._set_status,
                           f"{done}% — {detail or stage}", done)

            vc_client.wait_done(url, key, jid, on_progress=on_progress)
            self.after(0, self._set_status, "Mengunduh hasil...", 97)
            self._last_audio = vc_client.download_audio(url, key, jid, "mp3")
            self._last_format = "mp3"
            self.after(0, self._set_status, "Selesai. Klik Putar / Simpan.",
                       100)
            self.after(0, lambda: self.play_btn.config(state="normal"))
            self.after(0, lambda: self.save_btn.config(state="normal"))
        except Exception as exc:  # noqa: BLE001 - tampilkan ke pengguna
            self.after(0, self._set_status, "Siap.", 0)
            self.after(0, messagebox.showerror, "VidCut", str(exc)[:500])
        finally:
            if jid:
                try:
                    vc_client.delete_job(url, key, jid)
                except Exception:
                    pass
            self._busy = False
            self.after(0, lambda: self.btn.config(state="normal"))

    def _play(self) -> None:
        if not self._last_audio:
            return
        tmp = Path(tempfile.gettempdir()) / "vidcut-hasil.mp3"
        tmp.write_bytes(self._last_audio)
        os.startfile(str(tmp))  # buka pemutar bawaan Windows

    def _save(self) -> None:
        if not self._last_audio:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3")],
            initialfile="vidcut-hasil.mp3")
        if path:
            Path(path).write_bytes(self._last_audio)
            messagebox.showinfo("VidCut", f"Tersimpan:\n{path}")


def main() -> None:
    import sys
    if "--smoke" in sys.argv[1:]:
        # Uji bundel .exe tanpa membuka jendela.
        print("smoke OK:", vc_client.DEFAULT_URL)
        return
    App().mainloop()


if __name__ == "__main__":
    main()
