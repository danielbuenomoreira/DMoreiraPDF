import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import fitz
import os
import threading
from tkinterdnd2 import DND_FILES
from pdf_motor import PDFMotor


class AbaDividir:
    def __init__(self, parent, root):
        self.root = root
        self.container = tb.Frame(parent)
        parent.add(self.container, text="Extrair e dividir páginas")

        self.arquivo_origem = ""
        self.total_paginas = 0
        self.pasta_saida = ""
        self.var_modo = tb.StringVar(value="iguais")
        self.var_compressao = tb.BooleanVar()
        self.partes_personalizadas = []

        self._construir_ui()

        # Escuta eventos de troca de tema para atualizar componentes nativos
        self.root.bind("<<ThemeChanged>>", self._atualizar_cores_tema, add="+")
        self._atualizar_cores_tema()

    def _construir_ui(self):
        frame = tb.Frame(self.container, padding=30)
        frame.pack(fill=BOTH, expand=True)

        f_in = ttk.LabelFrame(frame, text="PDF Original (arraste ou solte)")
        f_in.pack(fill=X, pady=10)
        f_in_int = tb.Frame(f_in)
        f_in_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        f_in_int.drop_target_register(DND_FILES)
        f_in_int.dnd_bind('<<Drop>>', self.drop)
        tb.Button(f_in_int, text="Selecionar PDF", command=self.selecionar, bootstyle="primary").pack(anchor=W)
        self.lbl_arq = tb.Label(f_in_int, text="Nenhum arquivo selecionado.", bootstyle="secondary")
        self.lbl_arq.pack(anchor=W, pady=5)

        f_modo = ttk.LabelFrame(frame, text="Método de particionamento")
        f_modo.pack(fill=BOTH, expand=True, pady=10)
        f_modo_int = tb.Frame(f_modo)
        f_modo_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        f_modo_ig = tb.Frame(f_modo_int)
        f_modo_ig.grid(row=0, column=0, sticky=W, pady=5)
        tb.Radiobutton(f_modo_ig, text="Dividir em partes iguais. Quantidade de partes:", variable=self.var_modo, value="iguais",
                       command=self.mudar_modo, bootstyle="info").pack(side=LEFT)
        vcmd = (self.root.register(lambda P: str.isdigit(P) or P == ""), '%P')
        self.entry_iguais = tb.Entry(f_modo_ig, width=8, validate='all', validatecommand=vcmd)
        self.entry_iguais.pack(side=LEFT, padx=10)
        self.entry_iguais.insert(0, "2")
        self.entry_iguais.bind("<KeyRelease>", lambda e: self.validar())

        tb.Radiobutton(f_modo_int, text="Fila personalizada (Extrair páginas específicas)", variable=self.var_modo,
                       value="personalizado", command=self.mudar_modo, bootstyle="info").grid(row=1, column=0, sticky=W,
                                                                                              pady=(15, 5))

        self.f_pers = tb.Frame(f_modo_int)
        self.f_pers.grid(row=2, column=0, sticky=W)
        tb.Label(self.f_pers, text="Páginas (ex: 1-5, 8):").pack(side=LEFT)
        self.ent_pers = tb.Entry(self.f_pers, width=25)
        self.ent_pers.pack(side=LEFT, padx=10)
        tb.Button(self.f_pers, text="Adicionar Parte", command=self.add_pers, bootstyle="secondary").pack(side=LEFT)

        self.lb_pers = tk.Listbox(f_modo_int, height=4, font=("Arial", 10), relief="flat")
        self.lb_pers.grid(row=3, column=0, sticky=W + E, pady=10)
        tb.Button(f_modo_int, text="Remover parte selecionada", command=self.rem_pers, bootstyle="danger-outline").grid(row=4,
                                                                                                                  column=0,
                                                                                                                  sticky=W)

        f_out = ttk.LabelFrame(frame, text="Configuração de Saída")
        f_out.pack(fill=X, pady=10)
        f_out_int = tb.Frame(f_out)
        f_out_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        f_out_top = tb.Frame(f_out_int)
        f_out_top.pack(fill=X, pady=5)
        tb.Button(f_out_top, text="Escolher pasta destino", command=self.escolher_destino, bootstyle="dark").pack(side=LEFT)
        self.lbl_destino = tb.Label(f_out_top, text="Nenhuma pasta selecionada.", bootstyle="secondary")
        self.lbl_destino.pack(side=LEFT, padx=10)

        f_out_mid = tb.Frame(f_out_int)
        f_out_mid.pack(fill=X, pady=10)
        tb.Label(f_out_mid, text="Nome Base dos arquivos gerados:").pack(side=LEFT)
        self.entry_nome = tb.Entry(f_out_mid, width=40)
        self.entry_nome.pack(side=LEFT, padx=10)
        self.entry_nome.bind("<KeyRelease>", lambda e: self.validar())

        tb.Checkbutton(f_out_int, text="Máxima compressão (Aplica Ghostscript para redução severa)", variable=self.var_compressao,
                       bootstyle="danger-round-toggle").pack(anchor=W, pady=5)

        self.btn_executar = tb.Button(frame, text="Extrair e Dividir", command=self.executar, state=DISABLED,
                                      bootstyle="primary")
        self.btn_executar.pack(fill=X, pady=10)
        self.mudar_modo()

    def _atualizar_cores_tema(self, event=None):
        """Aplica as cores do tema ativo do ttkbootstrap ao Listbox nativo."""
        colors = tb.Style().colors
        self.lb_pers.config(
            bg=colors.inputbg,
            fg=colors.inputfg,
            selectbackground=colors.selectbg,
            selectforeground=colors.selectfg,
            highlightbackground=colors.border,
            highlightcolor=colors.primary
        )

    def mudar_modo(self):
        if self.var_modo.get() == "iguais":
            self.entry_iguais.config(state=NORMAL)
            for w in self.f_pers.winfo_children(): w.config(state=DISABLED)
        else:
            self.entry_iguais.config(state=NORMAL)
            for w in self.f_pers.winfo_children(): w.config(state=NORMAL)
        self.validar()

    def add_pers(self):
        v = self.ent_pers.get().strip()
        if v:
            self.partes_personalizadas.append(v)
            self.lb_pers.insert(tk.END, f"Parte {len(self.partes_personalizadas)}: {v}")
            self.ent_pers.delete(0, tk.END)
            self.validar()

    def rem_pers(self):
        s = self.lb_pers.curselection()
        if s:
            self.lb_pers.delete(s[0])
            self.partes_personalizadas.pop(s[0])
            self.lb_pers.delete(0, tk.END)
            for i, p in enumerate(self.partes_personalizadas):
                self.lb_pers.insert(tk.END, f"Parte {i + 1}: {p}")
            self.validar()

    def drop(self, event):
        a = self.root.tk.splitlist(event.data)
        if a and a[0].lower().endswith(".pdf"): self._processar_pdf(a[0])

    def selecionar(self):
        a = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if a: self._processar_pdf(a)

    def _processar_pdf(self, caminho):
        self.arquivo_origem = os.path.normpath(caminho)
        try:
            doc = PDFMotor.abrir_pdf_ram(self.arquivo_origem)
            self.total_paginas = doc.page_count
            doc.close()
            nome = os.path.basename(self.arquivo_origem)
            self.lbl_arq.config(text=f"{nome} ({self.total_paginas} págs)", bootstyle="dark")
            self.entry_nome.delete(0, tk.END)
            self.entry_nome.insert(0, os.path.splitext(nome)[0])
        except Exception as e:
            self.arquivo_origem = ""
            self.lbl_arq.config(text="Erro ao ler PDF.", bootstyle="danger")
        self.validar()

    def escolher_destino(self):
        p = filedialog.askdirectory()
        if p:
            self.pasta_saida = os.path.normpath(p)
            self.lbl_destino.config(text=self.pasta_saida, bootstyle="dark")
            self.validar()

    def validar(self):
        v = bool(self.arquivo_origem and self.pasta_saida and self.entry_nome.get().strip())
        if self.var_modo.get() == "iguais" and (
                not self.entry_iguais.get() or int(self.entry_iguais.get()) < 1): v = False
        if self.var_modo.get() == "personalizado" and not self.partes_personalizadas: v = False
        self.btn_executar.config(state=NORMAL if v else DISABLED)

    def executar(self):
        self.btn_executar.config(state=DISABLED, text="Processando...")
        threading.Thread(target=self._thread_dividir, daemon=True).start()

    def _thread_dividir(self):
        try:
            total = self.total_paginas
            nome_base = self.entry_nome.get().strip()
            pts = []

            if self.var_modo.get() == "iguais":
                qtd = int(self.entry_iguais.get())
                b, r = total // qtd, total % qtd
                inicio = 1
                for i in range(qtd):
                    fim = inicio + b + (1 if i < r else 0) - 1
                    pts.append(f"{inicio}-{fim}")
                    inicio = fim + 1
            else:
                pts = self.partes_personalizadas

            for idx, p in enumerate(pts, 1):
                paginas = set()
                for pedaco in p.split(','):
                    pedaco = pedaco.strip()
                    if '-' in pedaco:
                        i, f = map(int, pedaco.split('-'))
                        paginas.update(range(i - 1, f))
                    else:
                        paginas.add(int(pedaco) - 1)

                indices = sorted(list(paginas))

                doc_temp = PDFMotor.abrir_pdf_ram(self.arquivo_origem)
                doc_temp.select(indices)
                doc_saida = fitz.open()
                doc_saida.insert_pdf(doc_temp)
                doc_temp.close()

                PDFMotor.sanitizar(doc_saida)
                caminho = os.path.join(self.pasta_saida, f"{nome_base}_Parte{idx}.pdf")
                PDFMotor.salvar_e_comprimir(doc_saida, caminho, self.var_compressao.get())

            self.root.after(0, self._sucesso)
        except Exception as e:
            self.root.after(0, self._erro, str(e))

    def _sucesso(self):
        messagebox.showinfo("Sucesso", "Divisão concluída com segurança!")
        self.btn_executar.config(text="Extrair e Dividir", state=NORMAL)

    def _erro(self, msg):
        messagebox.showerror("Erro", msg)
        self.btn_executar.config(text="Extrair e Dividir", state=NORMAL)
