package TacticalEdgeRouteAgent.plugin;

import java.io.BufferedReader;
import java.io.OutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
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
    private static final int TIMEOUT_MS = 15000;

    private TeraPlanClient() {
    }

    static void requestPlan(String endpoint, String prompt, Callback callback) {
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

                URL url = new URL(endpoint.trim());
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(TIMEOUT_MS);
                connection.setReadTimeout(TIMEOUT_MS);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);

                String payload = buildPromptPayload(prompt.trim(), null);
                byte[] body = payload.getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(body.length);

                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body);
                }

                int code = connection.getResponseCode();
                BufferedReader reader = new BufferedReader(new InputStreamReader(
                        code >= 200 && code < 300
                                ? connection.getInputStream()
                                : connection.getErrorStream(),
                        StandardCharsets.UTF_8));
                StringBuilder result = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    result.append(line).append('\n');
                }

                callback.onComplete(code >= 200 && code < 300,
                        responseMessage(code, result.toString()));
            } catch (Exception e) {
                callback.onComplete(false, e.getClass().getSimpleName() + ": " + e.getMessage());
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private static String buildPromptPayload(String prompt, JSONObject mapContext)
            throws JSONException {
        JSONObject payload = new JSONObject();
        payload.put("prompt", prompt);
        payload.put("model", "gemma3:4b");
        payload.put("llm_provider", "ollama");
        payload.put("agent_profile", "tera-atak-link-test");
        if (mapContext != null) {
            payload.put("map_context", mapContext);
        }
        return payload.toString();
    }

    private static String responseMessage(int code, String body) {
        try {
            JSONObject json = new JSONObject(body);
            String response = json.optString("response", "");
            if (!response.trim().isEmpty()) {
                return response.trim();
            }
        } catch (JSONException ignored) {
            // Fall back to the raw body if the server returns non-JSON.
        }
        return "HTTP " + code + "\n" + truncate(body);
    }

    private static String truncate(String value) {
        if (value.length() <= 1200) {
            return value;
        }
        return value.substring(0, 1200) + "\n...";
    }
}
