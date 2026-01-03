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
    runAlertError: 'Graph not connected',
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
      runtimeError: 'Pipeline Runtime must be at least 5 seconds',
      channelsError: 'Number of channels must be a positive number',
      frequencyError: 'Frequency must be a positive number',
    },
  },
}
