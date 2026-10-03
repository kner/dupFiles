# dupFiles

Kommandozeilenprogramm für Ubuntu 24.04. Benötigt Python 3, keine zusätzlichen Python-Pakete. Die ausführbare Datei `dupFiles` ist bereits einsatzbereit.

Im Projektordner starten:

```bash
./dupFiles --newindex --extension .jpg ~/Dropbox ~/tmp ~/verz1
```

Ohne Suchpfade wird das aktuelle Arbeitsverzeichnis rekursiv durchsucht:

```bash
./dupFiles --extension .jpg
```

Es sind bis zu neun Suchverzeichnisse möglich. Ihre Reihenfolge bestimmt die Nummern in der Ausgabe. Die Ausgabe zeigt absolute Dateipfade in Anführungszeichen. Steuerzeichen in Dateinamen werden zur eindeutigen Darstellung maskiert.

## Vergleich

Dateien mit derselben angegebenen Endung und exakt demselben Zeitstempel `JJJJ-MM-TT HH.MM.SS` im Dateinamen gehören zu einer Duplikatgruppe. Beispiel:

```text
2026-09-16 09.55.05.jpg
2026-09-16 09.55.05_cb.jpg
cb_2026-09-16 09.55.05.JPG
```

Eine direkt an den Kalender-Zeitstempel angehängte Nummer (`-1`, `-10` usw.) wird mitverglichen. Daher bleiben `2025-11-22 20.55.25-1.jpg`, `2025-11-22 20.55.25-10.jpg`, `-11.jpg`, `-12.jpg` und `-13.jpg` in getrennten Gruppen. Auch die Datei ohne Nummer bleibt getrennt. Zusätze wie `cb_` oder `_cb` werden weiterhin ignoriert, etwa bei `cb_2025-11-22 20.55.25-1.jpg`.

Auch eingebettete Epoch-Zeitstempel werden erkannt: 10 Ziffern für Sekunden oder 13 Ziffern für Millisekunden. Beispielsweise gehören diese Dateien zusammen:

```text
1607083502589.mp4
cb_1607083502589.mp4
1607083502589_cb.mp4
```

Der Zahlenblock darf beliebige Zusätze haben, aber kein Teil einer längeren Ziffernfolge sein. Verglichen wird der exakte Epoch-Wert innerhalb derselben Einheit; unterschiedliche Millisekunden bleiben getrennt. Sekunden-, Millisekunden- und Kalenderformate werden nicht ineinander umgerechnet. Bei mehreren Zeitstempeln oder einer Mischung aus Kalender- und Epoch-Zeitstempel wird nur der vollständige Dateiname verglichen. 10- oder 13-stellige Zahlen werden als Epoch interpretiert; auch eine gleich lange Kennnummer kann daher Treffer erzeugen.

Die Endung wird ohne Beachtung der Groß-/Kleinschreibung verglichen. Erlaubt sind `--extension .jpg`, `--extension=jpg` und `--extension==jpg`. Dateien ohne eindeutigen gültigen Zeitstempel werden anhand ihres vollständigen Dateinamens verglichen, ebenfalls ohne Beachtung der Groß-/Kleinschreibung. Damit werden beispielsweise drei Dateien namens `1607083502589.mp4` in verschiedenen Unterverzeichnissen als eine Duplikatgruppe erkannt. Für diese Suche `--extension .mp4` angeben. Dateiinhalte werden nicht verglichen: Gleiche Zeitstempel können auch zu unterschiedlichen Bildern gehören.

Symbolische Links auf Dateien oder Verzeichnisse werden innerhalb der Suche nicht verfolgt. Ein als Suchpfad angegebener Link wird dagegen vor der Suche in seinen absoluten Zielpfad aufgelöst. Bei überlappenden Suchpfaden wird jeder absolute Dateipfad nur einmal erfasst und dem zuerst angegebenen passenden Suchverzeichnis zugeordnet.

## Suchindex

`dupFiles.index.json` liegt im Installationsordner, also neben der tatsächlichen Programmdatei. Dieser Ordner muss beschreibbar sein. Ein Start über einen symbolischen Link ändert den Speicherort nicht.

- Fehlt der Index oder stammt er aus einer älteren Programmversion, wird er automatisch neu aufgebaut.
- `--newindex` verwirft den bisherigen Index und baut ihn neu auf. Der alte Index wird erst nach erfolgreicher Suche atomar ersetzt.
- Andere Suchpfade, eine andere Reihenfolge oder eine andere Endung führen ebenfalls zum Neuaufbau.
- Sonst wird der vorhandene Index wiederverwendet. Neue Dateien erscheinen erst nach einem Neuaufbau.
- Seit der Indexierung veränderte oder entfernte Dateien werden übersprungen und mit einem Hinweis gezählt.
- Nach Löschungen wird der Index aktualisiert.

## Löschen

Zunächst die Ergebnisse ohne `--delete` ansehen. Danach beispielsweise:

```bash
./dupFiles --extension .jpg --delete=13 ~/Dropbox ~/tmp ~/verz1
```

`--delete=13` löscht Dateien aus Duplikatgruppen in Suchverzeichnis 1 und 3, einschließlich deren Unterverzeichnissen. Dateien in Suchverzeichnis 2 bleiben erhalten. Einzeldateien werden nicht gelöscht.

Spalte 1 zeigt vor dem Löschen:

```text
X  [1] "/absoluter/Pfad/Dropbox/2026-09-16 09.55.05_cb.jpg"
-  [2] "/absoluter/Pfad/tmp/2026-09-16 09.55.05.jpg"
X  [3] "/absoluter/Pfad/verz1/cb_2026-09-16 09.55.05.jpg"
```

`X` bedeutet zur Löschung ausgewählt; `-` bedeutet bleibt erhalten. Vor der Löschung zeigt das Programm die Anzahl der mit `X` markierten Dateien und fragt nach einer Bestätigung. Nur die Eingabe `JA` startet das Löschen. Enter, jede andere Eingabe, Strg+C oder das Ende der Eingabe brechen ohne Löschung ab. Anschließend wird jede erfolgreiche oder fehlgeschlagene Löschung gemeldet. Ohne `--delete` bleiben alle Dateien erhalten.

Sind sämtliche Dateien einer Gruppe zum Löschen ausgewählt, bleibt die erste Datei erhalten: zuerst nach Suchverzeichnisnummer, dann nach absolutem Pfad sortiert. Vor jeder Löschung wird geprüft, ob die zu löschende Datei und mindestens eine verbleibende Datei noch dem Index entsprechen.

**`--delete` löscht nach ausdrücklicher Bestätigung endgültig und ohne Papierkorb.** Während des Laufs sollten andere Programme die betroffenen Dateien und Verzeichnisse nicht verändern; Prüfung und Löschung sind keine gemeinsame atomare Operation.

## Lokale Installation

Ohne `sudo` aus dem Projektordner installieren:

```bash
./install.sh
```

Das Programm liegt danach in `~/.local/share/dupFiles/dupFiles`, der Suchindex wird beim ersten Suchlauf daneben angelegt. `~/.local/bin/dupFiles` ist ein symbolischer Link auf das Programm.

Falls `~/.local/bin` noch nicht im Suchpfad steht, gibt das Skript die passende `export PATH=...`-Zeile aus. Diese für die aktuelle Shell ausführen und für künftige Terminals in `~/.bashrc` ergänzen. Das Skript verändert keine Shell-Konfigurationsdateien.

Danach beispielsweise:

```bash
dupFiles --extension .mp4 ~/googledrive
```

Ein erneuter Aufruf von `./install.sh` aktualisiert das Programm. Ein vorhandener Index im Installationsordner bleibt erhalten; der Index aus dem Projektordner wird nicht mitkopiert. Einen fremden vorhandenen Programmaufruf überschreibt das Skript nicht.

Optional kann ein anderes Installationspräfix angegeben werden:

```bash
./install.sh --prefix "$HOME/Programme/dupFiles"
```

Programm und Index liegen dann unter `PREFIX/share/dupFiles`, der Aufruf unter `PREFIX/bin/dupFiles`.

## Hilfe und Tests

```bash
./dupFiles --help
python3 -m unittest -v test_dupfiles.py
```

Exitcode: `0` für erfolgreiche Suche/Löschung (auch ohne Treffer), `1` für Laufzeit- oder Löschfehler, `2` für ungültige Argumente.
# dupFiles
