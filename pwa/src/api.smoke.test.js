import test from "node:test";
import assert from "node:assert/strict";

import { login, syncMeals } from "./api.js";


test("login posts credentials to the auth endpoint", async () => {
  let captured = null;
  global.fetch = async (url, options) => {
    captured = { url, options };
    return {
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ access_token: "token-1", user_id: 4, role: "user" }),
    };
  };

  const result = await login("http://localhost:5000", "user@fittrack.com", "user123");

  assert.equal(result.user_id, 4);
  assert.deepEqual(captured, {
    url: "http://localhost:5000/auth/login",
    options: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "user@fittrack.com", password: "user123" }),
    },
  });
});


test("syncMeals sends the queued entries payload", async () => {
  let captured = null;
  global.fetch = async (url, options) => {
    captured = { url, options };
    return {
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ synced: 2, ids: [10, 11] }),
    };
  };

  const entries = [
    { meal_name: "breakfast", food_items: [{ name: "Oats", calories: 389 }] },
    { meal_name: "snack", food_items: [{ name: "Banana", calories: 89 }] },
  ];
  const result = await syncMeals("http://localhost:5000", "token-1", entries);

  assert.equal(result.synced, 2);
  assert.deepEqual(captured, {
    url: "http://localhost:5000/meals/sync",
    options: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer token-1",
      },
      body: JSON.stringify({ entries }),
    },
  });
});