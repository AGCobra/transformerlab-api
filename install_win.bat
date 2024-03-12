@echo off

set ENV_NAME=transformerlab
set TLAB_DIR=%HOME%\.transformerlab
set TLAB_CODE_DIR=%TLAB_DIR%\%src

@rem deactivate existing conda envs as needed to avoid conflicts
(call conda deactivate && call conda deactivate && call conda deactivate) 2>nul

@rem Check if there are arguments to this script, and if so, run the appropriate function.
if [%1]==[] (
  @rem title "Performing a full installation of Transformer Lab."
  call :download_transformer_lab
  call :install_conda
  call :create_conda_environment
  call :install_dependencies
  call :print_success_message
) else (
  call :%1
  @rem TODO fix emoji
  if ERRORLEVEL 1 echo ❌ Unknown argument: %1
)

:end
EXIT /B %ERRORLEVEL%


:: ---------------------------------------- INSTALLATION STEPS -------------------------------------

:title
@rem TODO Remove all of the commented lines
echo TITLE
:: printf "%tty_blue%#########################################################################%tty_reset%\n"
:: SET _INTERPOLATION_0=
:: FOR /f "delims=" %%a in ('shell_join "$@"') DO (SET "_INTERPOLATION_0=!_INTERPOLATION_0! %%a")
:: printf "%tty_blue%#### %tty_bold% %s%tty_reset%\n" "!_INTERPOLATION_0:~1!"
:: printf "!tty_blue!#########################################################################!tty_reset!\n"
EXIT /B 0

:download_transformer_lab
echo downloading transformer lab
EXIT /B 0

:install_conda
echo installing conda
EXIT /B 0

:create_conda_environment
echo creating conda environemtn
EXIT /B 0

:install_dependencies
echo installing dependencies
EXIT /B 0

:print_success_message
title "Installation Complete"
echo ------------------------------------------
echo Transformer Lab is installed to:
echo   %TLAB_DIR%
echo Your workspace is located at:
echo   %TLAB_DIR%\workspace
echo Your conda environment is at:
echo   %ENV_DIR%
echo You can run Transformer Lab with:
echo   conda activate %ENV_DIR%
echo   %TLAB_DIR%\src\run.bat
echo ------------------------------------------
echo
EXIT /B 0