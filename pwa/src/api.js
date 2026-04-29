const jsonHeaders = { "Content-Type": "application/json" };

async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = payload.error || JSON.stringify(payload);
    } catch {
      message = await response.text();
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export async function healthCheck(baseUrl) {
  return request(baseUrl, "/health");
}

export async function login(baseUrl, email, password) {
  return request(baseUrl, "/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ email, password }),
  });
}

export async function register(baseUrl, payload) {
  return request(baseUrl, "/auth/register", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
}

function authHeaders(token) {
  return {
    ...jsonHeaders,
    Authorization: `Bearer ${token}`,
  };
}

export async function saveWorkout(baseUrl, token, payload) {
  return request(baseUrl, "/workouts", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function searchFood(baseUrl, token, query) {
  return request(baseUrl, `/meals/search?q=${encodeURIComponent(query)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function saveMeal(baseUrl, token, payload) {
  return request(baseUrl, "/meals", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function syncMeals(baseUrl, token, entries) {
  return request(baseUrl, "/meals/sync", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ entries }),
  });
}

export async function getProgress(baseUrl, token, userId) {
  return request(baseUrl, `/users/${userId}/progress`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function saveGoal(baseUrl, token, _userId, payload) {
  return request(baseUrl, "/goals", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function saveMeasurement(baseUrl, token, _userId, payload) {
  return request(baseUrl, "/measurements", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function getBadges(baseUrl, token, userId) {
  return request(baseUrl, `/users/${userId}/badges`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getWorkouts(baseUrl, token) {
  return request(baseUrl, "/workouts", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMeals(baseUrl, token, date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return request(baseUrl, `/meals${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getGoals(baseUrl, token) {
  return request(baseUrl, "/goals", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function completeGoal(baseUrl, token, goalId) {
  return request(baseUrl, `/goals/${goalId}/complete`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMeasurementsLatest(baseUrl, token) {
  return request(baseUrl, "/measurements/latest", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMeasurements(baseUrl, token) {
  return request(baseUrl, "/measurements", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function addMeasurement(baseUrl, token, payload) {
  return request(baseUrl, "/measurements", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function getNotifications(baseUrl, token) {
  return request(baseUrl, "/notifications", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getDueNotifications(baseUrl, token) {
  return request(baseUrl, "/notifications/due", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function deliverNotification(baseUrl, token, notifId) {
  return request(baseUrl, `/notifications/${notifId}/deliver`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function addNotification(baseUrl, token, payload) {
  return request(baseUrl, "/notifications", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function getCoachDashboard(baseUrl, token, search) {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return request(baseUrl, `/coach/dashboard${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCoachClientProgress(baseUrl, token, clientId) {
  return request(baseUrl, `/coach/clients/${clientId}/progress`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function downloadCoachReport(baseUrl, token, clientId, format) {
  const response = await fetch(`${baseUrl}/coach/clients/${clientId}/progress?format=${format}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Download failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `client-${clientId}-progress.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}