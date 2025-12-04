# Jellyfin Playback Validator

Python CLI-Anwendung zur Validierung von Jellyfin-Filmen durch Playback-Stream-Tests. Die App identifiziert defekte Filmdateien, markiert sie mit Tags und erstellt eine Backup-Liste.

## Features

- **Batch-Verarbeitung**: Testet maximal 10 Filme pro Durchlauf (konfigurierbar)
- **Progress Tracking**: Speichert Fortschritt zwischen Durchläufen
- **Playback-Tests**: Nutzt Jellyfin's PlaybackInfo API
- **Automatische Markierung**: Fügt "DEFEKT" Tag zu kaputten Filmen hinzu
- **Backup-Datei**: Erstellt TXT-Datei mit defekten Filmen und Pfaden
- **Schöne CLI**: Rich-basierte Fortschrittsanzeige
- **Sequenzielle Verarbeitung**: Schont den Server durch einzelne Requests

## Anforderungen

- Python 3.10 oder höher
- Jellyfin Server mit API-Zugang
- API Key und User ID von Jellyfin

## Installation

1. Repository klonen oder herunterladen:
```bash
cd jellyfin-playback-validator
```

2. Virtuelle Umgebung erstellen (empfohlen):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Dependencies installieren:
```bash
pip install -r requirements.txt
```

4. Konfiguration erstellen:
```bash
# Kopiere die Beispiel-Konfiguration
copy config.example.json config.json

# Bearbeite config.json mit deinen Jellyfin-Credentials
```

## Konfiguration

Bearbeite `config.json` mit deinen Jellyfin-Daten:

```json
{
  "jellyfin": {
    "base_url": "https://your-jellyfin-server.com",
    "web_base": "https://your-jellyfin-server.com",
    "api_key": "your-api-key-here",
    "user_id": "your-user-id-here"
  },
  "validation": {
    "max_films_per_run": 10,
    "timeout_seconds": 30,
    "defect_tag": "DEFEKT",
    "pause_between_requests": 1.0
  },
  "output": {
    "backup_file": "defekte_filme.txt",
    "progress_file": "progress.json"
  }
}
```

### Jellyfin API Key erhalten

1. Öffne Jellyfin Web Interface
2. Gehe zu Dashboard → API Keys
3. Erstelle einen neuen API Key
4. Kopiere den Key in die `config.json`

### User ID finden

1. Öffne Jellyfin Web Interface
2. Gehe zu Dashboard → Users
3. Klicke auf deinen Benutzer
4. Die User ID steht in der URL: `/web/index.html#!/users/user.html?userId=YOUR_USER_ID`

## Verwendung

### Grundlegende Nutzung

Starte die Validierung:

```bash
python -m src.main
```

Das Script wird:
1. Die nächsten 10 ungetesteten Filme laden
2. Jeden Film sequenziell testen
3. Defekte Filme mit Tag markieren
4. Fortschritt speichern
5. Zusammenfassung anzeigen

### Mehrere Durchläufe

Da das Script nur 10 Filme pro Durchlauf testet, führe es einfach mehrmals aus:

```bash
# Durchlauf 1: Filme 1-10
python -m src.main

# Durchlauf 2: Filme 11-20
python -m src.main

# Durchlauf 3: Filme 21-30
python -m src.main

# usw...
```

Der Fortschritt wird automatisch in `progress.json` gespeichert.

### Beispiel-Ausgabe

```
═══════════════════════════════════
   Jellyfin Playback Validator
═══════════════════════════════════
Server: https://tv.einsle.com

Fortschritt: 150/2313 Filme getestet (6.5%)
Status: OK: 145 | DEFEKT: 5

Teste Batch 16/232

⠋ Teste: Avatar (2009) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/10 30%

  ✓ Avatar (2009)
  ✓ Inception (2010)
  ✗ The Lucky One (2012) - DEFEKT
  ✓ Interstellar (2014)
  ...

═══ Zusammenfassung ═══
Getestet     10 Filme
OK           9 Filme
DEFEKT       1 Film
Fortschritt  160/2313 (6.9%)

Noch zu testen: 2153 Filme
Führe das Script erneut aus, um fortzufahren.
```

## Output-Dateien

### progress.json

Speichert den Validierungsfortschritt:

```json
{
  "total_films": 2313,
  "tested_films": ["id1", "id2", ...],
  "defect_films": ["id3", "id5", ...]
}
```

### defekte_filme.txt

Backup-Liste aller defekten Filme:

```
=== Defekte Filme ===
Erstellt: 2025-12-04 15:30:45

- The Lucky One German DL 1080p BluRay x264-SONS (2012)
  /volume3/video2/Filme/_nzbs/The Lucky One German DL 1080p BluRay x264-SONS [tmdbid-446847]/The Lucky One German DL 1080p BluRay x264-SONS.mkv

- Another Broken Movie (2020)
  /volume3/video2/Filme/Another Broken Movie.mkv
```

### jellyfin_validator.log

Detailliertes Log aller Operationen für Debugging.

## Fortschritt zurücksetzen

Um von vorne zu beginnen, lösche einfach die `progress.json`:

```bash
# Windows
del progress.json

# Linux/Mac
rm progress.json
```

## Konfigurationsoptionen

### validation.max_films_per_run

Anzahl Filme pro Durchlauf (1-100). Standard: 10

### validation.timeout_seconds

Timeout für API-Requests in Sekunden (5-120). Standard: 30

### validation.defect_tag

Tag-Name für defekte Filme. Standard: "DEFEKT"

### validation.pause_between_requests

Pause zwischen Requests in Sekunden (0-10). Standard: 1.0
Erhöhe diesen Wert, wenn dein Server überlastet wird.

## Fehlerbehebung

### "Configuration file not found"

Erstelle `config.json` basierend auf `config.example.json`.

### "Request failed" / Timeout-Fehler

- Prüfe Netzwerkverbindung zu Jellyfin
- Erhöhe `timeout_seconds` in der Konfiguration
- Prüfe API Key und User ID

### "No media sources found"

Die Filmdatei existiert nicht oder ist korrupt. Dies ist ein erwarteter Fehler für defekte Filme.

### Script wird unterbrochen

Der Fortschritt wird nach jedem Film gespeichert. Starte das Script einfach neu, es macht genau dort weiter.

## Technische Details

### Validierungsmethode

Das Script nutzt Jellyfin's `/Items/{itemId}/PlaybackInfo` Endpoint:

1. Sendet POST Request mit DeviceProfile
2. Prüft ob MediaSources vorhanden sind
3. Prüft ob DirectStream/DirectPlay unterstützt wird
4. Prüft auf Fehler-Codes in der Response

### Tag-Verwaltung

Tags werden via Jellyfin API hinzugefügt:
1. Aktuelle Tags des Films abrufen
2. Neuen Tag hinzufügen
3. Item aktualisieren

## Lizenz

Dieses Projekt ist Open Source und frei verwendbar.

## Support

Bei Problemen oder Fragen, erstelle ein Issue im Repository.
