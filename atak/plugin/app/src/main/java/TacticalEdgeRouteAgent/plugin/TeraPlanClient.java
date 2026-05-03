package TacticalEdgeRouteAgent.plugin;

import java.io.BufferedReader;
import java.io.OutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.json.JSONException;
import org.json.JSONObject;

final class TeraPlanClient {

    interface Callback {
        void onComplete(boolean ok, String message);
    }

    interface PlanCallback {
        void onComplete(boolean ok, String message, JSONObject planJson);
    }

    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final int CONNECT_TIMEOUT_MS = 5000;
    private static final int READ_TIMEOUT_MS = 180000;
    private static final String REJECTED_SIGNATURE = "Route signature invalid - REJECTED";
    private static final String TERA_READY_MESSAGE = "TERA Agent ready. Send your traffic.";

    private TeraPlanClient() {
    }

    static void checkJetson(String endpoint, Callback callback) {
        EXECUTOR.execute(() -> {
            if (endpoint == null || !endpoint.startsWith("http")) {
                callback.onComplete(false, "Endpoint must start with http:// or https://");
                return;
            }

            String healthError = checkHealth(endpoint.trim());
            if (healthError != null) {
                callback.onComplete(false, healthError);
                return;
            }

            String readyError = ensureTeraReady(endpoint.trim());
            callback.onComplete(readyError == null, readyError == null
                    ? TERA_READY_MESSAGE
                    : readyError);
        });
    }

    static void requestPlan(String endpoint, String prompt, JSONObject mapContext,
                            PlanCallback callback) {
        EXECUTOR.execute(() -> {
            HttpURLConnection connection = null;
            try {
                if (endpoint == null || !endpoint.startsWith("http")) {
                    callback.onComplete(false, "Endpoint must start with http:// or https://", null);
                    return;
                }
                if (prompt == null || prompt.trim().isEmpty()) {
                    callback.onComplete(false, "Prompt is empty.", null);
                    return;
                }

                String healthError = checkHealth(endpoint.trim());
                if (healthError != null) {
                    callback.onComplete(false, healthError, null);
                    return;
                }
                String readyError = ensureTeraReady(endpoint.trim());
                if (readyError != null) {
                    callback.onComplete(false, readyError, null);
                    return;
                }

                URL url = new URL(endpoint.trim());
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
                connection.setReadTimeout(READ_TIMEOUT_MS);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);

                String payload = buildPlanPayload(prompt.trim(), mapContext);
                byte[] body = payload.getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(body.length);

                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body);
                }

                int code = connection.getResponseCode();
                String responseBody = readResponse(connection, code);
                if (code >= 200 && code < 300 && shouldVerifyPlanResponse(responseBody)) {
                    VerifyResult verify = verifyPlanResponse(endpoint, responseBody);
                    if (!verify.ok) {
                        callback.onComplete(false, REJECTED_SIGNATURE + "\n" + verify.message, null);
                        return;
                    }
                }

                JSONObject planJson = null;
                try {
                    planJson = new JSONObject(responseBody);
                } catch (JSONException ignored) {
                }

                PromptResult result = parsePromptResult(code, responseBody);
                callback.onComplete(result.ok, result.message, result.ok ? planJson : null);
            } catch (SocketTimeoutException e) {
                callback.onComplete(false, "Jetson timed out. Check WiFi, the configured endpoint port, and whether the agent is running.", null);
            } catch (Exception e) {
                callback.onComplete(false, friendlyException(e), null);
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private static String readResponse(HttpURLConnection connection, int code)
            throws java.io.IOException {
        java.io.InputStream stream = code >= 200 && code < 300
                ? connection.getInputStream()
                : connection.getErrorStream();
        if (stream == null) {
            return "";
        }

        BufferedReader reader = new BufferedReader(new InputStreamReader(
                stream, StandardCharsets.UTF_8));
        StringBuilder result = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            result.append(line).append('\n');
        }
        return result.toString();
    }

    private static VerifyResult verifyPlanResponse(String planEndpoint, String planResponseJson) {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(verifyEndpointFor(planEndpoint));
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(READ_TIMEOUT_MS);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);

            byte[] body = planResponseJson.getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int code = connection.getResponseCode();
            String verifyBody = readResponse(connection, code);
            boolean valid = code >= 200 && code < 300 && verifyBodyIsValid(verifyBody);
            return new VerifyResult(valid, "HTTP " + code + "\n" + truncate(verifyBody));
        } catch (Exception e) {
            return new VerifyResult(false, friendlyException(e));
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static boolean shouldVerifyPlanResponse(String body) {
        try {
            JSONObject json = new JSONObject(body);
            return json.has("route") || json.has("signature");
        } catch (JSONException ignored) {
            return false;
        }
    }

    private static boolean verifyBodyIsValid(String body) {
        try {
            return new JSONObject(body).optBoolean("valid", false);
        } catch (JSONException ignored) {
            return false;
        }
    }

    private static String verifyEndpointFor(String endpoint) {
        int planPath = endpoint.indexOf("/plan");
        if (planPath >= 0) {
            return endpoint.substring(0, planPath) + "/plan/verify";
        }
        int lastSlash = endpoint.indexOf("/", endpoint.indexOf("://") + 3);
        if (lastSlash >= 0) {
            return endpoint.substring(0, lastSlash) + "/plan/verify";
        }
        return endpoint + "/plan/verify";
    }

    private static String checkHealth(String endpoint) {
        HttpURLConnection connection = null;
        try {
            URL healthUrl = new URL(healthEndpoint(endpoint));
            connection = (HttpURLConnection) healthUrl.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(CONNECT_TIMEOUT_MS);

            int code = connection.getResponseCode();
            if (code >= 200 && code < 300) {
                return null;
            }
            return "Jetson health check failed: HTTP " + code;
        } catch (SocketTimeoutException e) {
            return "Jetson health check timed out. Check same WiFi, Jetson IP, and port 8080.";
        } catch (Exception e) {
            return "Cannot reach Jetson health endpoint. " + friendlyException(e);
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String ensureTeraReady(String endpoint) {
        Boolean ready = readAtakReadyStatus(endpoint);
        if (Boolean.TRUE.equals(ready)) {
            return null;
        }
        if (ready == null) {
            return null;
        }
        return activateAtakAgent(endpoint);
    }

    private static Boolean readAtakReadyStatus(String endpoint) {
        HttpURLConnection connection = null;
        try {
            URL statusUrl = new URL(serviceBaseUrl(endpoint) + "/api/jetson/atak-agent/status");
            connection = (HttpURLConnection) statusUrl.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(CONNECT_TIMEOUT_MS);

            int code = connection.getResponseCode();
            if (code == 404) {
                return null;
            }
            String body = readResponse(connection, code);
            if (code < 200 || code >= 300) {
                return null;
            }
            JSONObject json = new JSONObject(body);
            if (!json.optBoolean("active", false)) {
                return false;
            }
            return json.optBoolean("ollama_ready", false);
        } catch (Exception ignored) {
            return null;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String activateAtakAgent(String endpoint) {
        HttpURLConnection connection = null;
        try {
            URL activateUrl = new URL(serviceBaseUrl(endpoint) + "/api/jetson/atak-agent/activate");
            connection = (HttpURLConnection) activateUrl.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(READ_TIMEOUT_MS);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);

            byte[] body = "{\"model\":\"gemma3:4b\",\"agent_profile\":\"tera-atak-live\"}"
                    .getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int code = connection.getResponseCode();
            String responseBody = readResponse(connection, code);
            if (code == 404) {
                return null;
            }
            if (code < 200 || code >= 300) {
                return "TERA Agent is still starting. Hold traffic. HTTP " + code
                        + "\n" + truncate(responseBody);
            }
            JSONObject json = new JSONObject(responseBody);
            if (json.optBoolean("ollama_ready", false)) {
                return null;
            }
            String detail = json.optString("detail", "Ollama is still warming.");
            return "TERA Agent is still starting. Hold traffic.\n" + detail;
        } catch (SocketTimeoutException e) {
            return "TERA Agent is still starting. Hold traffic until Ollama finishes loading Gemma.";
        } catch (Exception e) {
            return "TERA Agent readiness check failed. " + friendlyException(e);
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String healthEndpoint(String endpoint) {
        return serviceBaseUrl(endpoint) + "/health";
    }

    private static String serviceBaseUrl(String endpoint) {
        int firstPathSlash = endpoint.indexOf("/", endpoint.indexOf("://") + 3);
        if (firstPathSlash >= 0) {
            return endpoint.substring(0, firstPathSlash);
        }
        return endpoint;
    }

    private static String buildPlanPayload(String prompt, JSONObject mapContext)
            throws JSONException {
        JSONObject payload = new JSONObject();
        payload.put("prompt", prompt);
        payload.put("llm_provider", "ollama");
        payload.put("model", "gemma3:4b");
        payload.put("agent_profile", "tera-atak-live");

        // Extract operator GPS position for the /plan PlanRequest `current` field.
        // Prefer the self-marker (operator's real GPS) over the map centre.
        if (mapContext != null) {
            payload.put("map_context", mapContext);
            JSONObject current = null;
            JSONObject selectedArea = mapContext.optJSONObject("selected_area");
            if (selectedArea != null
                    && selectedArea.has("center_lat")
                    && selectedArea.has("center_lon")) {
                current = new JSONObject();
                current.put("lat", selectedArea.getDouble("center_lat"));
                current.put("lon", selectedArea.getDouble("center_lon"));
            } else {
                JSONObject camera = mapContext.optJSONObject("camera");
                if (camera != null && camera.has("lat") && camera.has("lon")) {
                    current = new JSONObject();
                    current.put("lat", camera.getDouble("lat"));
                    current.put("lon", camera.getDouble("lon"));
                }
            }
            if (current != null) {
                payload.put("current", current);
            }
        }

        return payload.toString();
    }

    private static PromptResult parsePromptResult(int code, String body) {
        // Parse PlanResponse: {route, waypoints, rationale, signature, request_id}
        try {
            JSONObject json = new JSONObject(body);
            if (code >= 200 && code < 300 && json.has("route")) {
                StringBuilder summary = new StringBuilder();
                summary.append("[ROUTE ACCEPTED]");
                String rationale = json.optString("rationale", "");
                if (!rationale.trim().isEmpty()) {
                    summary.append("\n").append(rationale.trim());
                }
                if (json.has("waypoints")) {
                    int count = json.getJSONArray("waypoints").length();
                    summary.append("\nWaypoints: ").append(count);
                }
                if (json.has("signature")) {
                    summary.append("\nSignature: verified");
                }
                return new PromptResult(true, summary.toString());
            }
            if (code >= 200 && code < 300 && json.has("response")) {
                String response = json.optString("response", "").trim();
                if (!response.isEmpty()) {
                    return new PromptResult(true, response);
                }
                return new PromptResult(false, "Jetson returned an empty TERA response.");
            }
            String detail = json.optString("detail", json.optString("message", ""));
            if (code >= 200 && code < 300) {
                return new PromptResult(false,
                        "Jetson returned HTTP " + code + " but no route in response.");
            }
            return new PromptResult(false,
                    "HTTP " + code + (detail.isEmpty() ? "" : "\n" + detail));
        } catch (JSONException ignored) {
            // Non-JSON response — show raw body truncated.
        }
        return new PromptResult(false, "HTTP " + code + "\n" + truncate(body));
    }

    private static String friendlyException(Exception e) {
        String message = e.getMessage();
        String suffix = message == null || message.trim().isEmpty()
                ? ""
                : ": " + message;
        return e.getClass().getSimpleName() + suffix;
    }

    private static String truncate(String value) {
        if (value.length() <= 1200) {
            return value;
        }
        return value.substring(0, 1200) + "\n...";
    }

    private static final class VerifyResult {
        final boolean ok;
        final String message;

        VerifyResult(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private static final class PromptResult {
        final boolean ok;
        final String message;

        PromptResult(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }
}
