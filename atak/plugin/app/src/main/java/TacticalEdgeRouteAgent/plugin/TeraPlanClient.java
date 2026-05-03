package TacticalEdgeRouteAgent.plugin;

import java.io.BufferedReader;
import java.io.OutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class TeraPlanClient {

    interface Callback {
        void onComplete(boolean ok, String message);
    }

    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final int TIMEOUT_MS = 15000;

    private TeraPlanClient() {
    }

    static void requestPlan(String endpoint, String model, String prompt, Callback callback) {
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

                String selectedModel = model == null || model.trim().isEmpty()
                        ? "local"
                        : model.trim();
                String payload = "{\"prompt\":\"" + escapeJson(prompt.trim())
                        + "\",\"model\":\"" + escapeJson(selectedModel)
                        + "\",\"source\":\"atak-plugin\",\"lat\":null,\"lon\":null}";
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
                        "HTTP " + code + "\n" + truncate(result.toString()));
            } catch (Exception e) {
                callback.onComplete(false, e.getClass().getSimpleName() + ": " + e.getMessage());
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private static String escapeJson(String value) {
        return value.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private static String truncate(String value) {
        if (value.length() <= 1200) {
            return value;
        }
        return value.substring(0, 1200) + "\n...";
    }
}
