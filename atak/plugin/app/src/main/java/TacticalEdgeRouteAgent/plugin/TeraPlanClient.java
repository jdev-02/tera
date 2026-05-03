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

    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final int CONNECT_TIMEOUT_MS = 5000;
    private static final int READ_TIMEOUT_MS = 180000;
    private static final String REJECTED_SIGNATURE = "Route signature invalid - REJECTED";

    private TeraPlanClient() {
    }

    static void checkJetson(String endpoint, Callback callback) {
        EXECUTOR.execute(() -> {
            if (endpoint == null || !endpoint.startsWith("http")) {
                callback.onComplete(false, "Endpoint must start with http:// or https://");
                return;
            }

            String healthError = checkHealth(endpoint.trim());
            callback.onComplete(healthError == null, healthError == null
                    ? "Jetson health check passed."
                    : healthError);
        });
    }

    static void requestPlan(String endpoint, String prompt, JSONObject mapContext,
                            Callback callback) {
        EXECUTOR.execute(() -> {
            HttpURLConnection connection = null;
            try {
                if (endpoint == null || !endpoint.startsWith("http")) {
                    callback.onComplete(false, "Endpoint must start with http:// or https://");
                    return;
                }
                if (prompt == null || prompt.trim().isEmpty()) {
                    callback.onComplete(false, "Prompt is empty.");
                    return;
                }

                String healthError = checkHealth(endpoint.trim());
                if (healthError != null) {
                    callback.onComplete(false, healthError);
                    return;
                }

                URL url = new URL(endpoint.trim());
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
                connection.setReadTimeout(READ_TIMEOUT_MS);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);

                String payload = buildPromptPayload(prompt.trim(), mapContext);
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
                        callback.onComplete(false, REJECTED_SIGNATURE + "\n" + verify.message);
                        return;
                    }
                }

                PromptResult result = parsePromptResult(code, responseBody);
                callback.onComplete(result.ok, result.message);
            } catch (SocketTimeoutException e) {
                callback.onComplete(false, "Jetson timed out. Check WiFi, port 8080, and whether Gemma is still generating.");
            } catch (Exception e) {
                callback.onComplete(false, friendlyException(e));
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
        int promptPath = endpoint.indexOf("/api/prompt");
        if (promptPath >= 0) {
            return endpoint.substring(0, promptPath) + "/plan/verify";
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

    private static String healthEndpoint(String endpoint) {
        int promptPath = endpoint.indexOf("/api/prompt");
        if (promptPath >= 0) {
            return endpoint.substring(0, promptPath) + "/health";
        }
        int lastSlash = endpoint.indexOf("/", endpoint.indexOf("://") + 3);
        if (lastSlash >= 0) {
            return endpoint.substring(0, lastSlash) + "/health";
        }
        return endpoint + "/health";
    }

    private static String buildPromptPayload(String prompt, JSONObject mapContext)
            throws JSONException {
        JSONObject payload = new JSONObject();
        payload.put("prompt", prompt);
        payload.put("model", "gemma3:4b");
        payload.put("llm_provider", "ollama");
        payload.put("agent_profile", "tera-atak-live");
        if (mapContext != null) {
            payload.put("map_context", mapContext);
        }
        return payload.toString();
    }

    private static PromptResult parsePromptResult(int code, String body) {
        try {
            JSONObject json = new JSONObject(body);
            String response = json.optString("response", "");
            if (!response.trim().isEmpty()) {
                return new PromptResult(code >= 200 && code < 300, response.trim());
            }
            String rationale = json.optString("rationale", "");
            if (code >= 200 && code < 300 && !rationale.trim().isEmpty()) {
                return new PromptResult(true, "Signature verified\n" + rationale.trim());
            }
            if (code >= 200 && code < 300 && json.has("route")) {
                return new PromptResult(true, "Signature verified\n" + truncate(body));
            }
            if (code >= 200 && code < 300) {
                return new PromptResult(false,
                        "Jetson returned HTTP " + code + " but no response field.");
            }
        } catch (JSONException ignored) {
            // Fall back to the raw body if the server returns non-JSON.
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
