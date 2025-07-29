#!/bin/bash

SCRIPT_NAME="ocs_reporter.py"
CONFIG_DEFAULT_NAME="config.ini.defaults"
CONFIG_NAME="config.ini"
LOG_FILE="$HOME/ocs_report.log" 

echo "--- Rozpoczynanie instalacji i konfiguracji OCS Inventory Reporter ---"


echo "1. Sprawdzanie dostepnosci interpretera Python 3..."
if ! command -v python3 &> /dev/null
then
    echo "Blad: Interpreter 'python3' nie zostal znaleziony."
    echo "Upewnij sie, ze Python 3 jest zainstalowany i znajduje sie w sciezce systemowej."
    exit 1
fi
PYTHON_PATH=$(which python3)
echo "Znaleziono Python 3: $PYTHON_PATH"




echo "2. Konfiguracja zadania cron..."
CURRENT_DIR=$(pwd)
SCRIPT_FULL_PATH="$CURRENT_DIR/$SCRIPT_NAME"

CRON_JOB="0 8 * * * $PYTHON_PATH $SCRIPT_FULL_PATH >> $LOG_FILE 2>&1"

echo "Nastepujacy wpis zostanie dodany/zweryfikowany w crontab (codziennie o 8:00):"
echo "$CRON_JOB"
echo ""

(crontab -l 2>/dev/null | grep -Fq "$CRON_JOB")
if [ $? -eq 0 ]; then
    echo "Wpis cron juz istnieje. Nie zmieniam."
else
    echo "Dodawanie wpisu cron..."
    # Uzywamy (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    # aby bezpiecznie dodac nowa linie, zachowujac istniejace wpisy
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    if [ $? -eq 0 ]; then
        echo "Wpis cron dodany pomyslnie."
    else
        echo "Blad podczas dodawania wpisu cron. Sprawdz uprawnienia lub logi systemowe."
        exit 1
    fi
fi

echo "--- Konfiguracja zakonczona! ---"
echo "Raporty beda wysylane codziennie o 8:00."
echo "Logi wykonania skryptu znajdziesz w pliku: $LOG_FILE"
echo ""
echo "Wazne: Upewnij sie, ze plik '$CONFIG_NAME' jest poprawnie uzupelniony!"
