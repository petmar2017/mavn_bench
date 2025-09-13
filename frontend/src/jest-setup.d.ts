import '@testing-library/jest-dom';

declare global {
  interface ImportMeta {
    env: {
      VITE_API_URL?: string;
    };
  }
}

export {};