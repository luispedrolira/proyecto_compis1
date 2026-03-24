"""
YALex Lexer Generator — Graphical User Interface
Built with tkinter.
"""
from __future__ import annotations

import os
import sys
import io
import threading
import importlib.util
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from tkinter import font as tkfont
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_pipeline_capture(yal_path: str, output_path: str):
    """Run the pipeline and capture stdout/stderr. Returns (result_dict, log_text)."""
    import traceback

    buf = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = buf
    sys.stderr = buf

    result = None
    try:
        # Import here to avoid circular issues at module load time
        from pipeline import run_pipeline
        result = run_pipeline(yal_path, output_path)
    except Exception:
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result, buf.getvalue()


def _run_lexer_on_file(lexer_path: str, input_path: str) -> str:
    """Load a generated lexer module and run it on input_path. Returns output text."""
    import traceback

    buf = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = buf
    sys.stderr = buf

    try:
        spec = importlib.util.spec_from_file_location("generated_lexer", lexer_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        tokens = mod.tokenize(text)
        for tok in tokens:
            print(tok)
    except Exception:
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class YALexApp:
    """Main GUI application for the YALex Lexer Generator."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YALex Lexer Generator")
        self.root.geometry("1100x750")
        self.root.minsize(800, 600)

        self._yal_path: Optional[str] = None
        self._output_lexer_path: Optional[str] = None
        self._diagram_path: Optional[str] = None
        self._diagram_image: Optional[tk.PhotoImage] = None  # keep reference

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # ---- Top bar ----
        top = ttk.Frame(self.root, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Archivo YALex:").grid(row=0, column=0, sticky="w")
        self._yal_var = tk.StringVar()
        ttk.Entry(top, textvariable=self._yal_var, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(top, text="Examinar", command=self._browse_yal).grid(
            row=0, column=2, padx=2
        )
        self._gen_btn = ttk.Button(
            top, text="Generar Lexer", command=self._start_generate, state="disabled"
        )
        self._gen_btn.grid(row=0, column=3, padx=2)

        # ---- Main paned area ----
        paned_v = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned_v.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

        # Top half: source + diagram
        paned_h = ttk.PanedWindow(paned_v, orient=tk.HORIZONTAL)
        paned_v.add(paned_h, weight=3)

        # Source code panel
        src_frame = ttk.LabelFrame(paned_h, text="Código fuente YALex", padding=4)
        paned_h.add(src_frame, weight=1)
        src_frame.rowconfigure(0, weight=1)
        src_frame.columnconfigure(0, weight=1)
        self._source_text = scrolledtext.ScrolledText(
            src_frame, state="disabled", wrap="none",
            font=("Courier", 10), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white"
        )
        self._source_text.grid(row=0, column=0, sticky="nsew")

        # Diagram panel
        diag_frame = ttk.LabelFrame(paned_h, text="Diagrama de transición (DFA)", padding=4)
        paned_h.add(diag_frame, weight=1)
        diag_frame.rowconfigure(0, weight=1)
        diag_frame.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(diag_frame, bg="#f0f0f0", cursor="hand2")
        self._canvas.grid(row=0, column=0, sticky="nsew")
        diag_vsb = ttk.Scrollbar(diag_frame, orient="vertical", command=self._canvas.yview)
        diag_vsb.grid(row=0, column=1, sticky="ns")
        diag_hsb = ttk.Scrollbar(diag_frame, orient="horizontal", command=self._canvas.xview)
        diag_hsb.grid(row=1, column=0, sticky="ew")
        self._canvas.configure(yscrollcommand=diag_vsb.set, xscrollcommand=diag_hsb.set)
        self._canvas.bind("<MouseWheel>", self._on_canvas_scroll)
        self._canvas.bind("<Button-4>", self._on_canvas_scroll)
        self._canvas.bind("<Button-5>", self._on_canvas_scroll)

        ttk.Label(diag_frame, text="(genera un lexer para ver el diagrama)", foreground="gray").grid(
            row=2, column=0, columnspan=2
        )
        self._diag_hint = diag_frame.winfo_children()[-1]

        # Bottom half: log + tester
        paned_h2 = ttk.PanedWindow(paned_v, orient=tk.HORIZONTAL)
        paned_v.add(paned_h2, weight=2)

        # Log panel
        log_frame = ttk.LabelFrame(paned_h2, text="Log de generación", padding=4)
        paned_h2.add(log_frame, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self._log_text = scrolledtext.ScrolledText(
            log_frame, state="disabled", wrap="word",
            font=("Courier", 9), bg="#1e1e1e", fg="#9cdcfe",
            insertbackground="white"
        )
        self._log_text.grid(row=0, column=0, sticky="nsew")

        # Tester panel
        test_frame = ttk.LabelFrame(paned_h2, text="Probar Lexer", padding=4)
        paned_h2.add(test_frame, weight=1)
        test_frame.columnconfigure(1, weight=1)
        test_frame.rowconfigure(2, weight=1)

        ttk.Label(test_frame, text="Archivo:").grid(row=0, column=0, sticky="w")
        self._input_var = tk.StringVar()
        ttk.Entry(test_frame, textvariable=self._input_var, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(test_frame, text="Abrir", command=self._browse_input).grid(
            row=0, column=2, padx=2
        )
        self._run_btn = ttk.Button(
            test_frame, text="Ejecutar Lexer", command=self._run_lexer, state="disabled"
        )
        self._run_btn.grid(row=1, column=0, columnspan=3, pady=4)

        ttk.Label(test_frame, text="Tokens:").grid(row=2, column=0, sticky="nw")
        self._tokens_text = scrolledtext.ScrolledText(
            test_frame, state="disabled", wrap="word",
            font=("Courier", 9), bg="#1e1e1e", fg="#ce9178",
            insertbackground="white"
        )
        self._tokens_text.grid(row=3, column=0, columnspan=3, sticky="nsew")
        test_frame.rowconfigure(3, weight=1)

        # ---- Status bar ----
        self._status_var = tk.StringVar(value="Listo.")
        status_bar = ttk.Label(
            self.root, textvariable=self._status_var,
            relief="sunken", anchor="w", padding=(4, 2)
        )
        status_bar.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_yal(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo YALex",
            filetypes=[("YALex files", "*.yal"), ("All files", "*.*")],
        )
        if not path:
            return
        self._yal_path = path
        self._yal_var.set(path)
        self._gen_btn.configure(state="normal")

        # Show source code
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self._set_text(self._source_text, content)
        except Exception as e:
            self._log(f"Error leyendo archivo: {e}")

        self._status_var.set(f"Archivo seleccionado: {os.path.basename(path)}")

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de entrada",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self._input_var.set(path)
        if self._output_lexer_path and os.path.exists(self._output_lexer_path):
            self._run_btn.configure(state="normal")

    def _start_generate(self):
        if not self._yal_path:
            return
        self._gen_btn.configure(state="disabled")
        self._status_var.set("Generando lexer...")
        self._log_clear()
        self._canvas.delete("all")

        thread = threading.Thread(target=self._generate_worker, daemon=True)
        thread.start()

    def _generate_worker(self):
        yal_path = self._yal_path
        base_name = os.path.splitext(os.path.basename(yal_path))[0]

        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", f"{base_name}_lexer.py")
        diagram_base = os.path.join("output", f"{base_name}_diagram")

        result, log = _run_pipeline_capture(yal_path, output_path)

        # Schedule UI update on main thread
        self.root.after(0, self._generate_done, result, log, output_path, diagram_base)

    def _generate_done(self, result, log, output_path, diagram_base):
        self._log(log)

        if result is None:
            self._status_var.set("Error en la generacion. Ver log.")
            self._gen_btn.configure(state="normal")
            return

        self._output_lexer_path = output_path
        self._status_var.set(f"Lexer generado: {output_path}")
        self._log(f"\n[OK] Lexer guardado en: {output_path}")

        # Enable run button if input is already selected
        if self._input_var.get():
            self._run_btn.configure(state="normal")

        # Generate diagram
        min_dfa = result.get("min_dfa")
        if min_dfa:
            self._log("\n[Diagrama] Generando diagrama de transicion...")
            try:
                from diagram.visualizer import render_dfa_diagram
                img_path = render_dfa_diagram(min_dfa, output_path=diagram_base + ".png")
                if img_path and os.path.exists(img_path):
                    self._diagram_path = img_path
                    self._log(f"[Diagrama] Guardado en: {img_path}")
                    self.root.after(0, self._show_diagram, img_path)
                else:
                    self._log("[Diagrama] No se pudo generar la imagen.")
            except Exception as e:
                self._log(f"[Diagrama] Error: {e}")

        self._gen_btn.configure(state="normal")

    def _run_lexer(self):
        lexer_path = self._output_lexer_path
        input_path = self._input_var.get()

        if not lexer_path or not input_path:
            messagebox.showwarning("Faltan datos", "Genera un lexer y selecciona un archivo de entrada.")
            return

        self._set_text(self._tokens_text, "Ejecutando...\n")
        self._status_var.set("Ejecutando lexer...")

        def worker():
            output = _run_lexer_on_file(lexer_path, input_path)
            self.root.after(0, self._lexer_done, output)

        threading.Thread(target=worker, daemon=True).start()

    def _lexer_done(self, output: str):
        self._set_text(self._tokens_text, output)
        self._status_var.set("Lexer ejecutado.")

    # ------------------------------------------------------------------
    # Diagram display
    # ------------------------------------------------------------------

    def _show_diagram(self, img_path: str):
        try:
            # Try PIL first for better quality
            try:
                from PIL import Image, ImageTk
                img = Image.open(img_path)
                # Fit to canvas size
                self._canvas.update_idletasks()
                cw = max(self._canvas.winfo_width(), 400)
                ch = max(self._canvas.winfo_height(), 300)
                img.thumbnail((cw * 2, ch * 2), Image.LANCZOS)
                self._diagram_image = ImageTk.PhotoImage(img)
            except ImportError:
                # Fall back to tk.PhotoImage (only supports PNG/GIF)
                self._diagram_image = tk.PhotoImage(file=img_path)

            self._canvas.delete("all")
            iw = self._diagram_image.width()
            ih = self._diagram_image.height()
            self._canvas.config(scrollregion=(0, 0, iw, ih))
            self._canvas.create_image(0, 0, anchor="nw", image=self._diagram_image)

            # Hide the hint label
            self._diag_hint.configure(text="")
        except Exception as e:
            self._log(f"[GUI] Error mostrando diagrama: {e}\nRuta: {img_path}")

    def _on_canvas_scroll(self, event):
        if event.num == 4 or event.delta > 0:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self._canvas.yview_scroll(1, "units")

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state="disabled")
        widget.see(tk.END)

    def _log(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert(tk.END, msg + ("\n" if not msg.endswith("\n") else ""))
        self._log_text.configure(state="disabled")
        self._log_text.see(tk.END)

    def _log_clear(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()
