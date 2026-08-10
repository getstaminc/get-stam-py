// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// react-scripts 5's bundled Jest (27.x) jsdom environment doesn't polyfill
// TextEncoder/TextDecoder globally, which react-router-dom v7 expects to
// exist. Polyfill from Node's own util module before any test file loads.
import { TextEncoder, TextDecoder } from 'util';
if (typeof (global as any).TextEncoder === 'undefined') {
  (global as any).TextEncoder = TextEncoder;
}
if (typeof (global as any).TextDecoder === 'undefined') {
  (global as any).TextDecoder = TextDecoder;
}
