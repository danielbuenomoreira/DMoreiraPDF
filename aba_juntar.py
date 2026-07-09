import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import fitz
import os
import threading
from tkinterdnd2 import DND_FILES
from pdf_motor import PDFMotor


class AbaJuntar:
    def __init__(self, parent, root):
        self.root = root
        self.container = tb.Frame(parent)
        parent.add(self.container, text="Juntar e otimizar")

        self.arquivos = []
        self.saida = ""
        self.var_compressao = tb.BooleanVar()

        self._construir_ui()

    def _construir_ui(self):
        frame = tb.Frame(self.container, padding=30)
        frame.pack(fill=BOTH, expand=True)

        tb.Label(frame, text="Arraste os PDFs abaixo ou use os botões", font=("Arial", 12)).pack(pady=5)

        self.listbox = tk.Listbox(frame, selectmode=tk.SINGLE, font=("Arial", 11), relief="flat", highlightthickness=1)
        self.listbox.pack(fill=BOTH, expand=True, pady=5)
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind('<<Drop>>', self.drop)

        f_ctrl = tb.Frame(frame)
        f_ctrl.pack(fill=X, pady=15)
        tb.Button(f_ctrl, text="Adicionar arquivos", command=self.adicionar, bootstyle="primary").pack(side=LEFT, padx=5)
        tb.Button(f_ctrl, text="Remover selecionado", command=self.remover, bootstyle="danger-outline").pack(side=LEFT, padx=5)
        tb.Button(f_ctrl, text="Mover para cima", command=self.mover_cima, bootstyle="secondary").pack(side=RIGHT, padx=5)
        tb.Button(f_ctrl, text="Mover para baixo", command=self.mover_baixo, bootstyle="secondary").pack(side=RIGHT, padx=5)

        tb.Checkbutton(frame, text="Máxima compressão (Aplica Ghostscript para redução severa)", variable=self.var_compressao,
                       bootstyle="danger-round-toggle").pack(anchor=W, pady=10)

        # Usando o ttk nativo para evitar o bug de compatibilidade
        f_saida = ttk.LabelFrame(frame, text="Configuração de Saída")
        f_saida.pack(fill=X, pady=10)

        f_saida_interno = tb.Frame(f_saida)
        f_saida_interno.pack(fill=BOTH, expand=True, padx=15, pady=15)

        tb.Button(f_saida_interno, text="Escolher pasta de destino e nome", command=self.escolher_destino, bootstyle="info").pack(
            anchor=W)
        self.lbl_destino = tb.Label(f_saida_interno, text="Nenhum destino selecionado.", bootstyle="secondary")
        self.lbl_destino.pack(anchor=W, pady=5)

        self.btn_executar = tb.Button(frame, text="Processar PDFs", command=self.executar, state=DISABLED,
                                      bootstyle="success")
        self.btn_executar.pack(fill=X, pady=20)

    def drop(self, event):
        self._inserir_arquivos(self.root.tk.splitlist(event.data))

    def adicionar(self):
        self._inserir_arquivos(filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")]))

    def _inserir_arquivos(self, arquivos):
        for arq in arquivos:
            limpo = os.path.normpath(arq)
            if limpo.lower().endswith(".pdf") and limpo not in self.arquivos:
                self.arquivos.append(limpo)
                self.listbox.insert(tk.END, os.path.basename(limpo))
        self.validar()

    def remover(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            self.arquivos.pop(sel[0])
            self.validar()

    def mover_cima(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0: return
        idx = sel[0]
        self.arquivos[idx - 1], self.arquivos[idx] = self.arquivos[idx], self.arquivos[idx - 1]
        t = self.listbox.get(idx)
        self.listbox.delete(idx)
        self.listbox.insert(idx - 1, t)
        self.listbox.selection_set(idx - 1)

    def mover_baixo(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == len(self.arquivos) - 1: return
        idx = sel[0]
        self.arquivos[idx + 1], self.arquivos[idx] = self.arquivos[idx], self.arquivos[idx + 1]
        t = self.listbox.get(idx)
        self.listbox.delete(idx)
        self.listbox.insert(idx + 1, t)
        self.listbox.selection_set(idx + 1)

    def escolher_destino(self):
        arq = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if arq:
            self.saida = arq
            self.lbl_destino.config(text=self.saida, bootstyle="dark")
            self.validar()

    def validar(self):
        self.btn_executar.config(state=NORMAL if (self.arquivos and self.saida) else DISABLED)

    def executar(self):
        self.btn_executar.config(state=DISABLED, text="Processando...")
        threading.Thread(target=self._thread_juntar, daemon=True).start()

    def _thread_juntar(self):
        try:
            doc_saida = fitz.open()
            for arq in self.arquivos:
                doc_temp = PDFMotor.abrir_pdf_ram(arq)
                doc_saida.insert_pdf(doc_temp)
                doc_temp.close()

            PDFMotor.sanitizar(doc_saida)
            PDFMotor.salvar_e_comprimir(doc_saida, self.saida, self.var_compressao.get())

            self.root.after(0, self._sucesso, "PDFs unidos e higienizados com sucesso!")
        except Exception as e:
            self.root.after(0, self._erro, str(e))

    def _sucesso(self, msg):
        messagebox.showinfo("Concluído", msg)
        self.arquivos.clear()
        self.listbox.delete(0, tk.END)
        self.saida = ""
        self.lbl_destino.config(text="Nenhum selecionado.", bootstyle="secondary")
        self.validar()
        self.btn_executar.config(text="Processar PDFs", bootstyle="success")

    def _erro(self, msg):
        messagebox.showerror("Erro", msg)
        self.btn_executar.config(text="Processar PDFs", state=NORMAL)
