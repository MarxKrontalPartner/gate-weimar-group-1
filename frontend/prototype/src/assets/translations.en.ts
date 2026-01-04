export const TranslationsEN = {
  btns: {
    run: 'Run',
    export: 'Export',
    import: 'Import',
    editCode: 'Edit Code',
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    deleteConfirm: 'Delete Selected Nodes',
    addTransformationNode: 'Add Transformation Node',
    addIntermediateNode: 'Add Intermediate Node',
    runPipeline: 'Run Pipeline',
  },
  text: {
    nodeDeleteConfirm: {
      title: 'Delete Node Confirmation',
      warning: 'Are you sure you want to delete the selected Nodes?',
    },
    graphNotConnected: 'Graph not connected',
    missingIO: 'Input or Output Node missing!',
    apiConnectionError: 'Failed to start pipeline (API Connection Error).',
    backendContactError: 'Failed to contact backend.',
    webSocketError:
      'Cannot connect to backend or WebSocket. Please restart the backend and try again.',
    pipeline: {
      label: 'Pipeline',
      status: {
        running: 'running',
        completed: 'completed',
        failed: 'failed',
      },
    },
    runPipeline: {
      title: 'Configure Pipeline',
      description: 'Review the options below and start the pipeline.',
      allowProducer: 'Enable Producer',
      nChannels: 'Number of Channels',
      frequency: 'Frequency (records/sec)',
      runtime: 'Pipeline Runtime (seconds)',
    },
    validation: {
      runtimeError: 'Pipeline runtime must be a positive integer and at least 5 seconds',
      channelsError: 'Number of channels must be a positive integer',
      frequencyError: 'Frequency must be a positive number',
    },
  },
}
