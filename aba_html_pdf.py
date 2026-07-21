import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
import threading
import subprocess
from tkinterdnd2 import DND_FILES
from pdf_motor import PDFMotor


class AbaHtmlPdf:
    def __init__(self, parent, root):
        self.root = root
        self.container = tb.Frame(parent)
        parent.add(self.container, text="Converter HTML para PDF")

        self.arquivos_html = []
        self.pasta_saida = ""

        self._construir_ui()

        # Escuta eventos de troca de tema para atualizar componentes nativos
        self.root.bind("<<ThemeChanged>>", self._atualizar_cores_tema, add="+")
        self._atualizar_cores_tema()

    def _construir_ui(self):
        frame = tb.Frame(self.container, padding=30)
        frame.pack(fill=BOTH, expand=True)

        tb.Label(frame, text="Arraste os arquivos .html abaixo ou adicione por arquivos/pasta",
                 font=("Arial", 12)).pack(pady=5)

        self.listbox = tk.Listbox(frame, selectmode=tk.SINGLE, font=("Arial", 11), relief="flat", highlightthickness=1)
        self.listbox.pack(fill=BOTH, expand=True, pady=5)
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind('<<Drop>>', self.drop)

        f_ctrl = tb.Frame(frame)
        f_ctrl.pack(fill=X, pady=15)
        tb.Button(f_ctrl, text="Adicionar Arquivos", command=self.adicionar_arquivos, bootstyle="primary").pack(
            side=LEFT, padx=5)
        tb.Button(f_ctrl, text="Adicionar Pasta Inteira", command=self.adicionar_pasta, bootstyle="info").pack(
            side=LEFT, padx=5)
        tb.Button(f_ctrl, text="Remover selecionado", command=self.remover, bootstyle="danger-outline").pack(side=LEFT,
                                                                                                             padx=5)
        tb.Button(f_ctrl, text="Limpar Lista", command=self.limpar_lista, bootstyle="secondary").pack(side=RIGHT,
                                                                                                      padx=5)

        f_saida = ttk.LabelFrame(frame, text="Configuração de Saída")
        f_saida.pack(fill=X, pady=10)

        f_saida_interno = tb.Frame(f_saida)
        f_saida_interno.pack(fill=BOTH, expand=True, padx=15, pady=15)

        tb.Button(f_saida_interno, text="Escolher pasta de destino", command=self.escolher_destino,
                  bootstyle="info").pack(anchor=W)
        self.lbl_destino = tb.Label(f_saida_interno, text="Nenhuma pasta selecionada.", bootstyle="secondary")
        self.lbl_destino.pack(anchor=W, pady=5)

        self.barra = tb.Progressbar(frame, bootstyle="success-striped", maximum=100)
        self.barra.pack(fill=X, pady=(15, 5))
        self.lbl_status = tb.Label(frame, text="", bootstyle="secondary")
        self.lbl_status.pack()

        self.btn_executar = tb.Button(frame, text="Converter para PDF", command=self.executar, state=DISABLED,
                                      bootstyle="success")
        self.btn_executar.pack(fill=X, pady=10)

    def _atualizar_cores_tema(self, event=None):
        """Aplica as cores do tema ativo do ttkbootstrap ao Listbox nativo."""
        colors = tb.Style().colors
        self.listbox.config(
            bg=colors.inputbg,
            fg=colors.inputfg,
            selectbackground=colors.selectbg,
            selectforeground=colors.selectfg,
            highlightbackground=colors.border,
            highlightcolor=colors.primary
        )

    def drop(self, event):
        self._inserir_arquivos(self.root.tk.splitlist(event.data))

    def adicionar_arquivos(self):
        self._inserir_arquivos(filedialog.askopenfilenames(filetypes=[("Arquivos HTML", "*.html *.htm")]))

    def adicionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta com os arquivos HTML")
        if pasta:
            arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(('.html', '.htm'))]
            self._inserir_arquivos(arquivos)

    def _inserir_arquivos(self, arquivos):
        for arq in arquivos:
            limpo = os.path.normpath(arq)
            if limpo.lower().endswith(('.html', '.htm')) and limpo not in self.arquivos_html:
                self.arquivos_html.append(limpo)
                self.listbox.insert(tk.END, os.path.basename(limpo))
        self.validar()

    def remover(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            self.arquivos_html.pop(sel[0])
            self.validar()

    def limpar_lista(self):
        self.listbox.delete(0, tk.END)
        self.arquivos_html.clear()
        self.validar()

    def escolher_destino(self):
        pasta = filedialog.askdirectory(title="Selecione onde salvar os PDFs")
        if pasta:
            self.pasta_saida = os.path.normpath(pasta)
            self.lbl_destino.config(text=self.pasta_saida, bootstyle="dark")
            self.validar()

    def validar(self):
        v = bool(self.arquivos_html and self.pasta_saida)
        self.btn_executar.config(state=NORMAL if v else DISABLED)

    def _encontrar_navegador(self):
        """Busca o executável do Edge ou Chrome no sistema para usar como motor de conversão."""
        caminhos = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for c in caminhos:
            if os.path.exists(c):
                return c
        return None

    def executar(self):
        self.btn_executar.config(state=DISABLED, text="Convertendo...")
        self.barra["value"] = 0
        threading.Thread(target=self._thread_converter, daemon=True).start()

    def _thread_converter(self):
        navegador = self._encontrar_navegador()
        if not navegador:
            self.root.after(0, self._erro,
                            "Nenhum navegador compatível (Microsoft Edge ou Google Chrome) foi encontrado nos caminhos padrão. A conversão requer um desses instalados.")
            return

        total = len(self.arquivos_html)
        try:
            for idx, arq_html in enumerate(self.arquivos_html, 1):
                nome_base = os.path.splitext(os.path.basename(arq_html))[0]
                arq_pdf_saida = os.path.join(self.pasta_saida, f"{nome_base}.pdf")

                # Previne o bug do MAX_PATH convertendo para formato 8.3 se necessário
                arq_html_seguro = PDFMotor.obter_caminho_seguro(arq_html)
                arq_pdf_seguro = PDFMotor.obter_caminho_seguro(arq_pdf_saida)

                self.root.after(0, self.atualizar_progresso, (idx / total) * 100, f"Convertendo: {nome_base}.html")

                comando = [
                    navegador,
                    "--headless",
                    "--disable-gpu",
                    "--run-all-compositor-stages-before-draw",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={arq_pdf_seguro}",
                    arq_html_seguro
                ]

                # Executa o comando em background sem abrir janela (creationflags=0x08000000)
                subprocess.run(comando, check=True, creationflags=0x08000000)

            self.root.after(0, self._sucesso)
        except subprocess.CalledProcessError as e:
            self.root.after(0, self._erro, f"Falha ao executar o motor do navegador.\nDetalhes: {e}")
        except Exception as e:
            self.root.after(0, self._erro, f"Erro inesperado: {str(e)}")

    def atualizar_progresso(self, val, texto):
        self.barra["value"] = val
        self.lbl_status.config(text=texto)

    def _sucesso(self):
        messagebox.showinfo("Concluído", f"Conversão de {len(self.arquivos_html)} arquivo(s) finalizada com sucesso!")
        self.limpar_lista()
        self.btn_executar.config(text="Converter para PDF", state=DISABLED)
        self.atualizar_progresso(0, "")

    def _erro(self, msg):
        messagebox.showerror("Erro na Conversão", msg)
        self.btn_executar.config(text="Converter para PDF", state=NORMAL)
        self.atualizar_progresso(0, "")
