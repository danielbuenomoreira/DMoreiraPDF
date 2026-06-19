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
import json
import ctypes  # Necessário para blindagem de MAX_PATH no Windows

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    raise ImportError("A biblioteca tkinterdnd2 é necessária. Instale executando: pip install tkinterdnd2")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Piaa2026AppV2:
    def __init__(self, root):
        self.root = root
        self.root.title("Organizador PIAA 2026 v2.1 - Edital SELT")

        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)
        self.root.resizable(True, True)

        try:
            self.root.iconbitmap(resource_path("DMoreiraPDF.ico"))
        except:
            pass

        # ==========================================
        # ESTRUTURA DO EDITAL (Individual vs Unificado)
        # ==========================================
        self.STR_UNIFICADO = "[ ITENS UNIFICADOS DA OBRA ]"
        self.PASTA_UNIFICADO = "ITENS UNIFICADOS DA OBRA"

        self.estrutura = {
            'individual': {
                'Item 1 - Manifestação de Interesse': {
                    '1.1 - Termo de Adesão (3.1.1)': '3.1.1 Requerimento com a indicação obra de infraestrutura de pavimentação e de acesso asfáltico às expensas próprias para a posterior fruição de benefício fiscal compensatório, na forma de crédito fiscal presumido, a ser autorizada pela SEFAZ, limitado ao valor efetivamente despendido pela empresa na obra, com a localização do acesso em croqui com fotos, exposição de finalidades e demais documentos exigidos para apreciação, nos termos do Anexo I.',
                    '1.3 - Valor ICMS Próprio (3.1.4)': '3.1.4 declaração e comprovação do valor do ICMS próprio e direto gerado no exercício do ano fiscal anterior com detalhamento mensal.'
                },
                'Item 2 - Estimativa de Incremento': {
                    '2.1 - Declaração Interesse Público (3.1.2)': '3.1.2 indicação do interesse público envolvido com estimativa de incremento anual de faturamento da empresa proponente ou benefício para a comunidade local, associada à obra de infraestrutura de pavimentação e de acesso asfáltico, justificando a vantajosidade à região, tais como a projeção de empregos a serem gerados ou de incremento na arrecadação das receitas tributárias;'
                },
                'Item 5 - Certidão Negativa (SEFAZ)': {
                    '5.1 - Certidão Negativa Débitos (3.1.6)': '3.1.6 certidão negativa de débito tributário ou positiva com efeito de negativa expedida pela Secretaria da Fazenda – SEFAZ, bem como declaração expressa firmada pelo representante legal de não estar a empresa na lista dos devedores que tenham créditos tributários inscritos em Dívida Ativa do artigo 13 da Lei nº 6.537, de 27 de fevereiro de 1973.'
                },
                'Item 7 - CNPJ e Inscrição Estadual': {
                    '7.1 - Inscrição CNPJ (3.1.10)': '3.1.10 apresentação da inscrição no Cadastro Nacional de Pessoas Jurídicas – CNPJ, caracterizando a existência de estabelecimento empresarial no Estado que comprovem mínimo de dois anos de cadastro ativo.',
                    '7.2 - Inscrição Estadual (3.1.10)': '3.1.10 apresentação da Inscrição Estadual do ICMS, caracterizando a existência de estabelecimento empresarial no Estado que comprovem mínimo de dois anos de cadastro ativo.'
                },
                'Item 8 - Documentos Cadastrais e Contrato': {
                    '8.1 - Documentos Cadastrais (3.1.11)': '3.1.11 documentos cadastrais da empresa ou do grupo de empresas proponentes, e de seus sócios.',
                    '8.2 - Contrato Social (3.1.11)': '3.1.11 documentos cadastrais (Contrato Social) da empresa ou do grupo de empresas proponentes, e de seus sócios.'
                },
                'Item 9 - Enquadramento na lista do art. 13, da Lei nº 6.537': {
                    '9.1 - CADIN (Art. 13)': 'Enquadramento na lista do art. 13, da Lei nº 6.537, de 27 de fevereiro de 1973.'
                }
            },
            'unificado': {
                'Item 3 - Localização, Objeto e Orçamento': {
                    '3.1 - Orçamento e Cronograma (3.1.3)': '3.1.3 declaração com descrição do tipo de empreendimento, valor do orçamento da obra e que esse foi elaborado com base na tabela SICRO, e prazo previsto para execução.'
                },
                'Item 4 - Projeto Básico e Executivo': {
                    '4.1 - Projeto Básico e Executivo (3.1.7 e 3.1.8)': '3.1.7 projeto básico no qual conste o conjunto de elementos necessários e suficientes à execução completa da obra, de acordo com as normas pertinentes da ABNT.\n3.1.8 projeto executivo no qual conste o conjunto dos elementos necessários e suficientes à execução completa da obra, de acordo com as normas pertinentes da ABNT.'
                },
                'Item 6 - Comprovação Ambiental': {
                    '6.1 - Cumprimento Legislação Ambiental (3.1.9)': '3.1.9 comprovação de cumprimento da legislação ambiental por parte da empresa proponente, relativamente ao projeto vinculado, quando do início da obra; devendo a empresa proponente, mediante delegação do órgão gestor do trecho rodoviário, providenciar o licenciamento ambiental da obra.'
                },
                'Item 10 - Outros': {
                    '10.1 - Outros documentos': 'Outros documentos, projetos complementares, mapas, arquivos editáveis, e anexos volumosos ou técnicos não englobados nos itens anteriores.'
                }
            }
        }

        # Descrições para as categorias (Títulos principais)
        self.textos_categorias = {
            'Item 1 - Manifestação de Interesse': 'Manifestação de interesse de realizar determinada obra de infraestrutura de pavimentação e de acesso asfáltico.',
            'Item 2 - Estimativa de Incremento': 'Estimativa de incremento anual de faturamento da empresa proponente ou empregos ou receita tributaria (detalhar).',
            'Item 3 - Localização, Objeto e Orçamento': 'Localização e objeto da obra, valor do orçamento em conformidade com tabela SICRO, e período de execução.',
            'Item 4 - Projeto Básico e Executivo': 'Projeto Básico e Executivo no qual constem o conjunto dos elementos necessários e suficientes à execução completa da obra, de acordo com as normas pertinentes da Associação Brasileira de Normas Técnicas – ABNT.',
            'Item 5 - Certidão Negativa (SEFAZ)': 'Certidão negativa de débito tributário ou positiva com efeito de negativa expedida pela Secretaria da Fazenda – SEFAZ.',
            'Item 6 - Comprovação Ambiental': 'Comprovação de cumprimento da legislação ambiental por parte da empresa proponente, relativamente ao projeto vinculado.',
            'Item 7 - CNPJ e Inscrição Estadual': 'Comprovante de inscrição no Cadastro Nacional de Pessoas Jurídicas – CNPJ - e de Inscrição Estadual, ambos caracterizando a existência de estabelecimento empresarial no Estado.',
            'Item 8 - Documentos Cadastrais e Contrato': 'Documentos cadastrais da empresa ou do grupo de empresas proponentes, e de seus sócios.',
            'Item 9 - Enquadramento na lista do art. 13, da Lei nº 6.537': 'Enquadramento na lista do art. 13, da Lei nº 6.537, de 27 de fevereiro de 1973.',
            'Item 10 - Outros': 'Pasta opcional destinada a agrupar anexos extras e outros documentos.'
        }

        # Variáveis de Interface (Tkinter)
        self.municipio = tk.StringVar()
        self.nome_empresa_temp = tk.StringVar()

        # Estado Global (Será salvo no JSON)
        self.estado_projeto = {
            "municipio": "",
            "empresas": [],
            "dados": {}
        }

        self.pasta_raiz_projeto = ""
        self.caminho_json = ""

        self.entidade_atual = ""
        self.categoria_atual = ""
        self.subitem_atual = ""

        # Memória temporária para edição manual antes de salvar
        self.arquivos_temp = []

        self.var_compressao_maxima = tk.BooleanVar()
        self.var_nao_aplica = tk.BooleanVar()

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
    # LÓGICA DE NOMENCLATURA E PREFIXOS
    # ==========================================
    def formatar_nome(self, nome_original):
        """Remove acentos, mas PRESERVA letras, números, espaços, hífens e underlines."""
        nome = unicodedata.normalize('NFKD', nome_original).encode('ASCII', 'ignore').decode('utf-8')
        nome = re.sub(r'[^a-zA-Z0-9\-_ ]', ' ', nome)
        nome = re.sub(r'\s+', ' ', nome).strip()
        return nome

    def _obter_prefixo_empresa(self, nome_empresa):
        """Gera o prefixo da empresa com os primeiros 10 caracteres limpos."""
        nome_limpo = self.formatar_nome(nome_empresa)
        return nome_limpo[:10].strip()

    # ==========================================
    # NÚCLEO BLINDADO: SANITIZAÇÃO E GHOSTSCRIPT
    # ==========================================
    def _blindagem_sanitizacao(self, doc_origem, documento_destino):
        for pagina in doc_origem:
            for anotacao in pagina.annots():
                if anotacao.type[0] == fitz.PDF_ANNOT_WIDGET:
                    pagina.delete_annot(anotacao)

        documento_destino.insert_pdf(doc_origem)

    def _limpeza_final(self, doc_saida):
        try:
            cat = doc_saida.pdf_catalog()
            doc_saida.xref_set_key(cat, "AcroForm", "null")
            doc_saida.xref_set_key(cat, "Perms", "null")
            doc_saida.xref_set_key(cat, "Collection", "null")
            doc_saida.xref_set_key(cat, "SigFlags", "null")
        except:
            pass

    def _comprimir_com_ghostscript(self, arquivo_entrada, arquivo_saida):
        gs_exec = self._obter_caminho_seguro(resource_path("gswin64c.exe"))
        comando = [
            gs_exec, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={self._obter_caminho_seguro(arquivo_saida)}",
            self._obter_caminho_seguro(arquivo_entrada)
        ]
        try:
            subprocess.run(comando, check=True, creationflags=0x08000000)
            return True
        except Exception as e:
            raise RuntimeError(f"Falha no motor Ghostscript: {e}")

    # ==========================================
    # GERENCIAMENTO DE ESTADO (JSON)
    # ==========================================
    def inicializar_estrutura_json(self):
        # 1. Popula Itens Unificados
        if self.STR_UNIFICADO not in self.estado_projeto["dados"]:
            self.estado_projeto["dados"][self.STR_UNIFICADO] = {}
            for cat, subitens in self.estrutura['unificado'].items():
                self.estado_projeto["dados"][self.STR_UNIFICADO][cat] = {}
                for sub in subitens.keys():
                    # Item 10 fica como Não se Aplica por padrão
                    padrao_na = True if ("Item 10" in cat) else False
                    self.estado_projeto["dados"][self.STR_UNIFICADO][cat][sub] = {"arquivos": [],
                                                                                  "nao_aplica": padrao_na}

        # 2. Popula Empresas
        for emp in self.estado_projeto["empresas"]:
            if emp not in self.estado_projeto["dados"]:
                self.estado_projeto["dados"][emp] = {}
                for cat, subitens in self.estrutura['individual'].items():
                    self.estado_projeto["dados"][emp][cat] = {}
                    for sub in subitens.keys():
                        # Item 2 e Item 1.3 ficam como Não se Aplica por padrão
                        padrao_na = True if ("Item 2" in cat or "1.3" in sub) else False
                        self.estado_projeto["dados"][emp][cat][sub] = {"arquivos": [], "nao_aplica": padrao_na}

    def salvar_json(self):
        if self.caminho_json:
            with open(self.caminho_json, 'w', encoding='utf-8') as f:
                json.dump(self.estado_projeto, f, ensure_ascii=False, indent=4)

    def carregar_projeto(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta raiz do projeto")
        if not pasta: return

        self.pasta_raiz_projeto = os.path.normpath(pasta)
        json_files = [f for f in os.listdir(self.pasta_raiz_projeto) if f.endswith(".json") and "estado_piaa" in f]

        if json_files:
            self.caminho_json = os.path.join(self.pasta_raiz_projeto, json_files[0])
            with open(self.caminho_json, 'r', encoding='utf-8') as f:
                self.estado_projeto = json.load(f)

            self.municipio.set(self.estado_projeto.get("municipio", ""))
            self.listbox_empresas.delete(0, tk.END)
            for emp in self.estado_projeto.get("empresas", []):
                self.listbox_empresas.insert(tk.END, emp)

            self.ativar_aba_documentos()
            messagebox.showinfo("Sucesso", "Projeto carregado com sucesso!")
        else:
            messagebox.showwarning("Aviso",
                                   "Nenhum arquivo de estado (.json) encontrado nesta pasta. Crie um novo projeto.")

    # ==========================================
    # INTERFACE GRÁFICA (UI)
    # ==========================================
    def construir_interface(self):
        style = ttk.Style()

        style.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=[12, 8])
        style.configure("TLabelframe.Label", font=("Arial", 12, "bold"), foreground="#003366")

        style.configure("Treeview", font=("Arial", 12), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))

        frame_header = tk.Frame(self.root, bg="#005b96", pady=15)
        frame_header.pack(fill="x")
        tk.Label(frame_header,
                 text="Organizador PIAA 2026 v2.1 - Edital SELT\nGestão Inteligente e Sanitização Obrigatória PROA",
                 bg="#005b96", fg="white", font=("Arial", 16, "bold"), justify="center").pack()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.aba_estrutura = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_estrutura, text="1. Criar / Carregar Projeto")
        self.construir_aba_estrutura()

        self.aba_documentos = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_documentos, text="2. Gerenciar Documentos", state="disabled")
        self.construir_aba_documentos()

        frame_rodape = tk.Frame(self.root)
        frame_rodape.pack(side="bottom", pady=5)
        tk.Label(frame_rodape, text="Desenvolvido por ", font=("Arial", 10)).pack(side="left")
        lbl_link = tk.Label(frame_rodape, text="@danielbuenomoreiradev", fg="blue", cursor="hand2",
                            font=("Arial", 10, "bold"))
        lbl_link.pack(side="left")
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://danielbuenomoreira.github.io/QuemSouEu/"))

    # --- ABA 1: ESTRUTURA ---
    def construir_aba_estrutura(self):
        container = tk.Frame(self.aba_estrutura, padx=40, pady=20)
        container.pack(fill="both", expand=True)

        f_topo = tk.Frame(container)
        f_topo.pack(fill="x", pady=10)
        tk.Button(f_topo, text="📂 Carregar Projeto Existente", command=self.carregar_projeto, bg="#f39c12", fg="white",
                  font=("Arial", 12, "bold"), pady=5).pack(side="right")

        frame_mun = tk.Frame(container)
        frame_mun.pack(fill="x", pady=10)
        tk.Label(frame_mun, text="Município do Projeto:", font=("Arial", 14, "bold")).pack(side="left")
        tk.Entry(frame_mun, textvariable=self.municipio, font=("Arial", 16), width=40).pack(side="left", padx=10)

        frame_empresas = tk.LabelFrame(container, text="Empresas Participantes", padx=20, pady=20)
        frame_empresas.pack(fill="both", expand=True, pady=10)

        f_add = tk.Frame(frame_empresas)
        f_add.pack(fill="x", pady=5)
        tk.Label(f_add, text="Nome da Empresa:", font=("Arial", 12)).pack(side="left")
        entry_empresa = tk.Entry(f_add, textvariable=self.nome_empresa_temp, font=("Arial", 14), width=40)
        entry_empresa.pack(side="left", padx=10)
        entry_empresa.bind("<Return>", lambda e: self.adicionar_empresa())
        tk.Button(f_add, text="+ Adicionar", command=self.adicionar_empresa, bg="#2ecc71", fg="white",
                  font=("Arial", 12, "bold")).pack(side="left")

        self.listbox_empresas = tk.Listbox(frame_empresas, font=("Arial", 14), height=6)
        self.listbox_empresas.pack(fill="both", expand=True, pady=10)
        tk.Button(frame_empresas, text="- Remover Empresa", command=self.remover_empresa, font=("Arial", 12)).pack(
            anchor="w")

        f_criar = tk.Frame(container)
        f_criar.pack(fill="x", pady=20)
        tk.Button(f_criar, text="Criar Novo Projeto e Pastas", command=self.criar_diretorios, bg="#005b96", fg="white",
                  font=("Arial", 16, "bold"), pady=10).pack(fill="x")

    def adicionar_empresa(self):
        nome = self.nome_empresa_temp.get().strip()
        if nome:
            emps = list(self.listbox_empresas.get(0, tk.END))
            if nome not in emps:
                self.listbox_empresas.insert(tk.END, nome)
                self.nome_empresa_temp.set("")
            else:
                messagebox.showwarning("Aviso", "Empresa já adicionada.")

    def remover_empresa(self):
        sel = self.listbox_empresas.curselection()
        if sel:
            self.listbox_empresas.delete(sel[0])

    def criar_diretorios(self):
        mun = self.formatar_nome(self.municipio.get().strip())
        emps = list(self.listbox_empresas.get(0, tk.END))
        if not mun or not emps:
            messagebox.showwarning("Erro", "Preencha o município e adicione empresas.")
            return

        pasta_destino = filedialog.askdirectory(title="Selecione onde criar o Projeto")
        if not pasta_destino: return

        self.pasta_raiz_projeto = os.path.join(pasta_destino, f"PIAA2026_{mun}")
        os.makedirs(self.pasta_raiz_projeto, exist_ok=True)

        self.caminho_json = os.path.join(self.pasta_raiz_projeto, f"estado_piaa_{mun}.json")

        self.estado_projeto["municipio"] = self.municipio.get().strip()
        self.estado_projeto["empresas"] = emps
        self.inicializar_estrutura_json()
        self.salvar_json()

        os.makedirs(os.path.join(self.pasta_raiz_projeto, self.PASTA_UNIFICADO), exist_ok=True)
        for emp in emps:
            emp_limpa = self.formatar_nome(emp)
            os.makedirs(os.path.join(self.pasta_raiz_projeto, emp_limpa), exist_ok=True)

        self.ativar_aba_documentos()
        messagebox.showinfo("Sucesso", "Projeto criado. Siga para a aba Gerenciar Documentos.")

    def ativar_aba_documentos(self):
        self.notebook.tab(self.aba_documentos, state="normal")
        opcoes_dropdown = [self.STR_UNIFICADO] + self.estado_projeto["empresas"]
        self.combo_empresas['values'] = opcoes_dropdown
        self.combo_empresas.current(0)
        self.notebook.select(self.aba_documentos)
        self.trocar_entidade()

    # --- ABA 2: DOCUMENTOS ---
    def construir_aba_documentos(self):
        container = tk.Frame(self.aba_documentos, padx=10, pady=10)
        container.pack(fill="both", expand=True)

        f_top = tk.Frame(container)
        f_top.pack(fill="x", pady=(0, 10))
        tk.Label(f_top, text="Selecione o Grupo/Empresa:", font=("Arial", 14, "bold")).pack(side="left")
        self.combo_empresas = ttk.Combobox(f_top, state="readonly", font=("Arial", 14), width=50)
        self.combo_empresas.pack(side="left", padx=10)
        self.combo_empresas.bind("<<ComboboxSelected>>", self.trocar_entidade)

        paned = ttk.PanedWindow(container, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        f_esq = tk.LabelFrame(paned, text="Checklist do Edital", padx=5, pady=5)
        paned.add(f_esq, weight=1)

        self.tree = ttk.Treeview(f_esq, selectmode="browse", show="tree")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_tree = ttk.Scrollbar(f_esq, orient="vertical", command=self.tree.yview)
        scroll_tree.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll_tree.set)
        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_treeview)

        f_dir = tk.LabelFrame(paned, text="Gerenciar Documentos (Edição Manual)", padx=15, pady=10)
        paned.add(f_dir, weight=2)

        self.lbl_subitem_titulo = tk.Label(f_dir, text="Selecione uma categoria ou subitem na lista",
                                           font=("Arial", 14, "bold"),
                                           fg="#005b96", wraplength=600, justify="left")
        self.lbl_subitem_titulo.pack(anchor="w", fill="x", pady=(0, 10))

        f_acoes_sub = tk.Frame(f_dir)
        f_acoes_sub.pack(fill="x", pady=5)
        tk.Button(f_acoes_sub, text="ⓘ Ler Instrução Normativa", command=self.mostrar_info, font=("Arial", 12, "bold"),
                  bg="#3498db", fg="white", pady=5).pack(side="left")

        self.check_na = tk.Checkbutton(f_acoes_sub, text="Não se aplica / Não necessário", variable=self.var_nao_aplica,
                                       font=("Arial", 12, "bold"), fg="#e74c3c")
        self.check_na.pack(side="right")

        tk.Label(f_dir, text="Arquivos Vinculados (Arraste PDFs):", font=("Arial", 12)).pack(anchor="w", pady=(10, 0))

        self.listbox_docs = tk.Listbox(f_dir, font=("Arial", 12), selectmode=tk.SINGLE)
        self.listbox_docs.pack(fill="both", expand=True, pady=5)
        self.listbox_docs.drop_target_register(DND_FILES)
        self.listbox_docs.dnd_bind('<<Drop>>', self.drop_documentos)

        f_controles_arq = tk.Frame(f_dir)
        f_controles_arq.pack(fill="x", pady=5)
        tk.Button(f_controles_arq, text="+ Adicionar PDF", command=self.adicionar_documentos, width=15,
                  font=("Arial", 11)).pack(
            side="left", padx=2)
        tk.Button(f_controles_arq, text="- Remover PDF", command=self.remover_documento, width=15,
                  font=("Arial", 11)).pack(side="left",
                                           padx=2)
        tk.Button(f_controles_arq, text="Subir", command=self.mover_cima, width=8, font=("Arial", 11)).pack(side="left",
                                                                                                            padx=10)
        tk.Button(f_controles_arq, text="Descer", command=self.mover_baixo, width=8, font=("Arial", 11)).pack(
            side="left", padx=2)

        tk.Button(f_dir, text="💾 Salvar Alterações deste Subitem", command=self.salvar_subitem, bg="#f39c12",
                  fg="white", font=("Arial", 14, "bold"), pady=5).pack(fill="x", pady=(10, 0))

        f_base = tk.LabelFrame(container, text="Ações de Consolidação e Entrega", padx=15, pady=15)
        f_base.pack(fill="x", pady=(10, 0))

        tk.Checkbutton(f_base,
                       text="Aplicar Máxima Compressão (Aviso: Pode degradar qualidade visual de plantas/imagens)",
                       variable=self.var_compressao_maxima, fg="red", font=("Arial", 12, "bold")).pack(anchor="w",
                                                                                                       pady=(0, 10))

        f_botoes = tk.Frame(f_base)
        f_botoes.pack(fill="x")

        self.btn_salvar_docs = tk.Button(f_botoes, text="Higienizar Arquivos e Consolidar PDFs",
                                         command=self.processamento_final_completo, bg="#27ae60", fg="white",
                                         font=("Arial", 14, "bold"), pady=8)
        self.btn_salvar_docs.pack(fill="x")

    def trocar_entidade(self, event=None):
        self.entidade_atual = self.combo_empresas.get()
        self.categoria_atual = ""
        self.subitem_atual = ""
        self.arquivos_temp = []
        self.lbl_subitem_titulo.config(text="Selecione uma categoria ou subitem na lista")
        self.listbox_docs.delete(0, tk.END)
        self.var_nao_aplica.set(False)
        self.atualizar_treeview()

    def atualizar_treeview(self):
        self.tree.delete(*self.tree.get_children())
        if not self.entidade_atual: return

        if self.entidade_atual == self.STR_UNIFICADO:
            dados_str = self.estrutura['unificado']
        else:
            dados_str = self.estrutura['individual']

        estado_ent = self.estado_projeto["dados"][self.entidade_atual]

        for cat, subitens in dados_str.items():
            id_cat = self.tree.insert("", "end", text=cat, open=True)
            for sub in subitens.keys():
                estado_sub = estado_ent[cat][sub]

                if estado_sub["nao_aplica"]:
                    icone = "[N/A]"
                elif len(estado_sub["arquivos"]) > 0:
                    icone = "[ OK ]"
                else:
                    icone = "[    ]"

                self.tree.insert(id_cat, "end", text=f"{icone} {sub}", values=(cat, sub))

    def ao_selecionar_treeview(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])

        if not item['values']:
            self.categoria_atual = item['text']
            self.subitem_atual = ""
            self.lbl_subitem_titulo.config(text=f"Categoria Selecionada: {self.categoria_atual}")
            self.arquivos_temp = []
            self.var_nao_aplica.set(False)
            self.listbox_docs.delete(0, tk.END)
            return

        self.categoria_atual = item['values'][0]
        self.subitem_atual = item['values'][1]
        self.lbl_subitem_titulo.config(text=self.subitem_atual)

        estado_sub = self.estado_projeto["dados"][self.entidade_atual][self.categoria_atual][self.subitem_atual]

        self.arquivos_temp = list(estado_sub["arquivos"])
        self.var_nao_aplica.set(estado_sub["nao_aplica"])

        self.listbox_docs.delete(0, tk.END)
        for arq in self.arquivos_temp:
            self.listbox_docs.insert(tk.END, os.path.basename(arq))

    def mostrar_info(self):
        if not self.categoria_atual and not self.subitem_atual:
            messagebox.showwarning("Aviso", "Selecione uma categoria ou subitem na lista primeiro.")
            return

        if not self.subitem_atual:
            msg = self.textos_categorias.get(self.categoria_atual, "Instrução geral não definida para este item.")
            titulo = self.categoria_atual
        else:
            if self.entidade_atual == self.STR_UNIFICADO:
                msg = self.estrutura['unificado'][self.categoria_atual][self.subitem_atual]
            else:
                msg = self.estrutura['individual'][self.categoria_atual][self.subitem_atual]
            titulo = self.subitem_atual

        messagebox.showinfo(f"Instrução Normativa: {titulo}", msg)

    def drop_documentos(self, event):
        arquivos = self.root.tk.splitlist(event.data)
        self._inserir_documentos_logica(arquivos)

    def adicionar_documentos(self):
        arquivos = filedialog.askopenfilenames(title="Selecione PDFs", filetypes=[("PDF", "*.pdf")])
        self._inserir_documentos_logica(arquivos)

    def _inserir_documentos_logica(self, arquivos):
        if not self.subitem_atual:
            messagebox.showwarning("Aviso",
                                   "Você selecionou um Título/Categoria. Para adicionar um arquivo, clique no Subitem desejado (abaixo do título).")
            return

        for arq in arquivos:
            arq_limpo = os.path.normpath(arq)
            if arq_limpo.lower().endswith(".pdf") and arq_limpo not in self.arquivos_temp:
                self.arquivos_temp.append(arq_limpo)
                self.listbox_docs.insert(tk.END, os.path.basename(arq_limpo))

        self.var_nao_aplica.set(False)

    def remover_documento(self):
        sel = self.listbox_docs.curselection()
        if sel and self.subitem_atual:
            idx = sel[0]
            self.listbox_docs.delete(idx)
            self.arquivos_temp.pop(idx)

    def mover_cima(self):
        sel = self.listbox_docs.curselection()
        if not sel or not self.subitem_atual or sel[0] == 0: return
        idx = sel[0]

        self.arquivos_temp[idx - 1], self.arquivos_temp[idx] = self.arquivos_temp[idx], self.arquivos_temp[idx - 1]

        texto = self.listbox_docs.get(idx)
        self.listbox_docs.delete(idx)
        self.listbox_docs.insert(idx - 1, texto)
        self.listbox_docs.selection_set(idx - 1)

    def mover_baixo(self):
        sel = self.listbox_docs.curselection()
        if not sel or not self.subitem_atual: return
        idx = sel[0]
        if idx == len(self.arquivos_temp) - 1: return

        self.arquivos_temp[idx + 1], self.arquivos_temp[idx] = self.arquivos_temp[idx], self.arquivos_temp[idx + 1]

        texto = self.listbox_docs.get(idx)
        self.listbox_docs.delete(idx)
        self.listbox_docs.insert(idx + 1, texto)
        self.listbox_docs.selection_set(idx + 1)

    def salvar_subitem(self):
        if not self.subitem_atual:
            messagebox.showwarning("Aviso", "Selecione um subitem válido na árvore para salvar as edições.")
            return

        estado_sub = self.estado_projeto["dados"][self.entidade_atual][self.categoria_atual][self.subitem_atual]
        estado_sub["arquivos"] = list(self.arquivos_temp)
        estado_sub["nao_aplica"] = self.var_nao_aplica.get()

        self.salvar_json()
        self.atualizar_treeview()
        messagebox.showinfo("Sucesso", f"Alterações salvas para o subitem:\n{self.subitem_atual}")

    # ==========================================
    # EXPORTAÇÃO, SANITIZAÇÃO E CONSOLIDAÇÃO FINAL
    # ==========================================
    def processamento_final_completo(self):
        self.salvar_json()
        self.btn_salvar_docs.config(state=tk.DISABLED, text="Iniciando Arrasto de Segurança e Consolidação...")
        threading.Thread(target=self._tarefa_processamento, daemon=True).start()

    def _tarefa_processamento(self):
        try:
            compressao_max = self.var_compressao_maxima.get()
            total_arquivos_gerados = 0
            mun_nome = self.estado_projeto['municipio']
            mun_limpo = self.formatar_nome(mun_nome)

            relatorio_linhas = []
            relatorio_linhas.append("RELATÓRIO GERAL DE PENDÊNCIAS - PIAA 2026")
            relatorio_linhas.append(f"Município do Processo: {mun_nome}")
            relatorio_linhas.append("=" * 80 + "\n")

            ordem_entidades = [self.STR_UNIFICADO] + self.estado_projeto["empresas"]

            for entidade in ordem_entidades:
                categorias = self.estado_projeto["dados"].get(entidade, {})
                if not categorias: continue

                if entidade == self.STR_UNIFICADO:
                    entidade_limpa = self.PASTA_UNIFICADO
                    nome_consolidador = "ITENS_UNIFICADOS_Consolidado.pdf"
                    prefixo_empresa = ""
                else:
                    entidade_limpa = self.formatar_nome(entidade)
                    nome_consolidador = f"{entidade_limpa}_Consolidado.pdf"
                    prefixo_empresa = self._obter_prefixo_empresa(entidade)

                pasta_entidade = self._obter_caminho_seguro(os.path.join(self.pasta_raiz_projeto, entidade_limpa))

                doc_consolidado = fitz.open()
                faltantes_entidade = []

                for cat, subitens in categorias.items():
                    pasta_cat = self._obter_caminho_seguro(os.path.join(pasta_entidade, cat))
                    pasta_cat_criada = False

                    # Ex: "Item 1 - Manifestação de Interesse" -> "1"
                    cat_num = cat.split()[1]

                    if " - " in cat:
                        cat_limpa = self.formatar_nome(cat.split(" - ", 1)[1])
                    else:
                        cat_limpa = self.formatar_nome(cat)

                    for subitem_str, estado_sub in subitens.items():

                        if not estado_sub["nao_aplica"] and len(estado_sub["arquivos"]) == 0:
                            faltantes_entidade.append(f"{cat} -> {subitem_str}")

                        if estado_sub["nao_aplica"]:
                            continue

                        arquivos = estado_sub["arquivos"]
                        if not arquivos:
                            continue

                        # Limpeza do nome do subitem: Remove código "X.X - " e os "(X.X.X)" do final
                        nome_sub_str = subitem_str
                        if " - " in nome_sub_str:
                            nome_sub_str = nome_sub_str.split(" - ", 1)[1]
                        nome_sub_str = re.sub(r'\(.*?\)', '', nome_sub_str).strip()
                        sub_limpo = self.formatar_nome(nome_sub_str)

                        contador_arquivo_sub = 1

                        for arq_origem in arquivos:
                            if not pasta_cat_criada:
                                os.makedirs(pasta_cat, exist_ok=True)
                                pasta_cat_criada = True

                            # ==========================================
                            # CONSTRUÇÃO EXATA DA REGRA DE NOME
                            # ==========================================
                            if entidade == self.STR_UNIFICADO:
                                # Regra: "3 Orcamento e Cronograma 01.pdf"
                                nome_final = f"{cat_num} {sub_limpo} {contador_arquivo_sub:02d}.pdf"
                            else:
                                if cat_num == "1":
                                    nome_final = f"{prefixo_empresa} - {cat_limpa} - {sub_limpo} {contador_arquivo_sub:02d}.pdf"
                                elif cat_num == "5":
                                    nome_final = f"{prefixo_empresa} - {cat_limpa} {contador_arquivo_sub:02d}.pdf"
                                elif cat_num == "9":
                                    nome_final = f"{prefixo_empresa} - CADIN {contador_arquivo_sub:02d}.pdf"
                                else:
                                    # Para 2, 7, 8
                                    nome_final = f"{prefixo_empresa} - {sub_limpo} {contador_arquivo_sub:02d}.pdf"

                            caminho_final = self._obter_caminho_seguro(os.path.join(pasta_cat, nome_final))
                            caminho_temp = self._obter_caminho_seguro(
                                caminho_final + ".tmp.pdf") if compressao_max else caminho_final

                            doc_temp = self._abrir_pdf_seguro(arq_origem)
                            self._blindagem_sanitizacao(doc_temp, doc_consolidado)

                            doc_avulso = fitz.open()
                            self._blindagem_sanitizacao(doc_temp, doc_avulso)
                            self._limpeza_final(doc_avulso)

                            try:
                                doc_avulso.save(caminho_temp, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                            except:
                                doc_avulso.save(caminho_temp, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
                            doc_avulso.close()
                            doc_temp.close()

                            if compressao_max:
                                self._comprimir_com_ghostscript(caminho_temp, caminho_final)
                                if os.path.exists(caminho_temp): os.remove(caminho_temp)

                            contador_arquivo_sub += 1
                            total_arquivos_gerados += 1

                if len(doc_consolidado) > 0:
                    caminho_consol = self._obter_caminho_seguro(os.path.join(pasta_entidade, nome_consolidador))
                    caminho_temp_consol = self._obter_caminho_seguro(
                        caminho_consol + ".tmp.pdf") if compressao_max else caminho_consol

                    self._limpeza_final(doc_consolidado)
                    try:
                        doc_consolidado.save(caminho_temp_consol, garbage=4, deflate=True,
                                             encryption=fitz.PDF_ENCRYPT_NONE)
                    except:
                        doc_consolidado.save(caminho_temp_consol, garbage=3, deflate=True,
                                             encryption=fitz.PDF_ENCRYPT_NONE)
                    doc_consolidado.close()

                    if compressao_max:
                        self._comprimir_com_ghostscript(caminho_temp_consol, caminho_consol)
                        if os.path.exists(caminho_temp_consol): os.remove(caminho_temp_consol)

                relatorio_linhas.append(f"Entidade: {entidade}")
                relatorio_linhas.append("-" * 60)
                if not faltantes_entidade:
                    relatorio_linhas.append(
                        "Status: COMPLETO. Todos os subitens obrigatórios possuem arquivos ou foram isentados (N/A).\n")
                else:
                    relatorio_linhas.append("ATENÇÃO: Faltam documentos nos seguintes subitens obrigatórios:")
                    for pendencia in faltantes_entidade:
                        relatorio_linhas.append(f"  [PENDENTE] {pendencia}")
                    relatorio_linhas.append("\n")

            caminho_relatorio = self._obter_caminho_seguro(
                os.path.join(self.pasta_raiz_projeto, f"Relatorio_Pendencias_{mun_limpo}.txt"))
            with open(caminho_relatorio, "w", encoding="utf-8") as f:
                f.write("\n".join(relatorio_linhas))

            self.root.after(0, self._finalizacao_sucesso,
                            f"Operação Estrutural Completa!\n\nForam higienizados, organizados nas pastas e consolidados {total_arquivos_gerados} arquivos no padrão PROA.")
        except Exception as e:
            self.root.after(0, self._finalizacao_erro, str(e))

    def _finalizacao_sucesso(self, mensagem):
        self.btn_salvar_docs.config(state=tk.NORMAL, text="Higienizar Arquivos e Consolidar PDFs")
        messagebox.showinfo("Sucesso Absoluto", mensagem)

    def _finalizacao_erro(self, erro):
        self.btn_salvar_docs.config(state=tk.NORMAL, text="Higienizar Arquivos e Consolidar PDFs")
        messagebox.showerror("Erro Crítico", f"Falha durante o arrastão final:\n{erro}")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = Piaa2026AppV2(root)
    root.mainloop()
