@echo off
:: Altera a paginação de código para UTF-8 para aceitar acentos no nome do atalho
chcp 65001 >nul

:: ==========================================================
:: VARIÁVEIS DE CONFIGURAÇÃO (Altere estas 3 linhas para outros programas)
:: ==========================================================
set "NOME_ATALHO=Organizador PIAA 2026.lnk"
set "PASTA_PROGRAMA=Piaa2026_2.1"
set "NOME_EXECUTAVEL=Piaa2026_2.1.exe"
:: ==========================================================

:: O %~dp0 pega o caminho exato de onde este .bat está sendo executado
set "CAMINHO_EXE=%~dp0%PASTA_PROGRAMA%\%NOME_EXECUTAVEL%"
set "CAMINHO_TRABALHO=%~dp0%PASTA_PROGRAMA%"
set "CAMINHO_ATALHO=%USERPROFILE%\Desktop\%NOME_ATALHO%"

:: Verifica se o executável realmente está lá antes de criar o atalho
if not exist "%CAMINHO_EXE%" (
    echo ERRO: Arquivo nao encontrado!
    echo Certifique-se de que extraiu a pasta "%PASTA_PROGRAMA%" no mesmo local deste arquivo.
    pause
    exit
)

:: Usa o PowerShell em segundo plano para criar um atalho perfeito (.lnk)
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%CAMINHO_ATALHO%'); $s.TargetPath='%CAMINHO_EXE%'; $s.WorkingDirectory='%CAMINHO_TRABALHO%'; $s.Save()"

:: Autoexclusão: O script deleta a si mesmo após terminar o serviço
del "%~f0"