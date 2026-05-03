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

    private static final class VerifyResult {
        final boolean ok;
        final String message;

        VerifyResult(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final int TIMEOUT_MS = 15000;
    private static final String REJECTED_SIGNATURE = "Route signature invalid - REJECTED";

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

                String responseBody = result.toString();
                if (code >= 200 && code < 300) {
                    VerifyResult verify = verifyPlanResponse(endpoint, responseBody);
                    if (!verify.ok) {
                        callback.onComplete(false, REJECTED_SIGNATURE + "\n" + verify.message);
                        return;
                    }
                    callback.onComplete(true,
                            "HTTP " + code + "\nSignature verified\n"
                                    + truncate(responseBody));
                } else {
                    callback.onComplete(false, "HTTP " + code + "\n" + truncate(responseBody));
                }
            } catch (Exception e) {
                callback.onComplete(false, e.getClass().getSimpleName() + ": " + e.getMessage());
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private static VerifyResult verifyPlanResponse(String planEndpoint, String planResponseJson) {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(verifyEndpointFor(planEndpoint));
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(TIMEOUT_MS);
            connection.setReadTimeout(TIMEOUT_MS);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);

            byte[] body = planResponseJson.getBytes(StandardCharsets.UTF_8);
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

            String verifyBody = result.toString();
            boolean valid = code >= 200 && code < 300 && jsonBooleanTrue(verifyBody, "valid");
            return new VerifyResult(valid, "HTTP " + code + "\n" + truncate(verifyBody));
        } catch (Exception e) {
            return new VerifyResult(false, e.getClass().getSimpleName() + ": " + e.getMessage());
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String verifyEndpointFor(String planEndpoint) {
        String endpoint = planEndpoint.trim();
        if (endpoint.endsWith("/plan")) {
            return endpoint.substring(0, endpoint.length() - "/plan".length()) + "/plan/verify";
        }
        if (endpoint.endsWith("/plan/")) {
            return endpoint.substring(0, endpoint.length() - "/plan/".length()) + "/plan/verify";
        }
        return endpoint.endsWith("/") ? endpoint + "plan/verify" : endpoint + "/plan/verify";
    }

    private static boolean jsonBooleanTrue(String json, String fieldName) {
        String compact = json.replaceAll("\\s+", "");
        return compact.contains("\"" + fieldName + "\":true");
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
