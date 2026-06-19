import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import fitz
import os
import threading
from pdf_motor import PDFMotor


class AbaLotes:
    def __init__(self, parent, root):
        self.root = root
        self.container = tb.Frame(parent)
        parent.add(self.container, text="Mesclar em lotes")

        self.entrada = ""
        self.saida = ""
        self.var_modo = tb.StringVar(value="quantidade")
        self.var_comp = tb.BooleanVar()

        self._construir_ui()

    def _construir_ui(self):
        f = tb.Frame(self.container, padding=40)
        f.pack(fill=BOTH, expand=True)

        f_in = ttk.LabelFrame(f, text="Pasta Origem")
        f_in.pack(fill=X, pady=10)
        f_in_int = tb.Frame(f_in)
        f_in_int.pack(fill=BOTH, expand=True, padx=15, pady=15)
        tb.Button(f_in_int, text="Selecionar pasta de origem", command=self.sel_in, bootstyle="primary-outline").pack(anchor=W)
        self.lbl_in = tb.Label(f_in_int, text="Nenhuma pasta selecionada.", bootstyle="secondary")
        self.lbl_in.pack(anchor=W, pady=5)

        f_out = ttk.LabelFrame(f, text="Pasta Destino")
        f_out.pack(fill=X, pady=10)
        f_out_int = tb.Frame(f_out)
        f_out_int.pack(fill=BOTH, expand=True, padx=15, pady=15)
        tb.Button(f_out_int, text="Selecionar pasta para salvar", command=self.sel_out, bootstyle="primary-outline").pack(anchor=W)
        self.lbl_out = tb.Label(f_out_int, text="Nenhuma pasta selecionada.", bootstyle="secondary")
        self.lbl_out.pack(anchor=W, pady=5)

        f_cfg = ttk.LabelFrame(f, text="Configuração de agrupamento")
        f_cfg.pack(fill=X, pady=10)
        f_cfg_int = tb.Frame(f_cfg)
        f_cfg_int.pack(fill=BOTH, expand=True, padx=15, pady=15)

        tb.Label(f_cfg_int, text="Nome Base (opcional):").grid(row=0, column=0, sticky=W, pady=5)
        self.ent_nome = tb.Entry(f_cfg_int, width=40)
        self.ent_nome.grid(row=0, column=1, sticky=W, padx=10, pady=5)

        f_radios = tb.Frame(f_cfg_int)
        f_radios.grid(row=1, column=1, sticky=W, padx=10, pady=5)
        tb.Radiobutton(f_radios, text="Quantidade de Arquivos", variable=self.var_modo, value="quantidade",
                       bootstyle="info").pack(side=LEFT, padx=(0, 15))
        tb.Radiobutton(f_radios, text="Tamanho máximo (MB)", variable=self.var_modo, value="tamanho", bootstyle="info").pack(
            side=LEFT)

        tb.Label(f_cfg_int, text="Valor Limite:").grid(row=2, column=0, sticky=W, pady=5)
        self.ent_limite = tb.Entry(f_cfg_int, width=15)
        self.ent_limite.insert(0, "20")
        self.ent_limite.grid(row=2, column=1, sticky=W, padx=10, pady=5)
        self.ent_limite.bind("<KeyRelease>", lambda e: self.validar())

        tb.Checkbutton(f_cfg_int, text="Máxima compressão (Aplica Ghostscript para redução severa)", variable=self.var_comp,
                       bootstyle="danger-round-toggle").grid(row=3, column=0, columnspan=2, sticky=W, pady=10)

        self.barra = tb.Progressbar(f, bootstyle="success-striped", maximum=100)
        self.barra.pack(fill=X, pady=(20, 5))
        self.lbl_status = tb.Label(f, text="", bootstyle="secondary")
        self.lbl_status.pack()

        self.btn = tb.Button(f, text="Processar Lotes", command=self.executar, state=DISABLED, bootstyle="info",
                             width=30)
        self.btn.pack(fill=X, pady=15)

    def sel_in(self):
        p = filedialog.askdirectory()
        if p:
            self.entrada = p
            self.lbl_in.config(text=p, bootstyle="dark")
            self.validar()

    def sel_out(self):
        p = filedialog.askdirectory()
        if p:
            self.saida = p
            self.lbl_out.config(text=p, bootstyle="dark")
            self.validar()

    def validar(self):
        v = bool(self.entrada and self.saida and self.ent_limite.get().strip())
        self.btn.config(state=NORMAL if v else DISABLED)

    def executar(self):
        self.btn.config(state=DISABLED, text="Processando...")
        self.barra["value"] = 0
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        try:
            seguro_in = PDFMotor.obter_caminho_seguro(self.entrada)
            arquivos = [f for f in os.listdir(seguro_in) if f.lower().endswith('.pdf')]
            arquivos.sort()

            if not arquivos:
                self.root.after(0, self._erro, "Nenhum PDF encontrado na origem.")
                return

            limite = float(self.ent_limite.get())
            base = self.ent_nome.get().strip() or os.path.basename(self.entrada)

            lotes = []
            if self.var_modo.get() == "quantidade":
                l = int(limite)
                lotes = [arquivos[i:i + l] for i in range(0, len(arquivos), l)]
            else:
                lim_b = limite * 1024 * 1024
                lote, tam = [], 0
                for a in arquivos:
                    t = os.path.getsize(os.path.join(seguro_in, a))
                    if tam + t > lim_b and lote:
                        lotes.append(lote)
                        lote, tam = [a], t
                    else:
                        lote.append(a)
                        tam += t
                if lote: lotes.append(lote)

            proc = 0
            for idx, lote in enumerate(lotes, 1):
                doc_saida = fitz.open()
                for a in lote:
                    proc += 1
                    self.root.after(0, self.atualizar_progresso, (proc / len(arquivos)) * 100, f"Processando: {a}")

                    doc_temp = PDFMotor.abrir_pdf_ram(os.path.join(seguro_in, a))
                    doc_saida.insert_pdf(doc_temp)
                    doc_temp.close()

                PDFMotor.sanitizar(doc_saida)
                caminho = os.path.join(self.saida, f"{base}_Parte_{idx}.pdf")
                PDFMotor.salvar_e_comprimir(doc_saida, caminho, self.var_comp.get())

            self.root.after(0, self._sucesso, len(arquivos), len(lotes))
        except Exception as e:
            self.root.after(0, self._erro, str(e))

    def atualizar_progresso(self, val, texto):
        self.barra["value"] = val
        self.lbl_status.config(text=texto)

    def _sucesso(self, t_arq, t_lote):
        messagebox.showinfo("Concluído", f"{t_arq} arquivos processados em {t_lote} PDFs.")
        self.btn.config(state=NORMAL, text="Processar Lotes")
        self.atualizar_progresso(0, "")

    def _erro(self, msg):
        messagebox.showerror("Erro", msg)
        self.btn.config(state=NORMAL, text="Processar Lotes")
        self.atualizar_progresso(0, "")
