export const TranslationsDE = {
  btns: {
    run: 'Ausführen',
    export: 'Exportieren',
    import: 'Importieren',
    editCode: 'Code bearbeiten',
    save: 'Speichern',
    cancel: 'Abbrechen',
    confirm: 'Bestätigen',
    deleteConfirm: 'Ausgewählte Knoten löschen',
    addTransformationNode: 'Transformationsknoten hinzufügen',
    addIntermediateNode: 'Zwischenknoten hinzufügen',
    runPipeline: 'Pipeline ausführen',
    showTraceback: 'Traceback anzeigen',
    hideTraceback: 'Traceback verbergen',
    abort: 'Abbrechen',
    aborting: 'Abbruch läuft...',
  },
  text: {
    nodeDeleteConfirm: {
      title: 'Knoten löschen Bestätigung',
      warning: 'Möchten Sie die ausgewählten Knoten wirklich löschen?',
    },
    graphNotConnected: 'Grafik nicht verbunden',
    missingIO: 'Eingabe- oder Ausgabeknoten fehlt!',
    apiConnectionError: 'Pipeline konnte nicht gestartet werden (API-Verbindungsfehler).',
    backendContactError: 'Backend konnte nicht erreicht werden.',
    webSocketError:
      'Kann keine Verbindung zum Backend oder WebSocket herstellen. Bitte Backend neu starten und erneut versuchen.',
    abortError: 'Pipeline-Abbruch fehlgeschlagen.',
    pipeline: {
      label: 'Pipeline',
      status: {
        running: 'läuft',
        completed: 'abgeschlossen',
        failed: 'fehlgeschlagen',
        aborted: 'abgebrochen',
      },
    },
    runPipeline: {
      title: 'Pipeline konfigurieren',
      description: 'Überprüfen Sie unten die Optionen und starten Sie die Pipeline.',
      allowProducer: 'Producer aktivieren',
      nChannels: 'Anzahl der Kanäle',
      frequency: 'Frequenz (Datensätze/Sek.)',
      runtime: 'Laufzeit der Pipeline (Sekunden)',
    },
    validation: {
      runtimeError:
        'Die Pipeline-Laufzeit muss eine positive ganze Zahl und mindestens 5 Sekunden betragen',
      channelsError: 'Anzahl der Kanäle muss eine positive ganze Zahl sein',
      frequencyError: 'Frequenz muss eine positive Zahl sein',
    },
  },
}
