# usb_toolkit_dd
 * Po zglebieniu montowania  bootowalnych nosnikow przez dd i zlaczenie kilku innych 
projektow powstal taki projekt ktory mysle ma szanse stac sie USB make predatorem :D 

# kopia mojego "readme" roboczego i co to wogole jest :D 
> Opis dla kodu w usb_toolkit narzędzie CLI <
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
>>Tak sie rozkr³cilem z funkcjonalnoscią takiego narzędzia >> Większosc z tych funkcji jest u mnie projektem podobnym do toolkit-a a tu mialbyc czescia pisania bootowalnego nosnika lacznosci tailnetem automatycznie po installacji w czesniej mialo zostawic plik .txt z ip, magicDNS, i ścieżkom dla tailscale przez curl w pozniejszej wersji ma nawet wlasny program crypto dla zapisu takich rzeczy jak hasla i linki do sevisow tez dodany w formie ukonczonej

# 2. od teraz wrzuce kilka usprawnionych wersji bo w konekwencji tu tez bym chcial ukonczyc to narzędzie i zajać sie innymi projektami. Nie zawracajac sobie juz głowy co do nosnikow pamieci i bootowania systemów operacyjnych. Przy okazji nauczę sie mam nadzieje kozystać z servisu git github jako postawa i srodowisko do zajawek programistycznych
2. Tworzenie bootowalnego pendrive’a USB przez dd + pv (kilka wkleje kwlasnych notek, gdyby ktoś sieę  chciał czepić)
- pv? PipeViewer, żeby narzedzie pokazywało podczas procesów progress. Coś jakby process bar dla dd
- zakładając ze obraz.iso to : system.iso, a ścieżka do nośnika to /dev/sdX
- !!! tu mam notke ze dd uwala dyski przy pomyłce z /dev i potrafi usunac pamięć nośnika gdyby coś poszlo nie tak !!!
- te narzędzie i ten problem rozwiązuje :)

* Zakladamy ze .iso to | system.iso a nośnik to /dev/sdX 
 #! sudo dd if=system.iso | pv | sudo dd of=/dev/sdX bs=4M status=none oflag=sync
 + bs=4M – bufor (szybciej niż domyślnie)
 + oflag=sync – wymusza synchronizację bloków, zmniejsza ryzyko uszkodzenia.
 + pv – pokazuje postęp...
3. Kopiowanie całego pendrive’a (backup obrazu), gdyby flash się ujebał i chciałbym przywrócić nośnik
   * sudo dd if=/dev/sdX | pv > pendrive_backup.img -- zgranie do iso
   * sudo dd if=pendrive_backup.img | pv | sudo dd of=/dev/sdX bs=4M oflag=sync -- odtworzenie obrazu z .iso

  >> ## Opcjonalnie ale to tak od siebie nie powinno byc mowy o tym nie w temacie ale mozna uzyc Clonezilla (robibackupy obrazow nosnikow) sama sie bootuje i kompresuje dosc fajnie klona , (niech bedzie porobie wkleiki swoich notatek)
   1. Clonezilla Live z USB/CD.
   * device-image → zapiszesz pendrive/dysk do pliku .img na inny nośnik (np. HDD)
   * device-device → klon 1:1 między nośnikami
   * Do backupu najlepiej: device-image + zapis na zewnętrzny dysk
   * mozna też nado katalogu SAMBA, NFS, SSH
   * i kompressuje wszystko klon jest lzejszy od zwyklego dd
    - - - ale nie o takie rozwiazanie chodzi to tak jakby ktos jednak wolal alternatywe ..

    2. (opcja ktora sie chyba na sam pierw nasowa najprostrza)
 
     
     > System „kieszonkowy” do labu + Tailscale
>Zabrać lab ze sobą i odpalać go z pendrive’a na dowolnym PC/laptopie:
>>Opcje:
>>>>>>> Ventoy + ISO
>Instalacja Ventoy na dużym pendrive (np. 256GB).
>Bootujesz i wybierasz co chcesz odpalić.
>Najlepsza opcja jak chcesz mieć wiele systemów.
>Pełna instalacja Linuxa na pendrive (persistent live)
>Tworzysz system np. Ubuntu, Debian, Kali czy Parrot z persistent storage.
>Masz normalny system, który zachowuje ustawienia.
>Dodajesz Tailscale:
   ( , ,,, ,curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up, ,,, ,)

>Masz swoje środowisko zawsze ze sobą i dostęp do sieci labowej.
>Najprościej: Tailscale + Tailscale Funnel (lub subnet router)
>Na pendrive Linux z persistent storage.
>Instalujesz Dockera (jak chcesz lab w kontenerach).
>Całość odpala się na każdej maszynie (ważne: UEFI/BIOS → trzeba czasem kombinować z trybami legacy/secure boot).



