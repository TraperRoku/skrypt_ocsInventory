import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import sys
import datetime
import configparser 

def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
        
        db_config = {
            'host': config['database']['host'],
            'user': config['database']['user'],
            'password': config['database']['password'],
            'database': config['database']['database']
        }

        email_config = {
            'sender_email': config['email']['sender_email'],
            'sender_name': config['email']['sender_name'],
            'recipient_email': config['email']['recipient_email'],
            'smtp_server': config['email']['smtp_server'],
            'smtp_port': int(config['email']['smtp_port']), 
            'use_tls': config['email'].getboolean('use_tls'), 
            'smtp_username': config['email']['smtp_username'],
            'smtp_password': config['email']['smtp_password']
        }
        return db_config, email_config
    except KeyError as e:
        print(f"Blad konfiguracji: Brak wymaganego klucza w pliku '{config_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Blad: Plik konfiguracyjny '{config_file}' nie zostal znaleziony.", file=sys.stderr)
        print("Upewnij sie, ze 'config.ini' istnieje i jest poprawnie skonfigurowany.")
        print("Mozesz utworzyc go na podstawie 'config.ini.defaults'.")
        sys.exit(1)
    except ValueError as e:
        print(f"Blad wartosci w pliku '{config_file}': {e}", file=sys.stderr)
        sys.exit(1)


def get_db_connection(db_config): 
    try:
        conn = mysql.connector.connect(**db_config)
        print("Udalo sie polaczyc z baza danych.")
        return conn
    except mysql.connector.Error as err:
        print(f"Blad polaczenia z baza danych: {err}", file=sys.stderr)
        sys.exit(1)

def create_software_history_table(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `detected_software_history` (
                `software_name` VARCHAR(255) NOT NULL UNIQUE,
                `first_detected_on_computer` VARCHAR(255) NULL,
                `first_detected_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`software_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        conn.commit()
        print("Tabela 'detected_software_history' zostala utworzona lub juz istnieje.")
    except mysql.connector.Error as err:
        print(f"Blad podczas tworzenia tabeli 'detected_software_history': {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()

def populate_initial_history(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM detected_software_history")
        count = cursor.fetchone()[0]
        print(f"Aktualna liczba rekordow w detected_software_history: {count}")

        if count == 0:
            print("Tabela detected_software_history jest pusta. Wypelniam danymi o wszystkich unikalnych programach z OCS i komputerach, na ktorych je wykryto po raz pierwszy.")
            
            cursor.execute("""
                INSERT IGNORE INTO detected_software_history (software_name, first_detected_on_computer)
                SELECT
                    sn.NAME AS software_name,
                    MIN(h.NAME) AS first_detected_on_computer
                FROM
                    software s
                JOIN
                    software_name sn ON s.NAME_ID = sn.ID
                JOIN
                    hardware h ON s.HARDWARE_ID = h.ID
                GROUP BY
                    sn.NAME;
            """)
            conn.commit()
            print(f"Dodano {cursor.rowcount} unikalnych nazw oprogramowania z komputerami pierwszego wykrycia do tabeli historii.")
        else:
            print("Tabela detected_software_history zawiera juz dane. Pomijam wypelnianie poczatkowe.")
    except mysql.connector.Error as err:
        print(f"Blad podczas wypelniania poczatkowej historii oprogramowania: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()

def get_new_software_report(conn):
    cursor = conn.cursor(dictionary=True)
    new_software_for_report = {}
    
    try:
        cursor.execute("SELECT software_name FROM detected_software_history")
        historical_unique_software_names = {row['software_name'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT
                s.HARDWARE_ID,
                sn.NAME AS software_name,
                h.NAME AS computer_name
            FROM
                software s
            JOIN
                hardware h ON s.HARDWARE_ID = h.ID
            JOIN
                software_name sn ON sn.ID = s.NAME_ID;
        """)
        current_software_scan = cursor.fetchall()
        
        first_detected_computer_for_new_software = {} 
        current_unique_software_names = set()

        for item in current_software_scan:
            software_name = item['software_name']
            computer_name = item['computer_name']
            hardware_id = item['HARDWARE_ID']
            
            current_unique_software_names.add(software_name)

            if software_name not in historical_unique_software_names and software_name not in first_detected_computer_for_new_software:
                first_detected_computer_for_new_software[software_name] = {
                    'name': computer_name,
                    'id': hardware_id
                }

        global_new_software = current_unique_software_names - historical_unique_software_names

        if global_new_software:
            print(f"Wykryto {len(global_new_software)} globalnie nowych programow.")
            
            updates_to_history = []
            for software_name in global_new_software:
                if software_name in first_detected_computer_for_new_software:
                    new_software_for_report[software_name] = {
                        'first_computer_name': first_detected_computer_for_new_software[software_name]['name'],
                        'first_computer_id': first_detected_computer_for_new_software[software_name]['id']
                    }
                    updates_to_history.append((
                        software_name, 
                        first_detected_computer_for_new_software[software_name]['name']
                    ))
                else:
                    new_software_for_report[software_name] = {
                        'first_computer_name': 'N/A',
                        'first_computer_id': 'N/A'
                    }
                    updates_to_history.append((software_name, 'N/A'))
            
            insert_query = "INSERT IGNORE INTO `detected_software_history` (`software_name`, `first_detected_on_computer`) VALUES (%s, %s)"
            cursor.executemany(insert_query, updates_to_history)
            conn.commit()
            print(f"Dodano {cursor.rowcount} nowych unikalnych programow z komputerami pierwszego wykrycia do tabeli historii.")
        else:
            print("Brak globalnie nowego oprogramowania do raportowania.")

    except mysql.connector.Error as err:
        print(f"Blad podczas pobierania lub aktualizacji nowego oprogramowania: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()

    return new_software_for_report

def get_removed_software_report(conn):
    cursor = conn.cursor(dictionary=True) 
    removed_software_names = set() 

    try:
        cursor.execute("""
            SELECT software_name
            FROM detected_software_history;
        """)
        historical_unique_software = {row['software_name'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT DISTINCT sn.NAME AS software_name
            FROM software s
            JOIN software_name sn ON s.NAME_ID = sn.ID;
        """)
        current_unique_software = {row['software_name'] for row in cursor.fetchall()}

        software_globally_removed = historical_unique_software - current_unique_software

        if software_globally_removed:
            print(f"Wykryto {len(software_globally_removed)} programow globalnie usunietych z infrastruktury (do raportu).")
            removed_software_names.update(software_globally_removed)
        else:
            print("Brak programow globalnie usunietych z infrastruktury (do raportu).")

    except mysql.connector.Error as err:
        print(f"Blad podczas pobierania usunietego oprogramowania: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()

    return list(removed_software_names)

def send_email_report(new_software_data, email_config): 
    report_lines = []
    subject_parts = []
    
    if new_software_data:
        report_lines.append("Wykryto globalnie nowe oprogramowanie w infrastrukturze OCS Inventory NG:")
        report_lines.append("-" * 50)
        sorted_new_software = sorted(new_software_data.items(), key=lambda item: item[0].lower())
        for software_key, data in sorted_new_software:
            report_lines.append(f"Program: {software_key} (NOWY w INFRASTRUKTURZE)")
            report_lines.append(f"  Wykryto po raz pierwszy na komputerze: {data['first_computer_name']} | ID: {data['first_computer_id']}")
            report_lines.append("")
        subject_parts.append("[NOWE OPROGRAMOWANIE]")

    if not report_lines:
        print("Brak nowego oprogramowania do raportowania e-mailem.")
        return

    report_content = "\n".join(report_lines)

    if not subject_parts:
        subject = f"Raport OCS Inventory NG - {datetime.date.today().strftime('%Y-%m-%d')}"
    else:
        subject = f"{' '.join(subject_parts)} Raport OCS Inventory NG - {datetime.date.today().strftime('%Y-%m-%d')}"

    msg = MIMEText(report_content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = Header(f"{email_config['sender_name']} <{email_config['sender_email']}>", 'utf-8')
    msg['To'] = email_config['recipient_email']

    try:
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        if email_config['use_tls']:
            server.starttls()

        if 'smtp_username' in email_config and email_config['smtp_username']:
            server.login(email_config['smtp_username'], email_config['smtp_password'])

        server.sendmail(email_config['sender_email'], email_config['recipient_email'], msg.as_string())
        server.quit()
        print(f"Raport e-mailowy zostal wyslany na adres {email_config['recipient_email']}")
    except Exception as e:
        print(f"Blad podczas wysylania e-maila: {e}", file=sys.stderr)
        sys.exit(1)

def cleanup_removed_software_history(conn, removed_software_names_to_clean):
    cursor = conn.cursor() 
    try:
        if removed_software_names_to_clean:
            delete_query = "DELETE FROM detected_software_history WHERE software_name = %s;"
            data_to_delete = [(s,) for s in removed_software_names_to_clean]
            
            print(f"Zostanie usunietych {len(data_to_delete)} globalnie usunietych programow z historii: {', '.join(removed_software_names_to_clean)}")
            
            cursor.executemany(delete_query, data_to_delete)
            conn.commit()
            print(f"Usunieto {cursor.rowcount} rekordow z detected_software_history dla globalnie usunietych programow.")
        else:
            print("Brak globalnie usunietych programow do usuniecia z historii.")

    except mysql.connector.Error as err:
        print(f"Blad podczas czyszczenia historii oprogramowania: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()

def main():
    db_config, email_config = load_config() 
    conn = None
    try:
        conn = get_db_connection(db_config) 
        create_software_history_table(conn)
        populate_initial_history(conn) 

        removed_software_for_report = get_removed_software_report(conn)
        if removed_software_for_report:
            print("\nNastepujace programy zostaly globalnie usuniete z infrastruktury:")
            for software_name in removed_software_for_report:
                print(f"  - {software_name}")
            
        new_software_for_report = get_new_software_report(conn)
        if new_software_for_report:
            print("\nWykryto globalnie nowe oprogramowanie:")
            for software_key, data in new_software_for_report.items():
                print(f"  - {software_key} (NOWY w INFRASTRUKTURZE) wykryty na komputerze: {data['first_computer_name']} (ID: {data['first_computer_id']})")
        else:
            print("Brak globalnie nowego oprogramowania do raportowania.")

        if new_software_for_report:
            send_email_report(new_software_for_report, email_config) 
        else:
            print("Brak nowego oprogramowania do wyslania raportu e-mailowego.")
        
        cleanup_removed_software_history(conn, removed_software_for_report)

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
