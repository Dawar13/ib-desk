// Test setup: register jest-dom matchers for Vitest and clean up the DOM between
// tests so each test renders from a clean slate.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
