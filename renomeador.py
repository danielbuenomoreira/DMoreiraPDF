import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
import webbrowser
import os
import threading
import sys
import unicodedata
import re
import ctypes  # Necessário para blindagem de caminhos longos (MAX_PATH)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class RenomearRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sanitizador e Formatador de PDFs")
        self.root.geometry("600x550")
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap(resource_path("DMoreiraPDF.ico"))
        except:
            pass

        self.pasta_alvo = ""
        self.pasta_destino = ""
        self.var_incluir_subpastas = tk.BooleanVar(value=True)
        self.var_exportacao_unificada = tk.BooleanVar(value=False)

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
        """Lê o arquivo para a memória RAM. Evita erro de caminho longo e bloqueio de 'Acesso Negado'."""
        caminho_seg = self._obter_caminho_seguro(caminho)
        with open(caminho_seg, "rb") as f:
            pdf_bytes = f.read()
        doc = fitz.open("pdf", pdf_bytes)
        if doc.is_encrypted:
            doc.authenticate("")
        return doc

    # ==========================================
    # NÚCLEO DE HIGIENIZAÇÃO
    # ==========================================
    def _sanitizar_e_salvar(self, caminho_origem, caminho_destino):
        """Aplica a remoção de IRM, achatamento de assinaturas e destruição de catálogos com leitura segura."""
        # Usa o método de abertura segura (RAM)
        doc_origem = self._abrir_pdf_seguro(caminho_origem)

        for pagina in doc_origem:
            for anotacao in pagina.annots():
                if anotacao.type[0] == fitz.PDF_ANNOT_WIDGET:
                    anotacao.set_flags(fitz.ANNOT_FLAG_PRINT | fitz.ANNOT_FLAG_LOCKED | fitz.ANNOT_FLAG_LOCKED_CONTENTS)
                    anotacao.update()

        doc_saida = fitz.open()
        doc_saida.insert_pdf(doc_origem)
        doc_origem.close()

        try:
            cat = doc_saida.pdf_catalog()
            doc_saida.xref_set_key(cat, "AcroForm", "null")
            doc_saida.xref_set_key(cat, "Perms", "null")
            doc_saida.xref_set_key(cat, "Collection", "null")
            doc_saida.xref_set_key(cat, "SigFlags", "null")
        except:
            pass

        caminho_destino_seguro = self._obter_caminho_seguro(caminho_destino)
        try:
            doc_saida.save(caminho_destino_seguro, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
        except:
            doc_saida.save(caminho_destino_seguro, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
        doc_saida.close()

    # ==========================================
    # INTERFACE GRÁFICA (UI)
    # ==========================================
    def construir_interface(self):
        container = tk.Frame(self.root, padx=20, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Higienização e Formatação de Nomes", font=("Arial", 16, "bold")).pack(pady=5)
        tk.Label(container,
                 text="Remove travas de segurança (IRM/Assinaturas) e formata nomes.",
                 font=("Arial", 10)).pack(pady=5)

        # Frame Origem
        frame_entrada = tk.LabelFrame(container, text="1. Selecione a Pasta Alvo (Origem)", padx=10, pady=10)
        frame_entrada.pack(fill="x", pady=10)

        tk.Button(frame_entrada, text="Localizar Pasta Origem", command=self.selecionar_pasta_origem,
                  font=("Arial", 10)).pack(anchor="w")
        self.lbl_pasta = tk.Label(frame_entrada, text="Nenhuma pasta selecionada.", fg="gray", font=("Arial", 9))
        self.lbl_pasta.pack(anchor="w", pady=(5, 0))

        tk.Checkbutton(container, text="Incluir processamento de subpastas", variable=self.var_incluir_subpastas,
                       font=("Arial", 10)).pack(anchor="w", padx=5)

        # Frame Destino (Exportação Unificada)
        tk.Checkbutton(container, text="Ativar exportação unificada (prefixos Nível 1 e 2)",
                       variable=self.var_exportacao_unificada, command=self.alternar_modo_exportacao,
                       font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(10, 0))

        self.frame_destino = tk.LabelFrame(container,
                                           text="2. Selecione a Pasta de Destino (Obrigatório para Unificada)", padx=10,
                                           pady=10)
        self.frame_destino.pack(fill="x", pady=5)

        self.btn_destino = tk.Button(self.frame_destino, text="Localizar Pasta Destino",
                                     command=self.selecionar_pasta_destino, font=("Arial", 10), state=tk.DISABLED)
        self.btn_destino.pack(anchor="w")
        self.lbl_pasta_destino = tk.Label(self.frame_destino, text="Requer ativação da exportação unificada.",
                                          fg="gray", font=("Arial", 9))
        self.lbl_pasta_destino.pack(anchor="w", pady=(5, 0))

        # Status e Execução
        self.lbl_status = tk.Label(container, text="", fg="blue", font=("Arial", 10))
        self.lbl_status.pack(pady=10)

        self.btn_executar = tk.Button(container, text="Higienizar Arquivos",
                                      command=self.iniciar_processamento, state=tk.DISABLED, bg="red", fg="white",
                                      font=("Arial", 12, "bold"), pady=10)
        self.btn_executar.pack(fill="x", pady=5)

        # Rodapé
        frame_rodape = tk.Frame(self.root)
        frame_rodape.pack(side="bottom", pady=5)
        tk.Label(frame_rodape, text="Desenvolvido por ", font=("Arial", 10)).pack(side="left")
        lbl_link = tk.Label(frame_rodape, text="@danielbuenomoreiradev", fg="blue", cursor="hand2",
                            font=("Arial", 10, "bold"))
        lbl_link.pack(side="left")
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://danielbuenomoreira.github.io/QuemSouEu/"))

    def selecionar_pasta_origem(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta com os PDFs (Origem)")
        if pasta:
            self.pasta_alvo = os.path.normpath(pasta)
            self.lbl_pasta.config(text=self.pasta_alvo, fg="black")
            self.validar_prontidao()

    def selecionar_pasta_destino(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de destino")
        if pasta:
            self.pasta_destino = os.path.normpath(pasta)
            self.lbl_pasta_destino.config(text=self.pasta_destino, fg="black")
            self.validar_prontidao()

    def alternar_modo_exportacao(self):
        if self.var_exportacao_unificada.get():
            self.btn_destino.config(state=tk.NORMAL)
            self.lbl_pasta_destino.config(
                text="Nenhuma pasta de destino selecionada." if not self.pasta_destino else self.pasta_destino)
            self.btn_executar.config(text="Higienizar e Exportar para Destino", bg="darkgreen")
        else:
            self.btn_destino.config(state=tk.DISABLED)
            self.lbl_pasta_destino.config(text="Requer ativação da exportação unificada.")
            self.btn_executar.config(text="Higienizar e Sobrescrever Originais", bg="red")

        self.validar_prontidao()

    def validar_prontidao(self):
        pronto = False
        if self.pasta_alvo:
            if self.var_exportacao_unificada.get():
                if self.pasta_destino:
                    pronto = True
            else:
                pronto = True

        self.btn_executar.config(state=tk.NORMAL if pronto else tk.DISABLED)

    def formatar_nome(self, nome_original):
        nome = unicodedata.normalize('NFKD', nome_original).encode('ASCII', 'ignore').decode('utf-8')
        nome = re.sub(r'[^a-zA-Z0-9]', ' ', nome)
        nome = re.sub(r'\s+', ' ', nome).strip()
        return nome

    def gerar_nome_unico(self, caminho_base):
        """Garante que o arquivo não sobrescreva outro existente verificando o caminho seguro."""
        caminho_base_seguro = self._obter_caminho_seguro(caminho_base)
        if not os.path.exists(caminho_base_seguro):
            return caminho_base

        diretorio, nome_arquivo = os.path.split(caminho_base)
        nome, ext = os.path.splitext(nome_arquivo)

        contador = 2
        while True:
            novo_nome = f"{nome} {contador:02d}{ext}"
            novo_caminho = os.path.join(diretorio, novo_nome)
            novo_caminho_seguro = self._obter_caminho_seguro(novo_caminho)
            if not os.path.exists(novo_caminho_seguro):
                return novo_caminho
            contador += 1

    def iniciar_processamento(self):
        if not self.var_exportacao_unificada.get():
            resposta = messagebox.askyesno("Atenção - Ação Destrutiva",
                                           "Esta ação irá SOBRESCREVER permanentemente os PDFs originais na pasta alvo.\n\nTem a certeza de que deseja continuar?")
            if not resposta:
                return

        self.btn_executar.config(state=tk.DISABLED, text="Processando... Aguarde")
        self.lbl_status.config(text="Iniciando varredura...")
        threading.Thread(target=self._tarefa_processar, daemon=True).start()

    def _tarefa_processar(self):
        try:
            incluir_subpastas = self.var_incluir_subpastas.get()
            modo_unificado = self.var_exportacao_unificada.get()
            processados = 0

            pasta_alvo_segura = self._obter_caminho_seguro(self.pasta_alvo)

            for dir_atual, sub_dirs, arquivos in os.walk(pasta_alvo_segura):
                pdfs = [f for f in arquivos if f.lower().endswith('.pdf') and not f.startswith('.tmp')]

                for arquivo in pdfs:
                    caminho_origem = os.path.join(dir_atual, arquivo)
                    nome_base, extensao = os.path.splitext(arquivo)
                    nome_limpo = self.formatar_nome(nome_base)

                    self.root.after(0, self.lbl_status.config, {"text": f"Higienizando: {arquivo}"})

                    if modo_unificado:
                        caminho_relativo = os.path.relpath(dir_atual, pasta_alvo_segura)
                        partes_caminho = caminho_relativo.split(os.sep)

                        prefixos = []
                        if caminho_relativo != '.':
                            prefixos = [self.formatar_nome(p) for p in partes_caminho[:2]]

                        elementos_nome = prefixos + [nome_limpo]
                        novo_nome_arquivo = " ".join(elementos_nome) + extensao

                        caminho_destino_base = os.path.join(self.pasta_destino, novo_nome_arquivo)
                        caminho_destino_final = self.gerar_nome_unico(caminho_destino_base)

                        self._sanitizar_e_salvar(caminho_origem, caminho_destino_final)

                    else:
                        novo_nome_arquivo = f"{nome_limpo}{extensao}"
                        caminho_destino = os.path.join(dir_atual, novo_nome_arquivo)
                        caminho_temp = caminho_origem + ".tmp.pdf"

                        self._sanitizar_e_salvar(caminho_origem, caminho_temp)

                        # Usa os caminhos seguros na hora de manipular os arquivos físicos
                        os.remove(self._obter_caminho_seguro(caminho_origem))
                        os.replace(self._obter_caminho_seguro(caminho_temp),
                                   self._obter_caminho_seguro(caminho_destino))

                    processados += 1

                if not incluir_subpastas:
                    break

            self.root.after(0, self._finalizar, True,
                            f"Varredura concluída.\n{processados} arquivos foram processados.")
        except Exception as e:
            self.root.after(0, self._finalizar, False, str(e))

    def _finalizar(self, sucesso, mensagem):
        self.alternar_modo_exportacao()
        self.lbl_status.config(text="")
        if sucesso:
            messagebox.showinfo("Concluído", mensagem)
        else:
            messagebox.showerror("Erro Técnico", f"Falha no processamento:\n{mensagem}")


if __name__ == "__main__":
    root = tk.Tk()
    app = RenomearRemoverApp(root)
    root.mainloop()
