// src/global.d.ts

// This declares a global constant named 'UIkit'
// and defines the minimal structure needed to satisfy the type checker.
declare const UIkit: {
  modal: (selector: string) => {
    show: () => void
    hide: () => void
  }
  // Add other methods if you use them (e.g., UIkit.notification)
  // notification: (message: string) => void;
}
