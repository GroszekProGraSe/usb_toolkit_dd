#!/usr/bin/env python3
"""
usb_toolkit_prototyp.py

Rozbudowane narzędzie CLI do:
 - nagrywania ISO na pendrive (dd + pv)
 - backup/restore obrazu pendrive
 - wybór MBR/GPT
 - bezpieczny wybór urządzenia przez lsblk/lsusb
 - automatyczne montowanie partycji i wykrywanie systemu (sprawdzenie /etc)
 - wygenerowanie skryptu install_tailscale.sh na pulpicie środowiska live/persistent
 - (opcjonalne) chroot + instalacja tailscale (hardcore)
 - generowanie prostego docker-compose dla Nextcloud + MariaDB + nginx i zapis jako post-install file
 - generowanie JSON "agenta" i dopisanie funkcji z pliku txt post-install
 - wysyłka obrazu pendrive przez HTTP POST (multipart) lub zapis na serwer SSH

UWAGI:
 - Skrypt wykonuje operacje niszczące na dyskach. Uruchamiaj z rozwagą (sudo).
 - Wymaga: dd, pv, lsblk, lsusb, parted, mount, umount, ssh, scp, curl (opcjonalnie)

"""

import os
import sys
import subprocess
import shlex
import tempfile
import json
from datetime import datetime

# KONFIG
BACKUP_DIR = os.path.expanduser("~/usb_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
TMP_MNT_ROOT = "/tmp/usb_toolkit_mnt"
os.makedirs(TMP_MNT_ROOT, exist_ok=True)

# Pomocnicze
def run(cmd, capture=False, check=False):
    if isinstance(cmd, str):
        shell = True
    else:
        shell = False
    try:
        if capture:
            out = subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT, text=True)
            return out
        else:
            subprocess.check_call(cmd, shell=shell)
            return None
    except subprocess.CalledProcessError as e:
        print("❌ Błąd podczas wykonywania:", e)
        if capture:
            try:
                return e.output
            except Exception:
                return ""
        return None


def safe_input(prompt):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print()
        return ""

# Lista urządzeń
def list_devices():
    print("\n🔎 lsblk (urządzenia blokowe):")
    print(run(["lsblk", "-d", "-o", "NAME,SIZE,MODEL,TRAN"], capture=True) or "")
    print("\n🔎 lsusb (magiczne USB):")
    print(run(["lsusb"], capture=True) or "")

# Wybór urządzenia z walidacją
def select_device_interactive():
    list_devices()
    dev = safe_input("\n👉 Podaj ścieżkę urządzenia (np. /dev/sdX): ").strip()
    if not dev:
        return None
    if not os.path.exists(dev):
        print("❌ Urządzenie nie istnieje.")
        return None
    # upewnij się, że to block device
    if not os.path.exists(dev) or not os.stat(dev).st_mode & 0o600:
        # prosty test - plik powinien istnieć; głębsza walidacja pominięta
        pass
    return dev

# Mountowanie wszystkich partycji urządzenia do katalogu tymczasowego
def mount_device_partitions(dev):
    """Zamontuj wszystkie partycje z urządzenia /dev/sdX* do TMP_MNT_ROOT/<n>/* i zwróć listę mountpointów"""
    mounts = []
    # użyj lsblk do znalezienia partycji
    out = run(["lsblk", "-ln", "-o", "NAME,TYPE", dev], capture=True) if dev else ""
    if not out:
        # fallback: spróbuj odczytać partycje jako dev1 dev2
        print("⚠️ Nie udało się odczytać partycji przez lsblk. Proszę podać partycję (np. /dev/sdX1) ręcznie.")
        return mounts
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'part':
            part_name = parts[0]
            # jeśli dev to /dev/sdX, part_name może być sdX1
            if not part_name.startswith(os.path.basename(dev)):
                # gdy lsblk zwróci tylko nazwę, zbuduj ścieżkę
                part = f"/dev/{part_name}"
            else:
                part = f"/dev/{part_name}"
            if os.path.exists(part):
                mp = os.path.join(TMP_MNT_ROOT, os.path.basename(part))
                os.makedirs(mp, exist_ok=True)
                try:
                    run(["sudo", "mount", part, mp])
                    mounts.append(mp)
                    print(f"✅ Zamontowano {part} -> {mp}")
                except Exception as e:
                    print(f"⚠️ Nie udało się zamontować {part}: {e}")
    return mounts


def umount_all_mounts(mounts):
    for mp in mounts:
        try:
            run(["sudo", "umount", mp])
            print(f"✅ Odmontowano {mp}")
        except Exception as e:
            print(f"⚠️ Błąd odmontowania {mp}: {e}")

# Funkcje główne

def write_iso_to_device():
    iso = safe_input("Podaj ścieżkę do ISO: ").strip()
    if not iso or not os.path.isfile(iso):
        print("❌ Nie znaleziono ISO.")
        return
    dev = select_device_interactive()
    if not dev:
        return

    print("\nWybierz schemat partycji: ")
    print("1) MBR (msdos)")
    print("2) GPT")
    print("3) Pomijam (zostaw jak jest)")
    choice = safe_input("Twój wybór (1/2/3): ").strip()
    if choice == '1':
        print("🔧 Tworzenie etykiety msdos (MBR) ...")
        run(["sudo", "parted", "-s", dev, "mklabel", "msdos"])  # może nadpisać
    elif choice == '2':
        print("🔧 Tworzenie etykiety gpt ...")
        run(["sudo", "parted", "-s", dev, "mklabel", "gpt"])  # może nadpisać
    else:
        print("⚠️ Pomijam zmianę etykiety.")

    confirm = safe_input(f"\n⚠️ Wszystko na {dev} zostanie nadpisane. Wpisz TAK aby kontynuować: ").strip()
    if confirm != 'TAK':
        print("Anulowano.")
        return

    print("🔁 Start nagrywania (dd + pv)...")
    cmd = f"sudo dd if={shlex.quote(iso)} | pv | sudo dd of={shlex.quote(dev)} bs=4M status=none oflag=sync"
    print(f"[cmd] {cmd}")
    try:
        run(cmd)
    except Exception:
        print("❌ Błąd dd")
    run(["sync"])
    print("✅ Nagrywanie zakończone.")

    # opcjonalnie: zapytaj o dodanie tailscale script lub docker-compose
    post_actions_menu(dev)


def post_actions_menu(dev):
    print("\n--- Dodatkowe opcje po nagraniu ISO ---")
    print("1) Dodaj install_tailscale.sh na pulpit (jeśli wykryto system Linux)")
    print("2) Dodaj plik post_install.txt z poleceniami (np. instalacja Dockera/Nextcloud)")
    print("3) Wygeneruj docker-compose dla Nextcloud + MariaDB + nginx i zapisz jako post_install file")
    print("4) Wygeneruj JSON agenta i dodaj funkcje z pliku txt")
    print("5) Pomiń")
    choice = safe_input("Wybierz (1-5): ").strip()
    mounts = mount_device_partitions(dev)
    try:
        if choice == '1':
            add_tailscale_script_to_mounts(mounts)
        elif choice == '2':
            add_post_install_txt(mounts)
        elif choice == '3':
            generate_docker_compose_post_install(mounts)
        elif choice == '4':
            generate_agent_json(mounts)
        else:
            print("Pominięto dodatkowe opcje.")
    finally:
        # ostrożnie odmontuj
        umount_all_mounts(mounts)


def add_tailscale_script_to_mounts(mounts):
    script = """#!/bin/bash
# install_tailscale.sh - prosty instalator Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
"""
    wrote = False
    for mp in mounts:
        # spróbuj znaleźć pulpit - dla różnych live systemów może to być /home/user/Desktop lub /root/Desktop
        candidates = [
            os.path.join(mp, 'home'),
            os.path.join(mp, 'root'),
            mp,
        ]
        for c in candidates:
            # znajdź katalogy "Desktop" w drzewie do pewnej głębokości
            for root, dirs, files in os.walk(c if os.path.exists(c) else mp):
                for d in dirs:
                    if d.lower() == 'desktop' or d.lower() == 'pulpit':
                        desktop = os.path.join(root, d)
                        path = os.path.join(desktop, 'install_tailscale.sh')
                        try:
                            with open(path, 'w') as f:
                                f.write(script)
                            os.chmod(path, 0o755)
                            print(f"✅ Zapisano skrypt Tailscale: {path}")
                            wrote = True
                            return
                        except Exception as e:
                            print(f"⚠️ Błąd zapisu {path}: {e}")
                # ogranicz głębokość
                if root.count(os.sep) - (c.count(os.sep) if os.path.exists(c) else mp.count(os.sep)) > 4:
                    break
    if not wrote:
        # jako fallback zapisz w katalogu głównym mounta
        for mp in mounts:
            try:
                p = os.path.join(mp, 'install_tailscale.sh')
                with open(p, 'w') as f:
                    f.write(script)
                os.chmod(p, 0o755)
                print(f"✅ Zapisano skrypt Tailscale w {p} (fallback)")
                wrote = True
                break
            except Exception as e:
                print(f"⚠️ Błąd zapisu fallback: {e}")
    if not wrote:
        print("❌ Nie udało się zapisać skryptu Tailscale na pendrive.")


def add_post_install_txt(mounts):
    print("Tworzę post_install.txt z przykładowymi poleceniami...")
    content = """
# post_install.txt
# Uruchom po pierwszym starcie systemu (jako root):
# 1) Zaktualizuj system
sudo apt update && sudo apt upgrade -y
# 2) Zainstaluj docker i docker-compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 3) Wypakuj docker-compose.yml (jeśli istnieje) i uruchom
# sudo docker-compose up -d
"""
    wrote = False
    for mp in mounts:
        try:
            p = os.path.join(mp, 'post_install.txt')
            with open(p, 'w') as f:
                f.write(content)
            print(f"✅ Zapisano post_install.txt: {p}")
            wrote = True
            break
        except Exception as e:
            print(f"⚠️ Błąd zapisu {p}: {e}")
    if not wrote:
        print("❌ Nie udało się zapisać post_install.txt na pendrive.")


def generate_docker_compose_post_install(mounts):
    # prosty docker-compose dla nextclouda + mariadb + nginx jako reverse proxy (bardzo podstawowy)
    dc = {
        'version': '3.7',
        'services': {
            'db': {
                'image': 'mariadb:10.5',
                'restart': 'always',
                'command': '--transaction-isolation=READ-COMMITTED --log-bin=binlog --binlog-format=ROW',
                'environment': {
                    'MYSQL_ROOT_PASSWORD': 'example_root_pw',
                    'MYSQL_DATABASE': 'nextcloud',
                    'MYSQL_USER': 'ncuser',
                    'MYSQL_PASSWORD': 'ncpassword'
                },
                'volumes': ['./db:/var/lib/mysql']
            },
            'nextcloud': {
                'image': 'nextcloud',
                'ports': ['8080:80'],
                'restart': 'always',
                'volumes': ['./nextcloud:/var/www/html'],
                'depends_on': ['db']
            }
        }
    }
    yaml_text = json_to_simple_yaml(dc)
    wrote = False
    for mp in mounts:
        try:
            p = os.path.join(mp, 'docker-compose.nextcloud.yml')
            with open(p, 'w') as f:
                f.write('# docker-compose for Nextcloud + MariaDB (generated)\n')
                f.write(yaml_text)
            print(f"✅ Zapisano docker-compose: {p}")
            wrote = True
            break
        except Exception as e:
            print(f"⚠️ Błąd zapisu {p}: {e}")
    if not wrote:
        print("❌ Nie udało się zapisać docker-compose na pendrive.")


def json_to_simple_yaml(obj, indent=0):
    # bardzo prosty konwerter JSON->YAML (dla naszego DC)
    lines = []
    sp = '  ' * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{sp}{k}:")
                lines.append(json_to_simple_yaml(v, indent + 1))
            else:
                # wartości proste
                val = v
                if isinstance(val, bool):
                    val = 'true' if val else 'false'
                lines.append(f"{sp}{k}: {val}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{sp}- ")
                lines.append(json_to_simple_yaml(item, indent + 1))
            else:
                lines.append(f"{sp}- {item}")
    else:
        lines.append(f"{sp}{obj}")
    return '\n'.join(lines)


def generate_agent_json(mounts):
    print("Generowanie pliku agent.json i (opcjonalnie) funkcji z pliku txt")
    agent = {
        'id': f"agent-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'hostname': os.uname().nodename,
        'created': datetime.now().isoformat(),
        'functions': []
    }
    # zapytaj o plik z funkcjami
    fp = safe_input("Jeśli masz plik .txt z listą funkcji (po instalacji), podaj jego ścieżkę (Enter aby pominąć): ").strip()
    if fp and os.path.exists(fp):
        try:
            with open(fp, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # prosta struktura: nazwa:opis
                    if ':' in line:
                        name, desc = line.split(':', 1)
                    else:
                        name, desc = line, ''
                    agent['functions'].append({'name': name.strip(), 'description': desc.strip()})
            print(f"✅ Wczytano funkcje z {fp}")
        except Exception as e:
            print(f"⚠️ Błąd odczytu {fp}: {e}")

    wrote = False
    for mp in mounts:
        try:
            p = os.path.join(mp, 'agent.json')
            with open(p, 'w') as f:
                json.dump(agent, f, indent=2)
            print(f"✅ Zapisano {p}")
            wrote = True
            break
        except Exception as e:
            print(f"⚠️ Błąd zapisu {p}: {e}")
    if not wrote:
        print("❌ Nie udało się zapisać agent.json na pendrive.")

# Backup/Restore + wysyłka

def backup_usb_interactive():
    dev = select_device_interactive()
    if not dev:
        return
    print("\nGdzie zapisać backup?")
    print("1) Lokalny katalog")
    print("2) Serwer przez scp (user@host:/path)")
    print("3) Wysłać HTTP POST (endpoint)")
    print("4) Pomiń")
    choice = safe_input("Wybierz (1-4): ").strip()
    date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    out_file = os.path.join(BACKUP_DIR, f"{os.path.basename(dev)}_{date}.img")

    if choice == '1':
        print(f"Tworzę obraz -> {out_file}")
        run(f"sudo dd if={shlex.quote(dev)} | pv > {shlex.quote(out_file)}")
        print("✅ Backup lokalny ukończony.")
    elif choice == '2':
        dest = safe_input("Podaj cel scp (np. user@host:/path/pendrive.img): ").strip()
        if not dest:
            print("Anulowano.")
            return
        print("Wysyłam przez scp (może poprosić o hasło)")
        run(f"sudo dd if={shlex.quote(dev)} | pv | ssh {shlex.quote(dest)} 'cat > {shlex.quote(os.path.basename(dest))}'")
        print("✅ Wysłano na serwer (scp).")
    elif choice == '3':
        endpoint = safe_input("Podaj URL endpointu HTTP (POST multipart field 'file'): ").strip()
        if not endpoint:
            print("Anulowano.")
            return
        # tworzymy tymczasowy plik, wysyłamy, potem usuwamy
        run(f"sudo dd if={shlex.quote(dev)} | pv > {shlex.quote(out_file)}")
        print("Wysyłam plik przez curl...")
        run(f"curl -F 'file=@{shlex.quote(out_file)}' {shlex.quote(endpoint)}")
        print("✅ Wysłano przez HTTP POST.")
    else:
        print("Pominięto backup.")


def restore_usb_interactive():
    dev = select_device_interactive()
    if not dev:
        return
    print("Dostępne backupy:")
    run(["ls", "-1", BACKUP_DIR])
    name = safe_input("Podaj nazwę pliku backupu z katalogu lokalnego (lub pełną ścieżkę): ").strip()
    if not name:
        return
    if not os.path.isabs(name):
        path = os.path.join(BACKUP_DIR, name)
    else:
        path = name
    if not os.path.exists(path):
        print("❌ Nie znaleziono pliku backupu.")
        return
    confirm = safe_input(f"⚠️ Przywracasz {path} na {dev}. Wpisz TAK aby kontynuować: ").strip()
    if confirm != 'TAK':
        print("Anulowano.")
        return
    run(f"sudo dd if={shlex.quote(path)} | pv | sudo dd of={shlex.quote(dev)} bs=4M oflag=sync")
    run(["sync"])
    print("✅ Przywracanie zakończone.")

# opcjonalne chroot/install tailscale

def chroot_install_tailscale(mp):
    print("Próba instalacji Tailscale w chroot (wymaga, aby system na pendrive był zgodny z chrootem i miał podstawowe narzędzia)")
    if not os.path.exists(mp):
        print("❌ Mountpoint nie istnieje")
        return
    # prosta procedura: bind-mount /proc /sys /dev, then chroot and run install script
    try:
        run(["sudo", "mount", "--bind", "/proc", os.path.join(mp, 'proc')])
        run(["sudo", "mount", "--bind", "/sys", os.path.join(mp, 'sys')])
        run(["sudo", "mount", "--bind", "/dev", os.path.join(mp, 'dev')])
    except Exception as e:
        print("⚠️ Błąd mount bind: ", e)
    try:
        print("Uruchamiam skrypt instalacyjny wewnątrz chroot (może nie zadziała na wszystkich systemach)")
        cmd = f"sudo chroot {shlex.quote(mp)} /bin/bash -c \"curl -fsSL https://tailscale.com/install.sh | sh\""
        run(cmd)
        print("✅ Skrypt install.sh uruchomiony w chroot (sprawdź logi)")
    except Exception as e:
        print("⚠️ Błąd w chroot/install: ", e)
    finally:
        try:
            run(["sudo", "umount", os.path.join(mp, 'proc')])
            run(["sudo", "umount", os.path.join(mp, 'sys')])
            run(["sudo", "umount", os.path.join(mp, 'dev')])
        except Exception:
            pass

# Menu główne

def main_menu():
    if os.geteuid() != 0:
        print("⚠️ Rekomendowane uruchomienie jako root (sudo), niektóre operacje mogą się nie powieść bez uprawnień.)")
    while True:
        print('\n=== USB Toolkit EXTENDED ===')
        print('1) Wypal ISO na USB (dd + pv)')
        print('2) Backup USB (lokalny/scp/http)')
        print('3) Przywróć backup na USB')
        print('4) Pokaż urządzenia (lsblk/lsusb)')
        print('5) Mount partycji urządzenia i sprawdź /etc (przydatne do add-tailscale)')
        print('6) Wyjście')
        ch = safe_input('Wybierz (1-6): ').strip()
        if ch == '1':
            write_iso_to_device()
        elif ch == '2':
            backup_usb_interactive()
        elif ch == '3':
            restore_usb_interactive()
        elif ch == '4':
            list_devices()
        elif ch == '5':
            dev = select_device_interactive()
            if dev:
                mounts = mount_device_partitions(dev)
                # prosty check: czy w którymś mount jest /etc
                found = False
                for m in mounts:
                    if os.path.exists(os.path.join(m, 'etc')):
                        print(f"✅ Wykryto katalog /etc w: {m} -- wygląda jak system Linux")
                        found = True
                if not found:
                    print("⚠️ Nie wykryto /etc w żadnym montowaniu.")
                # zapytaj o chroot install
                if found:
                    do_chroot = safe_input('Chcesz spróbować chroot install tailscale? (tak/nie): ').strip().lower()
                    if do_chroot in ('tak', 't', 'y', 'yes'):
                        # wybierz mount
                        for i, m in enumerate(mounts, 1):
                            print(f"{i}) {m}")
                        idx = safe_input('Wybierz numer mounta do chroot: ').strip()
                        try:
                            idx = int(idx) - 1
                            if 0 <= idx < len(mounts):
                                chroot_install_tailscale(mounts[idx])
                        except Exception:
                            print('Niepoprawny wybór')
                umount_all_mounts(mounts)
        elif ch == '6':
            print('Do zobaczenia!')
            sys.exit(0)
        else:
            print('Nieznana opcja')

if __name__ == '__main__':
    main_menu()
