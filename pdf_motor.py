import fitz  # PyMuPDF
import os
import ctypes
import unicodedata
import re
import subprocess
import sys

def resource_path(relative_path):
    """Permite localizar arquivos embutidos pelo PyInstaller na pasta temporária _MEIPASS"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class PDFMotor:
    @staticmethod
    def obter_caminho_seguro(caminho):
        """Converte caminhos gigantes no formato curto 8.3 do Windows para burlar MAX_PATH."""
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

    @staticmethod
    def formatar_nome(nome_original):
        """Remove acentos e caracteres especiais indesejados."""
        nome = unicodedata.normalize('NFKD', nome_original).encode('ASCII', 'ignore').decode('utf-8')
        nome = re.sub(r'[^a-zA-Z0-9\-_ ]', ' ', nome)
        nome = re.sub(r'\s+', ' ', nome).strip()
        return nome

    @staticmethod
    def abrir_pdf_ram(caminho):
        """Abre o PDF blindado na memória RAM, ignorando bloqueios de sistema."""
        caminho_seg = PDFMotor.obter_caminho_seguro(caminho)
        with open(caminho_seg, "rb") as f:
            pdf_bytes = f.read()
        doc = fitz.open("pdf", pdf_bytes)
        if doc.is_encrypted:
            doc.authenticate("")
        return doc

    @staticmethod
    def sanitizar(doc):
        """Destrói IRM, catálogos de segurança e achata assinaturas."""
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

    @staticmethod
    def salvar_e_comprimir(doc, caminho_destino, aplicar_compressao):
        """Salva o documento no disco e aplica compressão extrema via Ghostscript se requisitado."""
        caminho_seguro = PDFMotor.obter_caminho_seguro(caminho_destino)
        caminho_temp = PDFMotor.obter_caminho_seguro(caminho_destino + ".tmp.pdf") if aplicar_compressao else caminho_seguro

        try:
            doc.save(caminho_temp, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
        except:
            doc.save(caminho_temp, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()

        if aplicar_compressao:
            gs_exec = PDFMotor.obter_caminho_seguro(resource_path("gswin64c.exe"))
            comando = [
                gs_exec, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/screen", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={caminho_seguro}", caminho_temp
            ]
            subprocess.run(comando, check=True, creationflags=0x08000000)
            if os.path.exists(caminho_temp):
                os.remove(caminho_temp)
                