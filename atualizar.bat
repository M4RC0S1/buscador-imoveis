@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Atualizando imoveis - Daros

set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo Python nao foi encontrado. Siga o passo 1 do README.md para instalar.
  pause
  exit /b 1
)

echo Verificando dependencias...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Nao consegui instalar as dependencias. Verifique sua internet.
  pause
  exit /b 1
)

echo.
echo Coletando imoveis (leva alguns minutos, o programa espera entre as paginas de proposito)...
%PY% coletor.py
set RESULTADO=%errorlevel%

echo.
if "%RESULTADO%"=="0" (echo PRONTO! Agora abra o arquivo buscar.html) else (echo A atualizacao falhou - a lista anterior foi mantida. Veja coletor.log)
if /i not "%~1"=="auto" pause
exit /b %RESULTADO%
