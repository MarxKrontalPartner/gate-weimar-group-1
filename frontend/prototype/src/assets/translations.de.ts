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
    viewPipelineResults: 'Pipeline-Ergebnisse anzeigen',
    runTransformation: 'Transformation ausführen',
    running: 'Läuft...',
    testRuntime: 'Test',
    abort: 'Abbruch!',
  },
  status: {
    loadingRuntime: 'Python-Laufzeit wird geladen...',
    runtimeReady: 'Laufzeit bereit',
    runtimeUnavailable: 'Laufzeit nicht verfügbar',
    runtimeError: 'Fehler beim Laden der Laufzeit',
  },
  labels: {
    enterJsonInput: 'JSON-Eingabe eingeben:',
    output: 'Ausgabe',
    line: 'Zeile',
  },
  text: {
    input: 'Eingabe',
    output: 'Ausgabe',
    streamInspector: 'Stream-Inspektor',
    transformNodeAlert: {
      missingInputData: 'Eingabedaten fehlen. Beispiel: ',
      jsonInputRequired: 'Eingabe muss ein JSON-Objekt sein.',
      invalidJson: 'Ungültiges JSON: ',
      workerInitializationError:
        'Laden des Workers für die Python-Laufzeit (Pyodide) fehlgeschlagen.',
      messageOnAbort:
        'Ausführung abgebrochen. Die Laufzeit wird beim nächsten Test neu initialisiert.',
      workerTimedOut: 'Ausführung zeitüberschritten. Bitte Laufzeit erneut testen.',
    },
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
    pipeline: {
      label: 'Pipeline',
      status: {
        running: 'läuft',
        completed: 'abgeschlossen',
        failed: 'fehlgeschlagen',
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
    exportGraph: 'Name der exportierten Grafik (.json), Standard graph.json',
  },
}
