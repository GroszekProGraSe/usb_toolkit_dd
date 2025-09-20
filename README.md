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
   * 

3. 
