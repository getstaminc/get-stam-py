declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
    ga?: (
      command: string,
      hitType: string,
      eventCategory?: string,
      eventAction?: string,
      eventLabel?: string
    ) => void;
  }
}

export {};
