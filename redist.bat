@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo Instalador Python + Requirements
echo ========================================
echo.

REM Verifica se winget está disponível
winget --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERRO: winget nao encontrado. Certifique-se de que esta instalado.
    echo Baixe o App Installer da Microsoft Store.
    pause
    exit /b 1
)

echo Verificando se Python ja esta instalado...
python --version >nul 2>&1
if !errorlevel! equ 0 (
    echo Python ja esta instalado:
    python --version
    echo.
    set /p resposta="Deseja reinstalar? (s/n): "
    if /i "!resposta!" neq "s" (
        goto install_requirements
    )
)

echo Instalando Python via winget...
echo.
winget install Python.Python.3.12

if !errorlevel! neq 0 (
    echo ERRO: Falha ao instalar Python
    pause
    exit /b 1
)

echo.
echo Python instalado com sucesso!
echo.

REM Atualiza as variáveis de ambiente
echo Atualizando variaveis de ambiente...
call refreshenv >nul 2>&1

REM Aguarda um pouco para o sistema reconhecer o Python
timeout /t 3 /nobreak >nul

:install_requirements
echo Verificando se requirements.txt existe...
if not exist "requirements.txt" (
    echo.
    echo AVISO: requirements.txt nao encontrado no diretorio atual.
    echo Criando um exemplo de requirements.txt...
    echo.
    (
        echo # Exemplo de requirements.txt
        echo # Descomente e modifique conforme necessario:
        echo # requests==2.31.0
        echo # numpy==1.24.3
        echo # pandas==2.0.3
        echo # flask==2.3.2
    ) > requirements.txt
    echo requirements.txt de exemplo criado.
    echo Edite o arquivo e execute o script novamente.
    pause
    exit /b 0
)

echo requirements.txt encontrado!
echo.

REM Atualiza pip primeiro
echo Atualizando pip...
python -m pip install --upgrade pip

if !errorlevel! neq 0 (
    echo ERRO: Falha ao atualizar pip
    pause
    exit /b 1
)

echo.
echo Instalando pacotes do requirements.txt...
echo.
python -m pip install -r requirements.txt

if !errorlevel! neq 0 (
    echo ERRO: Falha ao instalar alguns pacotes do requirements.txt
    echo Verifique o arquivo e tente novamente.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Instalacao concluida com sucesso!
echo ========================================
echo.
echo Python instalado e pacotes do requirements.txt instalados.
echo.

REM Mostra informações finais
echo Informacoes da instalacao:
python --version
echo.
echo Pacotes instalados:
python -m pip list
echo.

echo Pressione qualquer tecla para sair...
pause >nul