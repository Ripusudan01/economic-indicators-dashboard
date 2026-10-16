import assert from "node:assert/strict";
import test from "node:test";
import { getLoginErrorMessage } from "../src/auth/loginError.js";

test("identifies a real unauthorized response as invalid credentials", () => {
  assert.match(
    getLoginErrorMessage({ response: { status: 401, data: { detail: "Invalid credentials" } } }),
    /Invalid username or password/
  );
});

test("does not label a network or CORS failure as invalid credentials", () => {
  assert.match(
    getLoginErrorMessage({ request: {} }),
    /backend URL.*availability.*CORS/
  );
});

test("preserves backend error details for other HTTP responses", () => {
  assert.equal(
    getLoginErrorMessage({ response: { status: 429, data: { detail: "Try again later" } } }),
    "Try again later"
  );
});

test("reports an HTTP failure without a detail field", () => {
  assert.equal(
    getLoginErrorMessage({ response: { status: 503, data: {} } }),
    "Login request failed (HTTP 503). Please try again."
  );
});
