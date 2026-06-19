import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz  # PyMuPDF
import webbrowser
import os
import threading
import sys
import unicodedata
import re
import subprocess
import ctypes

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    raise ImportError("A biblioteca tkinterdnd2 é necessária. Instale executando: pip install tkinterdnd2")


def resource_path(relative_path):
    """Permite localizar arquivos embutidos pelo PyInstaller na pasta temporária _MEIPASS"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class OtimizadorPDFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DMoreiraPDF - Ferramenta de Manipulação v3.5")

        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)

        self.root.resizable(True, True)

        try:
            self.root.iconbitmap(resource_path("DMoreiraPDF.ico"))
        except:
            pass

        # Variáveis Juntar
        self.arquivos_juntar = []
        self.saida_juntar = ""
        self.var_compressao_maxima = tk.BooleanVar()

        # Variáveis Dividir/Extrair
        self.arquivo_dividir = ""
        self.total_paginas_dividir = 0
        self.saida_dividir_pasta = ""
        self.var_compressao_max_dividir = tk.BooleanVar()

        # Variáveis Lote
        self.pasta_entrada_lote = ""
        self.pasta_saida_lote = ""
        self.var_modo_lote = tk.StringVar(value="quantidade")
        self.var_compressao_max_lote = tk.BooleanVar()

        # Variáveis Renomear
        self.pasta_renomear = ""
        self.var_incluir_subpastas = tk.BooleanVar()

        self.construir_interface()

    # ==========================================
    # BLINDAGEM DE SISTEMA: CAMINHOS E MEMÓRIA RAM
    # ==========================================
    def _obter_caminho_seguro(self, caminho):
        """Converte caminhos gigantes no formato curto 8.3 do Windows para burlar o erro MAX_PATH."""
        if not caminho: return caminho
        caminho_abs = os.path.abspath(caminho)
        if os.name != 'nt': return caminho_abs

        try:
            diretorio = os.path.dirname(caminho_abs)
            arquivo = os.path.basename(caminho_abs)
            dir_pref = '\\\\?\\' + diretorio if not diretorio.startswith('\\\\?\\') else diretorio

            tamanho = ctypes.windll.kernel32.GetShortPathNameW(dir_pref, None, 0)
            if tamanho > 0:
                buffer = ctypes.create_unicode_buffer(tamanho)
                ctypes.windll.kernel32.GetShortPathNameW(dir_pref, buffer, tamanho)
                dir_curto = buffer.value
                if dir_curto.startswith('\\\\?\\'):
                    dir_curto = dir_curto[4:]
                return os.path.join(dir_curto, arquivo)
        except:
            pass

        return '\\\\?\\' + caminho_abs if not caminho_abs.startswith('\\\\?\\') else caminho_abs

    def _abrir_pdf_seguro(self, caminho):
        """Lê o arquivo para a memória RAM. Resolve bugs do C, limites de nome e o erro 'Acesso Negado'."""
        caminho_seg = self._obter_caminho_seguro(caminho)
        with open(caminho_seg, "rb") as f:
            pdf_bytes = f.read()
        doc = fitz.open("pdf", pdf_bytes)
        if doc.is_encrypted:
            doc.authenticate("")
        return doc

    # ==========================================
    # NÚCLEO PADRÃO DE HIGIENIZAÇÃO E GHOSTSCRIPT
    # ==========================================
    def _sanitizar_documento(self, doc):
        """Extermina bloqueios IRM, painéis de segurança e achata assinaturas digitais."""
        try:
            cat = doc.pdf_catalog()
            doc.xref_set_key(cat, "AcroForm", "null")
            doc.xref_set_key(cat, "Perms", "null")
            doc.xref_set_key(cat, "Collection", "null")
            doc.xref_set_key(cat, "SigFlags", "null")
        except:
            pass

        for pagina in doc:
            for anotacao in pagina.annots():
                if anotacao.type[0] == fitz.PDF_ANNOT_WIDGET:
                    anotacao.set_flags(fitz.ANNOT_FLAG_PRINT | fitz.ANNOT_FLAG_LOCKED | fitz.ANNOT_FLAG_LOCKED_CONTENTS)
                    anotacao.update()

    def _comprimir_com_ghostscript(self, arquivo_entrada, arquivo_saida):
        """Invoca a engine Ghostscript para compressão extrema."""
        gs_exec = self._obter_caminho_seguro(resource_path("gswin64c.exe"))

        comando = [
            gs_exec,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={self._obter_caminho_seguro(arquivo_saida)}",
            self._obter_caminho_seguro(arquivo_entrada)
        ]

        try:
            subprocess.run(comando, check=True, creationflags=0x08000000)
            return True
        except Exception as e:
            raise RuntimeError(f"Falha no motor Ghostscript: {e}")

    def converter_string_paginas(self, texto, total_paginas):
        paginas = set()
        for parte in texto.split(','):
            parte = parte.strip()
            if not parte: continue
            if '-' in parte:
                limites = parte.split('-')
                if len(limites) != 2: raise ValueError(f"Intervalo inválido: {parte}")
                paginas.update(range(int(limites[0]) - 1, int(limites[1])))
            else:
                paginas.add(int(parte) - 1)

        resultado = sorted(list(paginas))
        if any(p < 0 or p >= total_paginas for p in resultado):
            raise ValueError("As páginas informadas não existem no documento original.")
        return resultado

    def construir_interface(self):
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Arial", 11, "bold"), padding=[10, 5])
        style.configure("TLabelframe.Label", font=("Arial", 10, "bold"))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)

        self.aba_juntar = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_juntar, text="Juntar e Otimizar")
        self.construir_aba_juntar()

        self.aba_dividir = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_dividir, text="Extrair e Dividir Páginas")
        self.construir_aba_dividir()

        self.aba_lotes = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_lotes, text="Mesclar em Lotes")
        self.construir_aba_lotes()

        self.aba_renomear = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_renomear, text="Renomear PDFs")
        self.construir_aba_renomear()

        frame_rodape = tk.Frame(self.root)
        frame_rodape.pack(side="bottom", pady=5)
        tk.Label(frame_rodape, text="Desenvolvido por ", font=("Arial", 10)).pack(side="left")
        lbl_link = tk.Label(frame_rodape, text="@danielbuenomoreiradev", fg="blue", cursor="hand2",
                            font=("Arial", 10, "bold"))
        lbl_link.pack(side="left")
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://danielbuenomoreira.github.io/QuemSouEu/"))

    # ==========================================
    # ABA 1: JUNTAR E OTIMIZAR
    # ==========================================
    def construir_aba_juntar(self):
        container = tk.Frame(self.aba_juntar)
        container.pack(fill="both", expand=True, padx=50, pady=20)

        tk.Label(container, text="Arraste os PDFs abaixo ou use os botões", font=("Arial", 12)).pack(pady=5)

        frame_lista = tk.Frame(container)
        frame_lista.pack(fill="both", expand=True, pady=5)

        self.listbox_juntar = tk.Listbox(frame_lista, selectmode=tk.SINGLE, font=("Arial", 11))
        self.listbox_juntar.pack(side="left", fill="both", expand=True)
        self.listbox_juntar.drop_target_register(DND_FILES)
        self.listbox_juntar.dnd_bind('<<Drop>>', self.drop_juntar)

        scrollbar = tk.Scrollbar(frame_lista, orient="vertical", command=self.listbox_juntar.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox_juntar.config(yscrollcommand=scrollbar.set)

        frame_controles = tk.Frame(container)
        frame_controles.pack(fill="x", pady=10)

        tk.Button(frame_controles, text="Adicionar Arquivos", command=self.selecionar_entrada_juntar,
                  font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(frame_controles, text="Remover Selecionado", command=self.remover_selecionado,
                  font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(frame_controles, text="Mover para Baixo", command=self.mover_baixo, font=("Arial", 10)).pack(
            side="right", padx=5)
        tk.Button(frame_controles, text="Mover para Cima", command=self.mover_cima, font=("Arial", 10)).pack(
            side="right", padx=5)

        frame_opcoes = tk.Frame(container)
        frame_opcoes.pack(fill="x", pady=10)
        tk.Checkbutton(frame_opcoes,
                       text="Máxima Compressão (Opcional: Aplica redução severa usando Ghostscript)",
                       variable=self.var_compressao_maxima, fg="red", font=("Arial", 10)).pack(anchor="w")

        frame_saida = tk.LabelFrame(container, text="Configuração de Saída", padx=15, pady=15)
        frame_saida.pack(fill="x", pady=10)

        tk.Button(frame_saida, text="Escolher Pasta de Destino e Nome", command=self.selecionar_saida_juntar,
                  font=("Arial", 10)).pack(anchor="w")
        self.lbl_destino_juntar = tk.Label(frame_saida, text="Nenhum destino selecionado.", fg="gray",
                                           font=("Arial", 10))
        self.lbl_destino_juntar.pack(anchor="w", pady=(10, 0))

        self.btn_processar_juntar = tk.Button(container, text="Processar PDFs", command=self.iniciar_thread_juntar,
                                              state=tk.DISABLED, bg="green", fg="white", font=("Arial", 12, "bold"),
                                              pady=10)
        self.btn_processar_juntar.pack(fill="x", pady=20)

    def drop_juntar(self, event):
        self.adicionar_arquivos_juntar(self.root.tk.splitlist(event.data))

    def selecionar_entrada_juntar(self):
        self.adicionar_arquivos_juntar(filedialog.askopenfilenames(title="Selecione", filetypes=[("PDF", "*.pdf")]))

    def adicionar_arquivos_juntar(self, arquivos):
        for arq in arquivos:
            arq_limpo = os.path.normpath(arq)
            if arq_limpo.lower().endswith(".pdf") and arq_limpo not in self.arquivos_juntar:
                self.arquivos_juntar.append(arq_limpo)
                self.listbox_juntar.insert(tk.END, os.path.basename(arq_limpo))
        self.verificar_estado_juntar()

    def remover_selecionado(self):
        selecionados = self.listbox_juntar.curselection()
        if selecionados:
            pos = selecionados[0]
            self.listbox_juntar.delete(pos)
            self.arquivos_juntar.pop(pos)
            self.verificar_estado_juntar()

    def mover_cima(self):
        selecionados = self.listbox_juntar.curselection()
        if not selecionados or selecionados[0] == 0: return
        pos = selecionados[0]
        self.arquivos_juntar[pos - 1], self.arquivos_juntar[pos] = self.arquivos_juntar[pos], self.arquivos_juntar[
            pos - 1]
        texto = self.listbox_juntar.get(pos)
        self.listbox_juntar.delete(pos)
        self.listbox_juntar.insert(pos - 1, texto)
        self.listbox_juntar.selection_set(pos - 1)

    def mover_baixo(self):
        selecionados = self.listbox_juntar.curselection()
        if not selecionados or selecionados[0] == len(self.arquivos_juntar) - 1: return
        pos = selecionados[0]
        self.arquivos_juntar[pos + 1], self.arquivos_juntar[pos] = self.arquivos_juntar[pos], self.arquivos_juntar[
            pos + 1]
        texto = self.listbox_juntar.get(pos)
        self.listbox_juntar.delete(pos)
        self.listbox_juntar.insert(pos + 1, texto)
        self.listbox_juntar.selection_set(pos + 1)

    def selecionar_saida_juntar(self):
        arquivo = filedialog.asksaveasfilename(title="Salvar como", defaultextension=".pdf",
                                               filetypes=[("PDF", "*.pdf")])
        if arquivo:
            self.saida_juntar = arquivo
            self.lbl_destino_juntar.config(text=f"Destino: {self.saida_juntar}", fg="black")
            self.verificar_estado_juntar()

    def verificar_estado_juntar(self):
        if self.arquivos_juntar and self.saida_juntar:
            self.btn_processar_juntar.config(state=tk.NORMAL)
        else:
            self.btn_processar_juntar.config(state=tk.DISABLED)

    def iniciar_thread_juntar(self):
        self.btn_processar_juntar.config(state=tk.DISABLED, text="Processando... Aguarde", bg="gray")
        threading.Thread(target=self._tarefa_processar_juntar, daemon=True).start()

    def _tarefa_processar_juntar(self):
        try:
            tamanho_original_bytes = sum(
                os.path.getsize(self._obter_caminho_seguro(arq)) for arq in self.arquivos_juntar)
            tamanho_original_mb = tamanho_original_bytes / (1024 * 1024)
            compressao_maxima = self.var_compressao_maxima.get()

            caminho_final = self._obter_caminho_seguro(self.saida_juntar)
            caminho_salvamento_limpo = self._obter_caminho_seguro(
                caminho_final + ".tmp.pdf") if compressao_maxima else caminho_final

            doc_saida = fitz.open()
            for arquivo in self.arquivos_juntar:
                # Abre direto na memória RAM
                doc_temp = self._abrir_pdf_seguro(arquivo)
                doc_saida.insert_pdf(doc_temp)
                doc_temp.close()

            # Sanitização (destrói catálogos e IRM)
            self._sanitizar_documento(doc_saida)

            try:
                doc_saida.save(caminho_salvamento_limpo, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
            except:
                doc_saida.save(caminho_salvamento_limpo, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
            doc_saida.close()

            if compressao_maxima:
                self._comprimir_com_ghostscript(caminho_salvamento_limpo, caminho_final)
                if os.path.exists(caminho_salvamento_limpo):
                    os.remove(caminho_salvamento_limpo)

            tamanho_final_bytes = os.path.getsize(caminho_final)
            tamanho_final_mb = tamanho_final_bytes / (1024 * 1024)

            mensagem_tamanho = (
                f"Processamento e limpeza de segurança concluídos!\n\n"
                f"Tamanho total original: {tamanho_original_mb:.2f} MB\n"
                f"Tamanho do PDF final: {tamanho_final_mb:.2f} MB"
            )

            self.root.after(0, self._finalizar_juntar, True, mensagem_tamanho)
        except Exception as e:
            self.root.after(0, self._finalizar_juntar, False, str(e))

    def _finalizar_juntar(self, sucesso, mensagem):
        self.btn_processar_juntar.config(state=tk.NORMAL, text="Processar PDFs", bg="green")
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            self.arquivos_juntar.clear()
            self.listbox_juntar.delete(0, tk.END)
            self.saida_juntar = ""
            self.lbl_destino_juntar.config(text="Nenhum destino selecionado.", fg="gray")
            self.var_compressao_maxima.set(False)
            self.verificar_estado_juntar()
        else:
            messagebox.showerror("Erro Técnico", f"Falha ao processar:\n{mensagem}")

    # ==========================================
    # ABA 2: EXTRAIR E DIVIDIR PÁGINAS
    # ==========================================
    def construir_aba_dividir(self):
        container = tk.Frame(self.aba_dividir)
        container.pack(fill="both", expand=True, padx=50, pady=10)

        frame_entrada = tk.LabelFrame(container, text="1. PDF Original (Arraste ou Selecione)", padx=15, pady=10)
        frame_entrada.pack(fill="x", pady=5)
        frame_entrada.drop_target_register(DND_FILES)
        frame_entrada.dnd_bind('<<Drop>>', self.drop_dividir)

        tk.Button(frame_entrada, text="Selecionar PDF", command=self.selecionar_entrada_dividir,
                  font=("Arial", 10)).pack(anchor="w")
        self.lbl_arquivo_dividir = tk.Label(frame_entrada, text="Nenhum arquivo selecionado.", fg="gray",
                                            font=("Arial", 10))
        self.lbl_arquivo_dividir.pack(anchor="w", pady=(5, 0))

        frame_modo = tk.LabelFrame(container, text="2. Método de Particionamento", padx=15, pady=10)
        frame_modo.pack(fill="both", expand=True, pady=5)

        self.var_modo_dividir = tk.StringVar(value="iguais")

        frame_iguais = tk.Frame(frame_modo)
        frame_iguais.pack(fill="x", pady=5)
        tk.Radiobutton(frame_iguais, text="Dividir em partes iguais. Quantidade de partes:",
                       variable=self.var_modo_dividir, value="iguais", font=("Arial", 10),
                       command=self.atualizar_ui_divisao).pack(side="left")
        vcmd_int = (self.root.register(lambda P: str.isdigit(P) or P == ""), '%P')
        self.entry_partes_iguais = tk.Entry(frame_iguais, width=5, font=("Arial", 11), validate='all',
                                            validatecommand=vcmd_int)
        self.entry_partes_iguais.pack(side="left", padx=5)
        self.entry_partes_iguais.insert(0, "2")
        self.entry_partes_iguais.bind("<KeyRelease>", lambda e: self.verificar_estado_dividir())

        frame_pers = tk.Frame(frame_modo)
        frame_pers.pack(fill="x", pady=5)
        tk.Radiobutton(frame_pers, text="Fila Personalizada (Extrair páginas específicas para múltiplos PDFs)",
                       variable=self.var_modo_dividir, value="personalizado", font=("Arial", 10),
                       command=self.atualizar_ui_divisao).pack(anchor="w")

        self.frame_pers_controles = tk.Frame(frame_modo)
        self.frame_pers_controles.pack(fill="both", expand=True, padx=20, pady=5)

        tk.Label(self.frame_pers_controles, text="Páginas (ex: 1-50, 60):", font=("Arial", 9)).grid(row=0, column=0,
                                                                                                    sticky="w")
        self.entry_paginas_pers = tk.Entry(self.frame_pers_controles, width=30, font=("Arial", 11))
        self.entry_paginas_pers.grid(row=0, column=1, padx=5)
        tk.Button(self.frame_pers_controles, text="Adicionar Parte", command=self.adicionar_parte_personalizada).grid(
            row=0, column=2, padx=5)

        self.listbox_partes = tk.Listbox(self.frame_pers_controles, selectmode=tk.SINGLE, height=4, font=("Arial", 10))
        self.listbox_partes.grid(row=1, column=0, columnspan=3, sticky="we", pady=5)

        tk.Button(self.frame_pers_controles, text="Remover Parte Selecionada",
                  command=self.remover_parte_personalizada).grid(row=2, column=0, sticky="w")

        frame_saida = tk.LabelFrame(container, text="3. Configuração de Saída", padx=15, pady=10)
        frame_saida.pack(fill="x", pady=5)

        f_saida_top = tk.Frame(frame_saida)
        f_saida_top.pack(fill="x", pady=2)
        tk.Button(f_saida_top, text="Escolher Pasta Destino", command=self.selecionar_saida_pasta_dividir,
                  font=("Arial", 10)).pack(side="left")
        self.lbl_destino_pasta_dividir = tk.Label(f_saida_top, text="Nenhuma pasta selecionada.", fg="gray",
                                                  font=("Arial", 10))
        self.lbl_destino_pasta_dividir.pack(side="left", padx=10)

        f_saida_mid = tk.Frame(frame_saida)
        f_saida_mid.pack(fill="x", pady=5)
        tk.Label(f_saida_mid, text="Nome Base dos Arquivos Gerados:", font=("Arial", 10)).pack(side="left")
        self.entry_nome_base_dividir = tk.Entry(f_saida_mid, width=30, font=("Arial", 11))
        self.entry_nome_base_dividir.pack(side="left", padx=10)
        self.entry_nome_base_dividir.bind("<KeyRelease>", lambda e: self.verificar_estado_dividir())

        tk.Checkbutton(frame_saida, text="Máxima Compressão (Opcional: Aplica Ghostscript para redução severa)",
                       variable=self.var_compressao_max_dividir, fg="red", font=("Arial", 10)).pack(anchor="w", pady=5)

        self.btn_processar_dividir = tk.Button(container, text="Extrair e Dividir PDFs",
                                               command=self.iniciar_thread_dividir, state=tk.DISABLED, bg="blue",
                                               fg="white", font=("Arial", 12, "bold"), pady=10)
        self.btn_processar_dividir.pack(fill="x", pady=10)

        self.partes_personalizadas = []
        self.atualizar_ui_divisao()

    def atualizar_ui_divisao(self):
        if self.var_modo_dividir.get() == "iguais":
            self.entry_partes_iguais.config(state=tk.NORMAL)
            for child in self.frame_pers_controles.winfo_children():
                child.configure(state=tk.DISABLED)
        else:
            self.entry_partes_iguais.config(state=tk.DISABLED)
            for child in self.frame_pers_controles.winfo_children():
                child.configure(state=tk.NORMAL)
        self.verificar_estado_dividir()

    def adicionar_parte_personalizada(self):
        texto = self.entry_paginas_pers.get().strip()
        if texto:
            self.partes_personalizadas.append(texto)
            self.listbox_partes.insert(tk.END, f"Parte {len(self.partes_personalizadas)}: Páginas {texto}")
            self.entry_paginas_pers.delete(0, tk.END)
            self.verificar_estado_dividir()

    def remover_parte_personalizada(self):
        sel = self.listbox_partes.curselection()
        if sel:
            idx = sel[0]
            self.listbox_partes.delete(idx)
            self.partes_personalizadas.pop(idx)
            self.listbox_partes.delete(0, tk.END)
            for i, p in enumerate(self.partes_personalizadas):
                self.listbox_partes.insert(tk.END, f"Parte {i + 1}: Páginas {p}")
            self.verificar_estado_dividir()

    def processar_selecao_pdf_dividir(self, arquivo):
        self.arquivo_dividir = os.path.normpath(arquivo)
        try:
            # Blindado
            doc = self._abrir_pdf_seguro(self.arquivo_dividir)
            self.total_paginas_dividir = doc.page_count
            doc.close()
            nome = os.path.basename(self.arquivo_dividir)
            self.lbl_arquivo_dividir.config(text=f"{nome} (Total: {self.total_paginas_dividir} páginas)", fg="black")

            nome_sem_ext = os.path.splitext(nome)[0]
            self.entry_nome_base_dividir.delete(0, tk.END)
            self.entry_nome_base_dividir.insert(0, nome_sem_ext)
        except Exception as e:
            self.arquivo_dividir = ""
            messagebox.showerror("Erro", f"Não foi possível ler o PDF:\n{e}")
            self.lbl_arquivo_dividir.config(text="Nenhum arquivo selecionado.", fg="gray")
        self.verificar_estado_dividir()

    def drop_dividir(self, event):
        arquivos = self.root.tk.splitlist(event.data)
        if arquivos and arquivos[0].lower().endswith(".pdf"):
            self.processar_selecao_pdf_dividir(arquivos[0])

    def selecionar_entrada_dividir(self):
        arquivo = filedialog.askopenfilename(title="Selecione", filetypes=[("PDF", "*.pdf")])
        if arquivo:
            self.processar_selecao_pdf_dividir(arquivo)

    def selecionar_saida_pasta_dividir(self):
        pasta = filedialog.askdirectory(title="Selecionar Pasta Destino")
        if pasta:
            self.saida_dividir_pasta = os.path.normpath(pasta)
            self.lbl_destino_pasta_dividir.config(text=self.saida_dividir_pasta, fg="black")
            self.verificar_estado_dividir()

    def verificar_estado_dividir(self):
        valido = True
        if not getattr(self, 'arquivo_dividir', ""): valido = False
        if not getattr(self, 'saida_dividir_pasta', ""): valido = False
        if not self.entry_nome_base_dividir.get().strip(): valido = False

        if self.var_modo_dividir.get() == "iguais":
            if not self.entry_partes_iguais.get().strip() or int(self.entry_partes_iguais.get()) < 1:
                valido = False
        else:
            if not self.partes_personalizadas:
                valido = False

        if valido:
            self.btn_processar_dividir.config(state=tk.NORMAL)
        else:
            self.btn_processar_dividir.config(state=tk.DISABLED)

    def iniciar_thread_dividir(self):
        self.btn_processar_dividir.config(state=tk.DISABLED, text="Processando... Aguarde", bg="gray")
        threading.Thread(target=self._tarefa_processar_dividir, daemon=True).start()

    def _tarefa_processar_dividir(self):
        try:
            modo = self.var_modo_dividir.get()
            total = self.total_paginas_dividir
            nome_base = self.entry_nome_base_dividir.get().strip()
            compressao_max = self.var_compressao_max_dividir.get()

            partes_strings = []
            if modo == "iguais":
                qtd_partes = int(self.entry_partes_iguais.get())
                base = total // qtd_partes
                resto = total % qtd_partes
                inicio = 1
                for i in range(qtd_partes):
                    extra = 1 if i < resto else 0
                    fim = inicio + base + extra - 1
                    partes_strings.append(f"{inicio}-{fim}")
                    inicio = fim + 1
            else:
                partes_strings = self.partes_personalizadas

            arquivos_gerados = 0

            for idx, parte_str in enumerate(partes_strings, 1):
                paginas_indices = self.converter_string_paginas(parte_str, total)

                # Abre da RAM blindado
                doc_temp = self._abrir_pdf_seguro(self.arquivo_dividir)
                doc_temp.select(paginas_indices)

                doc_saida = fitz.open()
                doc_saida.insert_pdf(doc_temp)
                doc_temp.close()
                self._sanitizar_documento(doc_saida)

                nome_final = self._obter_caminho_seguro(
                    os.path.join(self.saida_dividir_pasta, f"{nome_base}_Parte{idx}.pdf"))
                caminho_temp = self._obter_caminho_seguro(nome_final + ".tmp.pdf") if compressao_max else nome_final

                try:
                    doc_saida.save(caminho_temp, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                except:
                    doc_saida.save(caminho_temp, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                doc_saida.close()

                if compressao_max:
                    self._comprimir_com_ghostscript(caminho_temp, nome_final)
                    if os.path.exists(caminho_temp):
                        os.remove(caminho_temp)

                arquivos_gerados += 1

            msg = f"Divisão concluída!\n{arquivos_gerados} arquivos PDF foram gerados na pasta destino com os bloqueios removidos."
            self.root.after(0, self._finalizar_dividir, True, msg)

        except Exception as e:
            self.root.after(0, self._finalizar_dividir, False, str(e))

    def _finalizar_dividir(self, sucesso, msg):
        self.btn_processar_dividir.config(state=tk.NORMAL, text="Extrair e Dividir PDFs", bg="blue")
        if sucesso:
            messagebox.showinfo("Sucesso", msg)
            self.listbox_partes.delete(0, tk.END)
            self.partes_personalizadas.clear()
            self.verificar_estado_dividir()
        else:
            messagebox.showerror("Erro Técnico", f"Falha na extração:\n{msg}")

    # ==========================================
    # ABA 3: MESCLAR EM LOTES
    # ==========================================
    def construir_aba_lotes(self):
        container = tk.Frame(self.aba_lotes)
        container.pack(fill="both", expand=True, padx=50, pady=20)

        frame_entrada = tk.LabelFrame(container, text="Pasta Origem", padx=15, pady=15)
        frame_entrada.pack(fill="x", pady=10)
        tk.Button(frame_entrada, text="Selecionar Pasta Original", command=self.selecionar_origem_lote,
                  font=("Arial", 10)).pack(anchor="w")
        self.lbl_pasta_entrada = tk.Label(frame_entrada, text="Nenhuma pasta selecionada.", fg="gray",
                                          font=("Arial", 10))
        self.lbl_pasta_entrada.pack(anchor="w", pady=(10, 0))

        frame_saida = tk.LabelFrame(container, text="Pasta Destino", padx=15, pady=15)
        frame_saida.pack(fill="x", pady=10)
        tk.Button(frame_saida, text="Selecionar Pasta para Salvar", command=self.selecionar_destino_lote,
                  font=("Arial", 10)).pack(anchor="w")
        self.lbl_saida_lote = tk.Label(frame_saida, text="Nenhum destino selecionado.", fg="gray", font=("Arial", 10))
        self.lbl_saida_lote.pack(anchor="w", pady=(10, 0))

        frame_config = tk.LabelFrame(container, text="Configuração de Agrupamento", padx=15, pady=15)
        frame_config.pack(fill="x", pady=10)

        tk.Label(frame_config, text="Nome Base (Opcional):", font=("Arial", 10)).grid(row=0, column=0, sticky="w",
                                                                                      pady=5)
        self.entry_nome_base = tk.Entry(frame_config, width=40, font=("Arial", 11))
        self.entry_nome_base.grid(row=0, column=1, columnspan=2, sticky="w", padx=10, pady=5)

        tk.Label(frame_config, text="Critério de Divisão:", font=("Arial", 10)).grid(row=1, column=0, sticky="w",
                                                                                     pady=5)

        frame_radios = tk.Frame(frame_config)
        frame_radios.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        tk.Radiobutton(frame_radios, text="Quantidade de Arquivos", variable=self.var_modo_lote, value="quantidade",
                       font=("Arial", 10)).pack(side="left", padx=(0, 10))
        tk.Radiobutton(frame_radios, text="Tamanho Máximo (MB)", variable=self.var_modo_lote, value="tamanho",
                       font=("Arial", 10)).pack(side="left")

        tk.Label(frame_config, text="Valor Limite:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        vcmd = (self.root.register(lambda P: str.isdigit(P) or P == "" or P == "."), '%P')
        self.entry_limite_lote = tk.Entry(frame_config, width=15, font=("Arial", 11), validate='all',
                                          validatecommand=vcmd)
        self.entry_limite_lote.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.entry_limite_lote.insert(0, "20")
        self.entry_limite_lote.bind("<KeyRelease>", lambda e: self.verificar_estado_lotes())

        tk.Checkbutton(frame_config, text="Máxima Compressão (Opcional: Aplica Ghostscript para redução severa)",
                       variable=self.var_compressao_max_lote, fg="red", font=("Arial", 10)).grid(row=3, column=0,
                                                                                                 columnspan=2,
                                                                                                 sticky="w", pady=5)

        self.barra_progresso_lote = ttk.Progressbar(container, orient="horizontal", mode="determinate")
        self.barra_progresso_lote.pack(fill="x", pady=(20, 5))
        self.lbl_status_lote = tk.Label(container, text="", fg="gray", font=("Arial", 10))
        self.lbl_status_lote.pack(pady=0)

        self.btn_processar_lotes = tk.Button(container, text="Processar Lotes", command=self.iniciar_thread_lotes,
                                             state=tk.DISABLED, bg="purple", fg="white", font=("Arial", 12, "bold"),
                                             pady=10)
        self.btn_processar_lotes.pack(fill="x", pady=15)

    def selecionar_origem_lote(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de origem")
        if pasta:
            self.pasta_entrada_lote = os.path.normpath(pasta)
            self.lbl_pasta_entrada.config(text=self.pasta_entrada_lote, fg="black")
            self.verificar_estado_lotes()

    def selecionar_destino_lote(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de destino")
        if pasta:
            self.pasta_saida_lote = os.path.normpath(pasta)
            self.lbl_saida_lote.config(text=self.pasta_saida_lote, fg="black")
            self.verificar_estado_lotes()

    def verificar_estado_lotes(self):
        limite = self.entry_limite_lote.get()
        if self.pasta_entrada_lote and self.pasta_saida_lote and limite and float(limite) > 0:
            self.btn_processar_lotes.config(state=tk.NORMAL)
        else:
            self.btn_processar_lotes.config(state=tk.DISABLED)

    def atualizar_progresso_lote(self, valor, texto):
        self.barra_progresso_lote["value"] = valor
        self.lbl_status_lote.config(text=texto)

    def iniciar_thread_lotes(self):
        self.btn_processar_lotes.config(state=tk.DISABLED, text="Processando... Aguarde", bg="gray")
        threading.Thread(target=self._tarefa_processar_lotes, daemon=True).start()

    def _tarefa_processar_lotes(self):
        try:
            # Usa o caminho curto na origem
            pasta_entrada = self._obter_caminho_seguro(self.pasta_entrada_lote)
            arquivos_na_pasta = [f for f in os.listdir(pasta_entrada) if
                                 f.lower().endswith('.pdf') and not f.startswith(('.', '$'))]
            arquivos_na_pasta.sort()

            total_arquivos = len(arquivos_na_pasta)
            if total_arquivos == 0:
                self.root.after(0, self._finalizar_lote, False, "Nenhum PDF encontrado na pasta.")
                return

            modo = self.var_modo_lote.get()
            limite = float(self.entry_limite_lote.get())
            nome_base = self.entry_nome_base.get().strip()
            compressao_max = self.var_compressao_max_lote.get()

            if not nome_base:
                nome_base = os.path.basename(self.pasta_entrada_lote)

            lotes = []
            if modo == "quantidade":
                limite_int = int(limite)
                lotes = [arquivos_na_pasta[i:i + limite_int] for i in range(0, total_arquivos, limite_int)]
            else:
                limite_bytes = limite * 1024 * 1024
                lote_atual = []
                tamanho_atual = 0
                for arq in arquivos_na_pasta:
                    caminho_completo = self._obter_caminho_seguro(os.path.join(self.pasta_entrada_lote, arq))
                    tam_arq = os.path.getsize(caminho_completo)

                    if tamanho_atual + tam_arq > limite_bytes and lote_atual:
                        lotes.append(lote_atual)
                        lote_atual = [arq]
                        tamanho_atual = tam_arq
                    else:
                        lote_atual.append(arq)
                        tamanho_atual += tam_arq

                if lote_atual:
                    lotes.append(lote_atual)

            arquivos_processados = 0

            for index, lote in enumerate(lotes, start=1):
                nome_final = self._obter_caminho_seguro(
                    os.path.join(self.pasta_saida_lote, f"{nome_base}_Parte_{index}.pdf"))
                caminho_temp = self._obter_caminho_seguro(nome_final + ".tmp.pdf") if compressao_max else nome_final

                doc_saida = fitz.open()
                for arq in lote:
                    arquivos_processados += 1
                    progresso = (arquivos_processados / total_arquivos) * 100
                    self.root.after(0, self.atualizar_progresso_lote, progresso,
                                    f"Processando: {arq} ({arquivos_processados}/{total_arquivos})")

                    caminho_completo = self._obter_caminho_seguro(os.path.join(self.pasta_entrada_lote, arq))

                    # Usa blindagem
                    doc_temp = self._abrir_pdf_seguro(caminho_completo)
                    doc_saida.insert_pdf(doc_temp)
                    doc_temp.close()

                self._sanitizar_documento(doc_saida)

                try:
                    doc_saida.save(caminho_temp, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                except:
                    doc_saida.save(caminho_temp, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                doc_saida.close()

                if compressao_max:
                    self._comprimir_com_ghostscript(caminho_temp, nome_final)
                    if os.path.exists(caminho_temp):
                        os.remove(caminho_temp)

            self.root.after(0, self._finalizar_lote, True,
                            f"Sucesso! {total_arquivos} arquivos processados em {len(lotes)} PDFs.")

        except Exception as e:
            self.root.after(0, self._finalizar_lote, False, str(e))

    def _finalizar_lote(self, sucesso, mensagem):
        self.btn_processar_lotes.config(state=tk.NORMAL, text="Processar Lotes", bg="purple")
        self.atualizar_progresso_lote(0, "")
        if sucesso:
            messagebox.showinfo("Concluído", mensagem)
            self.pasta_entrada_lote = ""
            self.lbl_pasta_entrada.config(text="Nenhuma pasta selecionada.", fg="gray")
        else:
            messagebox.showerror("Erro", mensagem)

    # ==========================================
    # ABA 4: RENOMEAR PDFs
    # ==========================================
    def construir_aba_renomear(self):
        container = tk.Frame(self.aba_renomear)
        container.pack(fill="both", expand=True, padx=50, pady=20)

        tk.Label(container, text="Formatação Automática de Nomes", font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(container, text="Remove acentos e caracteres especiais de todos os PDFs da pasta selecionada.",
                 font=("Arial", 11)).pack(pady=5)

        frame_entrada = tk.LabelFrame(container, text="Selecione a Pasta", padx=15, pady=15)
        frame_entrada.pack(fill="x", pady=20)
        tk.Button(frame_entrada, text="Localizar Pasta", command=self.selecionar_pasta_renomear,
                  font=("Arial", 11)).pack(anchor="w")
        self.lbl_pasta_renomear = tk.Label(frame_entrada, text="Nenhuma pasta selecionada.", fg="gray",
                                           font=("Arial", 11))
        self.lbl_pasta_renomear.pack(anchor="w", pady=(10, 0))

        frame_opcoes_renomear = tk.Frame(container)
        frame_opcoes_renomear.pack(fill="x", pady=5)
        tk.Checkbutton(frame_opcoes_renomear, text="Incluir arquivos em subpastas",
                       variable=self.var_incluir_subpastas, font=("Arial", 11)).pack(anchor="w")

        self.btn_executar_renomear = tk.Button(container, text="Renomear Arquivos na Pasta",
                                               command=self.executar_renomear, state=tk.DISABLED, bg="orange",
                                               fg="black", font=("Arial", 12, "bold"), pady=10)
        self.btn_executar_renomear.pack(fill="x", pady=20)

    def selecionar_pasta_renomear(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta com PDFs para renomear")
        if pasta:
            self.pasta_renomear = os.path.normpath(pasta)
            self.lbl_pasta_renomear.config(text=self.pasta_renomear, fg="black")
            self.btn_executar_renomear.config(state=tk.NORMAL)

    def executar_renomear(self):
        try:
            incluir_subpastas = self.var_incluir_subpastas.get()
            modificados = 0

            # Formata curto para a pasta raiz, mas usa string normal para os walk files
            pasta_segura = self._obter_caminho_seguro(self.pasta_renomear)

            for dir_atual, sub_dirs, arquivos in os.walk(pasta_segura):
                for arquivo in arquivos:
                    if arquivo.lower().endswith('.pdf'):
                        nome, extensao = os.path.splitext(arquivo)
                        nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8')
                        nome = re.sub(r'[^a-zA-Z0-9]', ' ', nome)
                        nome = re.sub(r'\s+', ' ', nome).strip()
                        novo_nome = nome + extensao

                        if novo_nome != arquivo:
                            antigo = self._obter_caminho_seguro(os.path.join(dir_atual, arquivo))
                            novo = self._obter_caminho_seguro(os.path.join(dir_atual, novo_nome))
                            os.rename(antigo, novo)
                            modificados += 1

                if not incluir_subpastas:
                    break

            messagebox.showinfo("Concluído", f"Varredura finalizada.\n{modificados} arquivos foram renomeados.")
            self.pasta_renomear = ""
            self.lbl_pasta_renomear.config(text="Nenhuma pasta selecionada.", fg="gray")
            self.btn_executar_renomear.config(state=tk.DISABLED)
            self.var_incluir_subpastas.set(False)
        except Exception as e:
            messagebox.showerror("Erro Técnico", f"Falha ao renomear arquivos:\n{e}")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = OtimizadorPDFApp(root)
    root.mainloop()
