# SentientVentures

SentientVentures ist ein lokales Monorepo mit drei Laufzeitkomponenten:

- Founder Portal: `http://localhost:8080`
- VC Dashboard: `http://localhost:8081`
- API: `http://localhost:8000`

Die API bietet außerdem einen Health-Check unter `http://localhost:8000/health`.

## Voraussetzungen

- Conda
- Node.js
- `pnpm` 9.15.4 oder kompatibel mit dem Repository-Root-`packageManager`

Die Python-Abhängigkeiten kommen aus `environment.yml`, das Web-Workspace-Setup aus dem pnpm-Monorepo.

## Installation

1. Conda-Umgebung erstellen und aktivieren:

```bash
conda env create -f environment.yml
conda activate codex-agents
```

2. Web-Workspace installieren:

```bash
pnpm install
```

3. Beispiel-Umgebung anlegen:

```bash
cp .env.example .env
```

Die Datei `.env` ist lokal und nicht im Repository enthalten. Die API lädt sie beim Start automatisch aus dem Repository-Root; bereits gesetzte Prozessvariablen behalten Vorrang.

## Konfiguration

Die wichtigsten lokalen Variablen stehen in `.env.example`:

- `VITE_API_BASE_URL=http://localhost:8000/api/v1`
- `SV_DATA_ROOT=./data/companies`
- `SV_ALLOWED_ORIGINS=http://localhost:8080,http://localhost:8081`
- `SV_LLM_PROVIDER=`
- `SV_LLM_MODEL=gpt-5.4-nano`
- `SV_LLM_TIMEOUT_SECONDS=120`
- `SV_LLM_MAX_OUTPUT_TOKENS=30000`
- `SV_ENABLE_DEV_RESET=false`

Für den Live-Council werden `SV_LLM_PROVIDER=openai`, ein Modell in `SV_LLM_MODEL` und `OPENAI_API_KEY` benötigt. Der Adapter nutzt strikt strukturiertes JSON; Zitate werden serverseitig auf bekannte Dokumentseiten zurückgeführt. Wenn `SV_LLM_PROVIDER` leer oder `disabled` ist, bleibt der Provider-Pfad deaktiviert. Der deterministische Demo-Provider wird nur aktiv, wenn `SV_LLM_PROVIDER=fake` oder `deterministic` und zusätzlich `SV_DEMO_MODE=1`, `true` oder `yes` gesetzt ist. Ein Anthropic-Live-Adapter ist derzeit nicht implementiert.

Die Persistenz liegt standardmäßig unter `./data/companies` relativ zum Repository. Dort werden Uploads, Extraktionsartefakte, Evaluierungen, Logs und `metadata.json` pro Company abgelegt.

## Start

Alle lokalen Dienste zusammen starten:

```bash
pnpm dev
```

Der Befehl startet:

- `apps/api` auf Port `8000`
- `apps/founder-portal` auf Port `8080`
- `apps/vc-dashboard` auf Port `8081`

Wenn du nur prüfen willst, ob die API läuft:

```bash
curl http://localhost:8000/health
```

## Nutzung

### Founder Portal

1. Öffne `http://localhost:8080`.
2. Fülle die Pflichtfelder für Unternehmen und Gründer aus.
3. Lade das Pitch-Deck als PDF hoch.
4. Lade entweder einen CV als PDF oder eine LinkedIn-HTTPS-URL hoch.
5. Optional kannst du bis zu vier weitere PDFs anhängen.
6. Sende das Formular ab und beobachte den Job-Status per Polling.

### VC Dashboard

1. Öffne `http://localhost:8081`.
2. Wähle eine Company aus der Liste.
3. Wechsle zwischen der Übersicht und den Kategorien.
4. Die Ansicht zeigt nur validierte API-Daten an, keine Rohdateien.

## Stoppen und Zurücksetzen

- Mit `Ctrl+C` beendest du den lokalen Dev-Stack.
- Es gibt keinen produktiven Reset- oder Reindex-Endpunkt.
- Wenn du die lokale Demo vollständig zurücksetzen willst, lösche den Inhalt unter `SV_DATA_ROOT` und starte danach die Dienste neu.

## Tests

Die verfügbaren Checks aus dem Repository-Root sind:

```bash
pnpm typecheck
pnpm test:web
pnpm test:contracts
pnpm test
pnpm test:e2e
conda run -n codex-agents pytest
```

Empfohlene Reihenfolge für lokale Änderungen:

1. `pnpm typecheck`
2. `pnpm test:web`
3. `pnpm test:contracts`
4. `conda run -n codex-agents pytest`
5. `pnpm test:e2e`

## Troubleshooting

- Port `8000` ist die API. Wenn `pnpm dev` dort scheitert, prüfe, ob ein anderer Prozess den Port belegt.
- Port `8080` ist das Founder Portal.
- Port `8081` ist das VC Dashboard.
- Wenn das Frontend die API nicht erreicht, prüfe `VITE_API_BASE_URL` in `.env`.
- Wenn lokale Daten fehlen oder alte Teststände stören, prüfe `SV_DATA_ROOT`.
- Bei `PROVIDER_UNAVAILABLE` prüfe `SV_LLM_PROVIDER=openai`, `SV_LLM_MODEL`, `OPENAI_API_KEY` und den Netzwerkzugriff. Für den vollständigen 75-Kriterien-Judge sollte das Timeout mindestens 120 Sekunden betragen.
- Wenn der deterministische Demo-Provider nicht greift, prüfe beide Variablen: `SV_LLM_PROVIDER=fake|deterministic` und `SV_DEMO_MODE=1|true|yes`.

## Weiteres

- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Markdown contract](docs/markdown-contract.md)
