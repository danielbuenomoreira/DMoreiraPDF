import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import fitz
import os
import threading
from pdf_motor import PDFMotor


class AbaRenomear:
    def __init__(self, parent, root):
        self.root = root
        self.container = tb.Frame(parent)
        parent.add(self.container, text="Higienizador / renomeador")

        self.origem = ""
        self.destino = ""
        self.var_sub = tb.BooleanVar(value=True)
        self.var_unificado = tb.BooleanVar(value=False)

        self._construir_ui()

    def _construir_ui(self):
        f = tb.Frame(self.container, padding=40)
        f.pack(fill=BOTH, expand=True)

        tb.Label(f, text="Higienização e formatação de nomes", font=("Arial", 15, "bold")).pack(pady=5)
        tb.Label(f, text="Remove acentos, caracteres especiais e travas de segurança (IRM/Assinaturas).", bootstyle="info").pack(pady=5)

        f_in = ttk.LabelFrame(f, text="Selecione a pasta de origem")
        f_in.pack(fill=X, pady=15)
        f_in_int = tb.Frame(f_in)
        f_in_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        tb.Button(f_in_int, text="Selecionar pasta", command=self.sel_in, bootstyle="primary-outline").pack(anchor=W)
        self.lbl_in = tb.Label(f_in_int, text="Nenhuma pasta selecionada.", bootstyle="secondary")
        self.lbl_in.pack(anchor=W, pady=5)

        tb.Checkbutton(f, text="Incluir processamento de subpastas", variable=self.var_sub, bootstyle="info-round-toggle").pack(
            anchor=W, pady=5)
        tb.Checkbutton(f, text="Ativar exportação unificada (prefixos nível 1 e 2)", variable=self.var_unificado,
                       command=self.toggle_modo, bootstyle="success-round-toggle").pack(anchor=W, pady=15)

        self.f_out = ttk.LabelFrame(f, text="Selecionar pasta destino (Obrigatório para unificada)")
        self.f_out.pack(fill=X, pady=10)
        self.f_out_int = tb.Frame(self.f_out)
        self.f_out_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        self.btn_out = tb.Button(self.f_out_int, text="Selecionar pasta destino", command=self.sel_out, state=DISABLED,
                                 bootstyle="success")
        self.btn_out.pack(anchor=W)
        self.lbl_out = tb.Label(self.f_out_int, text="Requer ativação da exportação unificada.", bootstyle="secondary")
        self.lbl_out.pack(anchor=W, pady=5)

        self.btn = tb.Button(f, text="Higienizar e Sobrescrever Originais", command=self.executar, state=DISABLED,
                             bootstyle="danger", width=40)
        self.btn.pack(fill=X, pady=30)

    def sel_in(self):
        p = filedialog.askdirectory()
        if p:
            self.origem = p
            self.lbl_in.config(text=p, bootstyle="dark")
            self.validar()

    def sel_out(self):
        p = filedialog.askdirectory()
        if p:
            self.destino = p
            self.lbl_out.config(text=p, bootstyle="dark")
            self.validar()

    def toggle_modo(self):
        if self.var_unificado.get():
            self.btn_out.config(state=NORMAL)
            self.lbl_out.config(text=self.destino if self.destino else "Nenhuma pasta selecionada.")
            self.btn.config(text="Higienizar e Exportar para Destino", bootstyle="success")
        else:
            self.btn_out.config(state=DISABLED)
            self.lbl_out.config(text="Requer modo unificado.", bootstyle="secondary")
            self.btn.config(text="Higienizar e Sobrescrever Originais", bootstyle="danger")
        self.validar()

    def validar(self):
        v = False
        if self.origem:
            if self.var_unificado.get():
                v = bool(self.destino)
            else:
                v = True
        self.btn.config(state=NORMAL if v else DISABLED)

    def _nome_unico(self, caminho_base):
        seguro = PDFMotor.obter_caminho_seguro(caminho_base)
        if not os.path.exists(seguro): return caminho_base
        d, a = os.path.split(caminho_base)
        n, e = os.path.splitext(a)
        c = 2
        while True:
            novo = os.path.join(d, f"{n} {c:02d}{e}")
            if not os.path.exists(PDFMotor.obter_caminho_seguro(novo)): return novo
            c += 1

    def executar(self):
        if not self.var_unificado.get():
            if not messagebox.askyesno("Aviso Crítico", "Isso SOBRESCREVERÁ os PDFs originais. Tem certeza?"): return
        self.btn.config(state=DISABLED, text="Processando...")
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        try:
            proc = 0
            seguro_in = PDFMotor.obter_caminho_seguro(self.origem)

            for d, sd, arqs in os.walk(seguro_in):
                pdfs = [f for f in arqs if f.lower().endswith('.pdf') and not f.startswith('.tmp')]
                for a in pdfs:
                    origem_arq = os.path.join(d, a)
                    nome_limpo = PDFMotor.formatar_nome(os.path.splitext(a)[0])
                    ext = os.path.splitext(a)[1]

                    if self.var_unificado.get():
                        rel = os.path.relpath(d, seguro_in)
                        prefs = [PDFMotor.formatar_nome(p) for p in rel.split(os.sep)[:2]] if rel != '.' else []
                        n_final = " ".join(prefs + [nome_limpo]) + ext
                        dest = self._nome_unico(os.path.join(self.destino, n_final))

                        doc = PDFMotor.abrir_pdf_ram(origem_arq)
                        doc_s = fitz.open()
                        doc_s.insert_pdf(doc)
                        doc.close()
                        PDFMotor.sanitizar(doc_s)
                        PDFMotor.salvar_e_comprimir(doc_s, dest, False)
                    else:
                        n_final = f"{nome_limpo}{ext}"
                        dest = os.path.join(d, n_final)
                        tmp = origem_arq + ".tmp.pdf"

                        doc = PDFMotor.abrir_pdf_ram(origem_arq)
                        doc_s = fitz.open()
                        doc_s.insert_pdf(doc)
                        doc.close()
                        PDFMotor.sanitizar(doc_s)
                        PDFMotor.salvar_e_comprimir(doc_s, tmp, False)

                        os.remove(PDFMotor.obter_caminho_seguro(origem_arq))
                        os.replace(PDFMotor.obter_caminho_seguro(tmp), PDFMotor.obter_caminho_seguro(dest))
                    proc += 1
                if not self.var_sub.get(): break

            self.root.after(0, self._sucesso, proc)
        except Exception as e:
            self.root.after(0, self._erro, str(e))

    def _sucesso(self, p):
        messagebox.showinfo("Concluído", f"{p} arquivos processados.")
        self.toggle_modo()

    def _erro(self, msg):
        messagebox.showerror("Erro", msg)
        self.toggle_modo()
