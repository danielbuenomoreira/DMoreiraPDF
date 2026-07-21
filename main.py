import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import webbrowser
import json
import os
from tkinterdnd2 import TkinterDnD

from aba_juntar import AbaJuntar
from aba_dividir import AbaDividir
from aba_lotes import AbaLotes
from aba_renomear import AbaRenomear
from aba_html_pdf import AbaHtmlPdf
from pdf_motor import resource_path

# Caminho do arquivo de configuração (Salvo na pasta de usuário do Windows)
ARQUIVO_CONFIG = os.path.join(os.path.expanduser("~"), "DMoreiraPDF_config.json")

def carregar_tema():
    """Lê o tema salvo no arquivo de configuração, se existir."""
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return dados.get("tema", "flatly")
        except:
            pass
    return "flatly"

def salvar_tema(tema):
    """Salva o tema escolhido no arquivo de configuração."""
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"tema": tema}, f, ensure_ascii=False, indent=4)
    except:
        pass


class AppPrincipal:
    def __init__(self, root, style):
        self.root = root
        self.style = style
        self.root.title("DMoreiraPDF v4.0")
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)
        self.root.resizable(True, True)
        try:
            self.root.iconbitmap(resource_path("DMoreiraPDF.ico"))
        except:
            pass

        # Cria o Notebook (abas) usando o estilo do ttkbootstrap
        self.notebook = tb.Notebook(self.root, bootstyle="info")
        self.notebook.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Instanciação modular
        self.aba_juntar = AbaJuntar(self.notebook, self.root)
        self.aba_dividir = AbaDividir(self.notebook, self.root)
        self.aba_lotes = AbaLotes(self.notebook, self.root)
        self.aba_renomear = AbaRenomear(self.notebook, self.root)
        self.aba_html_pdf = AbaHtmlPdf(self.notebook, self.root)

        # Rodapé reestruturado para suportar o seletor de temas
        rodape = tb.Frame(self.root)
        rodape.pack(side=BOTTOM, fill=X, padx=20, pady=10)

        # Esquerda do rodapé (Créditos)
        f_dev = tb.Frame(rodape)
        f_dev.pack(side=LEFT)
        tb.Label(f_dev, text="Desenvolvido por ", font=("Segoe UI", 11)).pack(side=LEFT)
        link = tb.Label(f_dev, text="@danielbuenomoreiradev", cursor="hand2", font=("Arial", 11, "bold"),
                        bootstyle="primary")
        link.pack(side=LEFT)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://danielbuenomoreira.github.io/QuemSouEu/"))

        # Direita do rodapé (Seletor de Temas)
        f_tema = tb.Frame(rodape)
        f_tema.pack(side=RIGHT)
        tb.Label(f_tema, text="Tema Visual:", font=("Segoe UI", 11)).pack(side=LEFT, padx=5)

        # Combobox que puxa automaticamente todos os temas instalados
        self.combo_tema = tb.Combobox(f_tema, values=self.style.theme_names(), state="readonly", width=15)
        self.combo_tema.set(self.style.theme.name)  # Define o tema atual como valor inicial
        self.combo_tema.pack(side=LEFT)

        # Evento que dispara a troca de tema ao selecionar uma nova opção
        self.combo_tema.bind("<<ComboboxSelected>>", self.mudar_tema)

    def mudar_tema(self, event):
        novo_tema = self.combo_tema.get()
        self.style.theme_use(novo_tema)

        # Reaplica as configurações de fonte logo após a troca de tema para não serem sobrescritas
        self.style.configure('.', font=('Segoe UI', 11))
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 12, 'bold'))

        # Salva a escolha do usuário
        salvar_tema(novo_tema)

        # Dispara o evento virtual para as abas atualizarem componentes nativos
        self.root.event_generate("<<ThemeChanged>>")


if __name__ == "__main__":
    root_tk = TkinterDnD.Tk()

    # Identifica e carrega o último tema salvo pelo usuário
    tema_inicial = carregar_tema()

    # Aplica o tema
    style = tb.Style(theme=tema_inicial)

    # Configurações globais de fonte (aplicadas na inicialização)
    style.configure('.', font=('Segoe UI', 11))
    style.configure('TNotebook.Tab', font=('Segoe UI', 12, 'bold'))

    # Passa o style como argumento para o AppPrincipal
    app = AppPrincipal(root_tk, style)
    root_tk.mainloop()
