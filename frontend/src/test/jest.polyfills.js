// Polyfills for Jest to support modern JavaScript features

// structuredClone polyfill (needed for Node < 17)
if (typeof globalThis.structuredClone === 'undefined') {
  globalThis.structuredClone = function structuredClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  };
}

// import.meta.env mock for Vite
global.import = {
  meta: {
    env: {
      VITE_API_URL: 'http://localhost:8000',
      MODE: 'test',
      DEV: false,
      PROD: false,
      SSR: false,
    }
  }
};

// Mock for Vite's import.meta.glob
global.import.meta.glob = () => ({});
global.import.meta.globEager = () => ({});

// Performance API polyfill if needed
if (typeof globalThis.performance === 'undefined') {
  globalThis.performance = {
    now: () => Date.now(),
  };
}

// URL polyfill for older environments
if (typeof globalThis.URL === 'undefined') {
  globalThis.URL = require('url').URL;
}

// Blob polyfill
if (typeof globalThis.Blob === 'undefined') {
  globalThis.Blob = require('buffer').Blob;
}

// FormData polyfill
if (typeof globalThis.FormData === 'undefined') {
  globalThis.FormData = class FormData {
    constructor() {
      this.data = new Map();
    }
    append(key, value) {
      this.data.set(key, value);
    }
    get(key) {
      return this.data.get(key);
    }
    has(key) {
      return this.data.has(key);
    }
    delete(key) {
      return this.data.delete(key);
    }
    forEach(callback) {
      this.data.forEach(callback);
    }
  };
}