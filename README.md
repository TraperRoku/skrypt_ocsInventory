-----

# Raport OCS Inventory

Ten skrypt Python (`ocs_reporter.py`) **automatycznie monitoruje i raportuje zmiany w oprogramowaniu** wykrytym przez OCS Inventory NG. Wysyła e-maile o **nowo zainstalowanym oprogramowaniu** i wyświetla w konsoli informacje o usuniętych programach.

-----

## Jak to działa?

1.  Skrypt łączy się z bazą danych OCS Inventory.
2.  Porównuje aktualnie wykryte oprogramowanie z historycznymi danymi.
3.  Generuje raporty o nowym oprogramowaniu (e-mail) i o usuniętym (konsola).
4.  Automatycznie aktualizuje historię oprogramowania.

-----

## Wymagania wstępne

  * **Linux** (dla skryptu `install.sh`).
  * **Python 3**.
  * **Dostęp do bazy danych MySQL/MariaDB** (OCS Inventory NG).
  * **Dostęp do serwera SMTP** (np. Gmail z hasłem aplikacji lub lokalny Postfix).

-----

## Używane biblioteki Pythona

Skrypt wykorzystuje kilka standardowych i zewnętrznych bibliotek Pythona do realizacji swoich funkcji:

    mysql.connector: Oficjalny sterownik MySQL/MariaDB dla Pythona, umożliwiający skryptowi łączenie się z bazą danych OCS Inventory NG i wykonywanie zapytań SQL.

## Szybkie uruchomienie

1.  **Sklonuj repozytorium:**

    ```bash
    git clone https://github.com/TraperRoku/skrypt_ocsInventory.git
    cd ocsInventoryProject
    ```

2.  **Uruchom instalator:**
    Skrypt `install.sh` skonfiguruje projekt, zainstaluje biblioteki i ustawi codzienne uruchamianie o **8:00 rano** przez `cron`.

    ```bash
    chmod +x install.sh
    sudo ./install.sh
    ```

    *Po uruchomieniu, **edytuj `config.ini`**, uzupełniając dane dostępowe do bazy danych OCS i konfigurację e-maila.*

3.  **Gotowe\!**
    Raporty będą wysyłane automatycznie. Logi znajdziesz w `ocs_report.log` w swoim katalogu domowym.

-----

## Dostosowywanie harmonogramu (opcjonalnie)

Aby zmienić godzinę lub częstotliwość raportów (np. co godzinę, co tydzień), edytuj wpis `cron` dla swojego użytkownika:

```bash
sudo crontab -e
```

Znajdź linię ze skryptem `ocs_reporter.py` i zmodyfikuj pięć pierwszych kolumn (`minuta` `godzina` `dzień_miesiąca` `miesiąc` `dzień_tygodnia`). Zapisz i zamknij plik.

-----
