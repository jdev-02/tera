
package TacticalEdgeRouteAgent.plugin;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.text.InputType;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.PopupWindow;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.atak.plugins.impl.PluginContextProvider;
import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.Marker;
import com.atakmap.android.maps.Polyline;
import com.atakmap.coremap.maps.coords.GeoBounds;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;
import gov.tak.api.ui.IHostUIService;
import gov.tak.api.ui.Pane;
import gov.tak.api.ui.PaneBuilder;
import gov.tak.api.ui.ToolbarItem;
import gov.tak.api.ui.ToolbarItemAdapter;
import gov.tak.platform.marshal.MarshalManager;

public class TERAPlugin implements IPlugin {

    IServiceController serviceController;
    Context pluginContext;
    IHostUIService uiService;
    ToolbarItem toolbarItem;
    Pane templatePane;
    Handler mainHandler = new Handler(Looper.getMainLooper());
    SpeechRecognizer speechRecognizer;
    final List<Polyline> activeRoutePolylines = new ArrayList<>();
    final List<Marker> activeWaypointMarkers = new ArrayList<>();
    final List<String> activeTeraItemUids = new ArrayList<>();
    final List<JSONObject> activeTeraItems = new ArrayList<>();
    static final String TERA_SHARED_PACKAGE_DIR = "/sdcard/fromTERA";

    public TERAPlugin(IServiceController serviceController) {
        this.serviceController = serviceController;
        final PluginContextProvider ctxProvider = serviceController
                .getService(PluginContextProvider.class);
        if (ctxProvider != null) {
            pluginContext = ctxProvider.getPluginContext();
            pluginContext.setTheme(R.style.ATAKPluginTheme);
        }

        // obtain the UI service
        uiService = serviceController.getService(IHostUIService.class);

        // initialize the toolbar button for the plugin

        // create the button and set the identifier to be well known
        // if you fail to do this, the toolbar configuration will never
        // be able to find it again after the user moves the icon.
        toolbarItem = new ToolbarItem.Builder(
                pluginContext.getString(R.string.app_name),
                MarshalManager.marshal(
                        pluginContext.getResources().getDrawable(R.drawable.ic_launcher),
                        android.graphics.drawable.Drawable.class,
                        gov.tak.api.commons.graphics.Bitmap.class))
                .setListener(new ToolbarItemAdapter() {
                    @Override
                    public void onClick(ToolbarItem item) {
                        showPane();
                    }
                }).setIdentifier(pluginContext.getPackageName())
                .build();
    }

    @Override
    public void onStart() {
        // the plugin is starting, add the button to the toolbar
        if (uiService == null)
            return;

        uiService.addToolbarItem(toolbarItem);
    }

    @Override
    public void onStop() {
        // the plugin is stopping, remove the button from the toolbar
        if (uiService == null)
            return;

        if (speechRecognizer != null) {
            speechRecognizer.destroy();
            speechRecognizer = null;
        }

        clearActiveRoute();
        uiService.removeToolbarItem(toolbarItem);
    }

    private void showPane() {
        // instantiate the plugin view if necessary
        if(templatePane == null) {
            // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
            // In this case, using it is not necessary - but I am putting it here to remind
            // developers to look at this Inflator

            View teraView = PluginLayoutInflater.inflate(pluginContext,
                    R.layout.main_layout, null);
            wireChatControls(teraView);

            templatePane = new PaneBuilder(teraView)
                    // relative location is set to default; pane will switch location dependent on
                    // current orientation of device screen
                    .setMetaValue(Pane.RELATIVE_LOCATION, Pane.Location.Default)
                    // pane will take up 50% of screen width in landscape mode
                    .setMetaValue(Pane.PREFERRED_WIDTH_RATIO, 0.5D)
                    // pane will take up 50% of screen height in portrait mode
                    .setMetaValue(Pane.PREFERRED_HEIGHT_RATIO, 0.5D)
                    .build();
        }

        // if the plugin pane is not visible, show it!
        if(!uiService.isPaneVisible(templatePane)) {
            uiService.showPane(templatePane, null);
        }
    }

    private void wireChatControls(View teraView) {
        final Button hostButton = teraView.findViewById(R.id.tera_host_input);
        final View infoButton = teraView.findViewById(R.id.tera_info);
        final TextView connectionStatus = teraView.findViewById(R.id.tera_connection_status);
        final ScrollView chatScroll = teraView.findViewById(R.id.tera_chat_scroll);
        final TextView transcript = teraView.findViewById(R.id.tera_chat_transcript);
        final EditText chatInput = teraView.findViewById(R.id.tera_chat_input);
        final View sendMessage = teraView.findViewById(R.id.tera_send_message);
        final View voiceMessage = teraView.findViewById(R.id.tera_voice_message);
        final View ttsToggle = teraView.findViewById(R.id.tera_tts_toggle);
        final StringBuilder chatHistory = new StringBuilder();
        final StringBuilder hostState = new StringBuilder();
        final boolean[] ttsEnabled = new boolean[] { false };
        final boolean[] listening = new boolean[] { false };

        hostButton.setText(R.string.host_local);
        hostButton.setOnClickListener(v -> showHostPopup(
                hostButton, hostState, connectionStatus));
        infoButton.setOnClickListener(v -> showInfoPopup(infoButton));
        voiceMessage.setOnClickListener(v -> toggleVoiceInput(
                voiceMessage, chatInput, listening));
        ttsToggle.setOnClickListener(v -> {
            ttsEnabled[0] = !ttsEnabled[0];
            ttsToggle.setBackgroundResource(ttsEnabled[0]
                    ? R.drawable.chat_icon_button_selected_bg
                    : R.drawable.chat_icon_button_bg);
            connectionStatus.setText(ttsEnabled[0] ? "TTS on" : "TTS off");
        });

        sendMessage.setOnClickListener(v -> {
            String message = chatInput.getText().toString().trim();
            if (message.isEmpty()) {
                return;
            }
            String host = hostState.toString();
            String endpoint = buildEndpoint(host);
            JSONObject mapContext = buildMapContext();

            appendChatLine(chatHistory, host.isEmpty() ? "Operator (local)" : "Operator (" + host + ")", message);
            transcript.setText(chatHistory.toString());
            scrollChatToBottom(chatScroll);
            chatInput.setText("");
            sendMessage.setEnabled(false);
            connectionStatus.setText(R.string.connection_connecting);

            TeraPlanClient.requestPlan(
                    endpoint,
                    message,
                    mapContext,
                    new TeraPlanClient.PlanCallback() {
                        @Override
                        public void onComplete(boolean ok, String msg, JSONObject planJson) {
                            mainHandler.post(() -> {
                                sendMessage.setEnabled(true);
                                connectionStatus.setText(ok
                                        ? pluginContext.getString(R.string.connection_online)
                                        : (msg.startsWith("Route signature invalid")
                                                ? "Route signature invalid - REJECTED"
                                                : pluginContext.getString(R.string.connection_error)));
                                appendChatLine(chatHistory, ok ? "Agent" : "Error", msg);
                                transcript.setText(chatHistory.toString());
                                scrollChatToBottom(chatScroll);
                                if (ok && planJson != null) {
                                    drawRoute(planJson);
                                }
                            });
                        }
                    });
        });
    }

    private void showHostPopup(Button hostButton, StringBuilder hostState,
                               TextView connectionStatus) {
        LinearLayout content = new LinearLayout(hostButton.getContext());
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = dp(12);
        content.setPadding(padding, padding, padding, padding);
        content.setBackgroundResource(R.drawable.status_bar_bg);

        TextView title = new TextView(hostButton.getContext());
        title.setText(R.string.host_popup_title);
        title.setTextColor(Color.WHITE);
        title.setTextSize(15);
        title.setTypeface(null, android.graphics.Typeface.BOLD);

        EditText hostEdit = new EditText(hostButton.getContext());
        hostEdit.setSingleLine(true);
        hostEdit.setInputType(InputType.TYPE_CLASS_TEXT
                | InputType.TYPE_TEXT_VARIATION_URI
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        hostEdit.setHint(R.string.host_input_hint);
        hostEdit.setText(hostState.toString());
        hostEdit.setTextSize(13);
        hostEdit.setTextColor(Color.BLACK);
        hostEdit.setHintTextColor(Color.GRAY);
        hostEdit.setBackgroundResource(R.drawable.host_input_bg);
        hostEdit.setPadding(dp(10), 0, dp(10), 0);
        hostEdit.setSelectAllOnFocus(false);

        TextView result = new TextView(hostButton.getContext());
        result.setTextColor(Color.WHITE);
        result.setTextSize(14);
        result.setLineSpacing(dp(2), 1.0f);
        result.setPadding(0, dp(10), 0, 0);
        result.setVisibility(View.GONE);

        LinearLayout actions = new LinearLayout(hostButton.getContext());
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(0, dp(10), 0, 0);

        Button connect = new Button(hostButton.getContext());
        connect.setText(R.string.host_popup_connect);
        connect.setTextSize(12);

        Button useLocal = new Button(hostButton.getContext());
        useLocal.setText(R.string.host_popup_local);
        useLocal.setTextSize(12);

        actions.addView(connect, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        actions.addView(useLocal, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        content.addView(title);
        content.addView(hostEdit, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(38)));
        content.addView(result);
        content.addView(actions);

        PopupWindow popup = new PopupWindow(content, dp(300),
                LinearLayout.LayoutParams.WRAP_CONTENT, true);
        popup.setOutsideTouchable(true);
        popup.setClippingEnabled(false);
        popup.setInputMethodMode(PopupWindow.INPUT_METHOD_NEEDED);
        popup.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
                | WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
        popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));

        useLocal.setOnClickListener(v -> {
            hostState.setLength(0);
            hostButton.setText(R.string.host_local);
            connectionStatus.setText(R.string.connection_offline);
            popup.dismiss();
        });

        connect.setOnClickListener(v -> {
            String host = hostEdit.getText().toString().trim();
            String endpoint = buildEndpoint(host);
            hideKeyboard(hostEdit);
            connect.setEnabled(false);
            connect.setText("...");
            connectionStatus.setText(R.string.connection_connecting);
            result.setVisibility(View.VISIBLE);
            result.setText("Testing:\n" + endpoint);
            TeraPlanClient.checkJetson(endpoint, new TeraPlanClient.Callback() {
                @Override
                public void onComplete(boolean ok, String message) {
                    mainHandler.post(() -> {
                        connect.setEnabled(true);
                        connect.setText(R.string.host_popup_connect);
                        connectionStatus.setText(ok
                                ? R.string.connection_online
                                : R.string.connection_error);
                        result.setText(message + "\n\nEndpoint:\n" + endpoint);
                        if (ok) {
                            hostState.setLength(0);
                            hostState.append(host);
                            hostButton.setText(hostState.length() == 0
                                    ? pluginContext.getString(R.string.host_local)
                                    : hostState.toString());
                            popup.dismiss();
                        }
                    });
                }
            });
        });

        popup.showAtLocation(hostButton.getRootView(),
                Gravity.TOP | Gravity.CENTER_HORIZONTAL, 0, dp(18));
        hostEdit.requestFocus();
        mainHandler.postDelayed(() -> {
            InputMethodManager imm = (InputMethodManager) pluginContext.getSystemService(
                    Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.showSoftInput(hostEdit, InputMethodManager.SHOW_IMPLICIT);
            }
        }, 100);
    }

    private void toggleVoiceInput(View voiceButton, EditText chatInput, boolean[] listening) {
        if (!SpeechRecognizer.isRecognitionAvailable(pluginContext)) {
            chatInput.setHint("Speech recognition unavailable");
            return;
        }

        if (listening[0]) {
            if (speechRecognizer != null) {
                speechRecognizer.stopListening();
            }
            listening[0] = false;
            voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
            chatInput.setHint(R.string.chat_input_hint);
            return;
        }

        if (speechRecognizer == null) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(pluginContext);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override
                public void onReadyForSpeech(Bundle params) {
                    chatInput.setHint(R.string.status_listening);
                }

                @Override
                public void onBeginningOfSpeech() {
                    chatInput.setHint(R.string.status_listening);
                }

                @Override
                public void onRmsChanged(float rmsdB) {
                }

                @Override
                public void onBufferReceived(byte[] buffer) {
                }

                @Override
                public void onEndOfSpeech() {
                    listening[0] = false;
                    voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
                    chatInput.setHint("Processing voice...");
                }

                @Override
                public void onError(int error) {
                    listening[0] = false;
                    voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
                    chatInput.setHint("Voice failed: " + speechErrorMessage(error));
                }

                @Override
                public void onResults(Bundle results) {
                    listening[0] = false;
                    voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
                    java.util.ArrayList<String> matches = results.getStringArrayList(
                            SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches == null || matches.isEmpty()) {
                        chatInput.setHint("No voice detected");
                        return;
                    }
                    chatInput.setText(matches.get(0));
                    chatInput.setSelection(chatInput.getText().length());
                    chatInput.setHint(R.string.chat_input_hint);
                }

                @Override
                public void onPartialResults(Bundle partialResults) {
                    java.util.ArrayList<String> matches = partialResults.getStringArrayList(
                            SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches != null && !matches.isEmpty()) {
                        chatInput.setText(matches.get(0));
                        chatInput.setSelection(chatInput.getText().length());
                    }
                }

                @Override
                public void onEvent(int eventType, Bundle params) {
                }
            });
        }

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, pluginContext.getPackageName());

        listening[0] = true;
        voiceButton.setBackgroundResource(R.drawable.chat_icon_button_selected_bg);
        chatInput.setHint(R.string.status_listening);
        speechRecognizer.startListening(intent);
    }

    private String speechErrorMessage(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                return "audio error";
            case SpeechRecognizer.ERROR_CLIENT:
                return "client error";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                return "microphone permission missing";
            case SpeechRecognizer.ERROR_NETWORK:
                return "network error";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                return "network timeout";
            case SpeechRecognizer.ERROR_NO_MATCH:
                return "no match";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                return "recognizer busy";
            case SpeechRecognizer.ERROR_SERVER:
                return "server error";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return "speech timeout";
            default:
                return "error " + error;
        }
    }

    private String buildEndpoint(String host) {
        if (host == null || host.trim().isEmpty()) {
            return pluginContext.getString(R.string.endpoint_hint);
        }

        String endpoint = host.trim();
        if (!endpoint.startsWith("http://") && !endpoint.startsWith("https://")) {
            endpoint = "http://" + endpoint;
        }
        int schemeIndex = endpoint.indexOf("://");
        int pathStart = schemeIndex >= 0
                ? endpoint.indexOf("/", schemeIndex + 3)
                : endpoint.indexOf("/");
        String base = pathStart >= 0 ? endpoint.substring(0, pathStart) : endpoint;
        String path = pathStart >= 0 ? endpoint.substring(pathStart) : "";
        int authorityStart = schemeIndex >= 0 ? schemeIndex + 3 : 0;
        String authority = base.substring(Math.min(authorityStart, base.length()));
        int bracketEnd = authority.indexOf("]");
        int portColon = authority.lastIndexOf(":");
        boolean hasPort = portColon >= 0 && portColon > bracketEnd;
        if (!hasPort) {
            base = base + ":8080";
        }
        if (path.isEmpty() || "/".equals(path)) {
            return base + pluginContext.getString(R.string.endpoint_path);
        }
        return base + path;
    }

    private void clearActiveRoute() {
        MapView mapView = MapView.getMapView();
        if (mapView == null) return;
        for (Polyline polyline : activeRoutePolylines) {
            mapView.getRootGroup().removeItem(polyline);
        }
        activeRoutePolylines.clear();
        for (Marker m : activeWaypointMarkers) {
            mapView.getRootGroup().removeItem(m);
        }
        activeWaypointMarkers.clear();
        activeTeraItemUids.clear();
        activeTeraItems.clear();
    }

    private void drawRoute(JSONObject planJson) {
        MapView mapView = MapView.getMapView();
        if (mapView == null) return;

        try {
            String savedPackage = saveTakPackage(planJson);
            if (savedPackage != null) {
                Toast.makeText(pluginContext, "Saved TERA TAK package: " + savedPackage,
                        Toast.LENGTH_LONG).show();
            }

            if (applyTakCot(planJson, mapView)) {
                return;
            }

            clearActiveRoute();

            // Extract LineString coordinates from route.geometry.coordinates
            // GeoJSON format: [[lon, lat], [lon, lat], ...]
            JSONObject route = planJson.optJSONObject("route");
            if (route == null) {
                Toast.makeText(pluginContext, "No route in response", Toast.LENGTH_SHORT).show();
                return;
            }
            JSONObject geometry = route.optJSONObject("geometry");
            if (geometry == null) {
                geometry = route; // some responses embed geometry directly
            }
            JSONArray coords = geometry.optJSONArray("coordinates");
            if (coords == null || coords.length() < 2) {
                Toast.makeText(pluginContext, "Route has no coordinates", Toast.LENGTH_SHORT).show();
                return;
            }

            GeoPoint[] points = new GeoPoint[coords.length()];
            double sumLat = 0, sumLon = 0;
            for (int i = 0; i < coords.length(); i++) {
                JSONArray coord = coords.getJSONArray(i);
                double lon = coord.getDouble(0);
                double lat = coord.getDouble(1);
                points[i] = new GeoPoint(lat, lon);
                sumLat += lat;
                sumLon += lon;
            }

            // Draw blue polyline
            Polyline polyline = new Polyline(UUID.randomUUID().toString());
            polyline.setPoints(points);
            polyline.setColor(Color.argb(220, 0, 100, 255));
            polyline.setStrokeWeight(4.0);
            mapView.getRootGroup().addItem(polyline);
            activeRoutePolylines.add(polyline);

            // Add waypoint markers from waypoints array
            JSONArray waypoints = planJson.optJSONArray("waypoints");
            if (waypoints != null) {
                for (int i = 0; i < waypoints.length(); i++) {
                    JSONObject wp = waypoints.getJSONObject(i);
                    double lat = wp.getDouble("lat");
                    double lon = wp.getDouble("lon");
                    String name = wp.optString("name", wp.optString("label", "WP-" + (i + 1)));
                    GeoPoint gp = new GeoPoint(lat, lon);
                    Marker marker = new Marker(gp, UUID.randomUUID().toString());
                    marker.setTitle(name);
                    marker.setType("a-f-G-U-C");
                    mapView.getRootGroup().addItem(marker);
                    activeWaypointMarkers.add(marker);
                }
            }

            // Pan camera to route centre
            double centerLat = sumLat / coords.length();
            double centerLon = sumLon / coords.length();
            mapView.getMapController().panTo(new GeoPoint(centerLat, centerLon), true);

        } catch (JSONException e) {
            Toast.makeText(pluginContext, "Route parse error: " + e.getMessage(),
                    Toast.LENGTH_SHORT).show();
        }
    }

    private String saveTakPackage(JSONObject responseJson) {
        JSONObject takCot = responseJson.optJSONObject("tak_cot");
        if (takCot == null) {
            return null;
        }
        JSONObject pkg = takCot.optJSONObject("package");
        if (pkg == null) {
            return null;
        }

        String contentB64 = pkg.optString("content_b64", "");
        if (contentB64.trim().isEmpty()) {
            return null;
        }

        String fileName = sanitizeTakPackageFileName(pkg.optString("file_name", "TERA-TAK.kmz"));
        byte[] content;
        try {
            content = Base64.decode(contentB64, Base64.DEFAULT);
        } catch (IllegalArgumentException e) {
            Toast.makeText(pluginContext, "TAK package decode failed: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
            return null;
        }

        int expectedSize = pkg.optInt("size_bytes", -1);
        if (expectedSize > 0 && expectedSize != content.length) {
            Toast.makeText(pluginContext, "TAK package size mismatch; refusing write.",
                    Toast.LENGTH_LONG).show();
            return null;
        }
        String expectedSha = pkg.optString("sha256", "");
        if (!expectedSha.trim().isEmpty()
                && !expectedSha.equalsIgnoreCase(sha256Hex(content))) {
            Toast.makeText(pluginContext, "TAK package checksum mismatch; refusing write.",
                    Toast.LENGTH_LONG).show();
            return null;
        }

        IOException lastError = null;
        for (File outputDir : takPackageDirectories()) {
            try {
                File outputFile = writeTakPackageFile(outputDir, fileName, content);
                return outputFile.getAbsolutePath();
            } catch (IOException e) {
                lastError = e;
            }
        }

        String detail = lastError == null || lastError.getMessage() == null
                ? "unknown storage error"
                : lastError.getMessage();
        Toast.makeText(pluginContext, "TAK package write failed: " + detail,
                Toast.LENGTH_LONG).show();
        return null;
    }

    private List<File> takPackageDirectories() {
        List<File> directories = new ArrayList<>();
        addTakPackageDirectory(directories, new File(TERA_SHARED_PACKAGE_DIR));
        addTakPackageDirectory(directories, new File(
                Environment.getExternalStorageDirectory(), "fromTERA"));
        addTakPackageDirectory(directories, new File("/storage/emulated/0/fromTERA"));
        File appExternal = pluginContext.getExternalFilesDir("fromTERA");
        if (appExternal != null) {
            addTakPackageDirectory(directories, appExternal);
        }
        return directories;
    }

    private void addTakPackageDirectory(List<File> directories, File candidate) {
        String candidatePath = candidate.getAbsolutePath();
        for (File existing : directories) {
            if (existing.getAbsolutePath().equals(candidatePath)) {
                return;
            }
        }
        directories.add(candidate);
    }

    private File writeTakPackageFile(File outputDir, String fileName, byte[] content)
            throws IOException {
        if (!outputDir.exists() && !outputDir.mkdirs()) {
            throw new IOException("could not create " + outputDir.getAbsolutePath());
        }
        if (!outputDir.isDirectory()) {
            throw new IOException(outputDir.getAbsolutePath() + " is not a directory");
        }

        File outputFile = uniqueTakPackageFile(outputDir, fileName);
        try (FileOutputStream output = new FileOutputStream(outputFile)) {
            output.write(content);
            output.flush();
        }
        if (outputFile.length() != content.length) {
            throw new IOException("short write to " + outputFile.getAbsolutePath());
        }
        return outputFile;
    }

    private File uniqueTakPackageFile(File outputDir, String fileName) {
        File candidate = new File(outputDir, fileName);
        if (!candidate.exists()) {
            return candidate;
        }

        int dot = fileName.lastIndexOf('.');
        String stem = dot > 0 ? fileName.substring(0, dot) : fileName;
        String extension = dot > 0 ? fileName.substring(dot) : "";
        for (int index = 1; index < 1000; index++) {
            candidate = new File(outputDir, stem + "-" + index + extension);
            if (!candidate.exists()) {
                return candidate;
            }
        }
        return new File(outputDir, stem + "-" + System.currentTimeMillis() + extension);
    }

    private String sha256Hex(byte[] content) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(content);
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte value : hash) {
                hex.append(String.format(Locale.US, "%02x", value & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            return "";
        }
    }

    private String sanitizeTakPackageFileName(String rawName) {
        String name = rawName == null ? "" : rawName.replaceAll("[^A-Za-z0-9._-]", "_");
        name = name.replaceAll("^[._-]+", "").replaceAll("[._-]+$", "");
        if (name.isEmpty()) {
            name = "TERA-TAK";
        }
        String lower = name.toLowerCase(Locale.US);
        if (!lower.endsWith(".kmz") && !lower.endsWith(".kml") && !lower.endsWith(".zip")) {
            name = name + ".kmz";
        }
        return name;
    }

    private boolean applyTakCot(JSONObject responseJson, MapView mapView) throws JSONException {
        if (!responseJson.has("tak_cot")) {
            return false;
        }

        JSONObject takCot = responseJson.optJSONObject("tak_cot");
        if (takCot == null) {
            return true;
        }
        JSONArray items = takCot.optJSONArray("items");
        if (items == null || items.length() == 0) {
            return true;
        }

        if (takCot.optBoolean("replace_existing", true)) {
            clearActiveRoute();
        }

        double sumLat = 0.0;
        double sumLon = 0.0;
        int plottedCount = 0;

        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            String itemType = item.optString("item_type", "");
            if ("route".equals(itemType)) {
                int count = drawTakCotRoute(item, mapView);
                if (count > 0) {
                    JSONArray coordinates = item.optJSONArray("coordinates");
                    for (int j = 0; coordinates != null && j < coordinates.length(); j++) {
                        JSONArray coord = coordinates.getJSONArray(j);
                        sumLon += coord.getDouble(0);
                        sumLat += coord.getDouble(1);
                        plottedCount += 1;
                    }
                }
            } else if ("point".equals(itemType)) {
                Marker marker = drawTakCotPoint(item, mapView);
                if (marker != null) {
                    GeoPoint point = marker.getPoint();
                    sumLat += point.getLatitude();
                    sumLon += point.getLongitude();
                    plottedCount += 1;
                }
            }
        }

        if (plottedCount > 0) {
            mapView.getMapController().panTo(
                    new GeoPoint(sumLat / plottedCount, sumLon / plottedCount),
                    true);
        }
        return true;
    }

    private int drawTakCotRoute(JSONObject item, MapView mapView) throws JSONException {
        JSONArray coords = item.optJSONArray("coordinates");
        if (coords == null || coords.length() < 2) {
            return 0;
        }

        GeoPoint[] points = new GeoPoint[coords.length()];
        for (int i = 0; i < coords.length(); i++) {
            JSONArray coord = coords.getJSONArray(i);
            points[i] = new GeoPoint(coord.getDouble(1), coord.getDouble(0));
        }

        String uid = item.optString("uid", UUID.randomUUID().toString());
        Polyline polyline = new Polyline(uid);
        polyline.setPoints(points);
        polyline.setColor(Color.argb(230, 0, 135, 255));
        polyline.setStrokeWeight(5.0);
        mapView.getRootGroup().addItem(polyline);
        activeRoutePolylines.add(polyline);
        rememberActiveTeraItem(item, uid);

        JSONArray checkpoints = item.optJSONArray("checkpoints");
        for (int i = 0; checkpoints != null && i < checkpoints.length(); i++) {
            JSONObject cp = checkpoints.getJSONObject(i);
            String cpUid = cp.optString("uid", uid + "-cp-" + i);
            Marker marker = new Marker(
                    new GeoPoint(cp.getDouble("lat"), cp.getDouble("lon")),
                    cpUid);
            marker.setTitle(cp.optString("label", "CP-" + (i + 1)));
            marker.setType("a-f-G-U-C");
            mapView.getRootGroup().addItem(marker);
            activeWaypointMarkers.add(marker);
            activeTeraItemUids.add(cpUid);
        }
        return coords.length();
    }

    private Marker drawTakCotPoint(JSONObject item, MapView mapView) throws JSONException {
        if (!item.has("lat") || !item.has("lon")) {
            return null;
        }
        String uid = item.optString("uid", UUID.randomUUID().toString());
        Marker marker = new Marker(new GeoPoint(item.getDouble("lat"), item.getDouble("lon")), uid);
        marker.setTitle(item.optString("title", "TERA point"));
        marker.setType(item.optString("cot_type", "a-f-G-U-C"));
        mapView.getRootGroup().addItem(marker);
        activeWaypointMarkers.add(marker);
        rememberActiveTeraItem(item, uid);
        return marker;
    }

    private void rememberActiveTeraItem(JSONObject item, String uid) throws JSONException {
        activeTeraItemUids.add(uid);

        JSONObject active = new JSONObject();
        active.put("uid", uid);
        active.put("item_type", item.optString("item_type", ""));
        active.put("title", item.optString("title", ""));
        active.put("cot_type", item.optString("cot_type", ""));
        if (item.has("lat") && !item.isNull("lat")) {
            active.put("lat", item.getDouble("lat"));
        }
        if (item.has("lon") && !item.isNull("lon")) {
            active.put("lon", item.getDouble("lon"));
        }
        JSONObject metadata = item.optJSONObject("metadata");
        if (metadata != null) {
            active.put("metadata", metadata);
        }
        activeTeraItems.add(active);
    }

    private JSONObject buildMapContext() {
        try {
            MapView mapView = MapView.getMapView();
            if (mapView == null) {
                return null;
            }

            JSONObject context = new JSONObject();
            GeoPointMetaData centerMeta = mapView.getCenterPoint();
            if (centerMeta != null && centerMeta.get() != null && centerMeta.get().isValid()) {
                context.put("camera", pointToJson(centerMeta.get()));
            }

            GeoBounds bounds = mapView.getBounds();
            if (bounds != null) {
                JSONObject viewBounds = new JSONObject();
                viewBounds.put("west", bounds.getWest());
                viewBounds.put("south", bounds.getSouth());
                viewBounds.put("east", bounds.getEast());
                viewBounds.put("north", bounds.getNorth());
                GeoPoint center = bounds.getCenter(null);
                if (center != null && center.isValid()) {
                    viewBounds.put("center_lat", center.getLatitude());
                    viewBounds.put("center_lon", center.getLongitude());
                }
                context.put("view_bounds", viewBounds);
            }

            Marker self = mapView.getSelfMarker();
            if (self != null && self.getPoint() != null && self.getPoint().isValid()) {
                GeoPoint selfPoint = self.getPoint();
                context.put("client_location", pointToJson(selfPoint));
            }

            JSONArray activeItems = new JSONArray();
            if (!activeTeraItems.isEmpty()) {
                for (JSONObject activeItem : activeTeraItems) {
                    activeItems.put(new JSONObject(activeItem.toString()));
                }
            } else {
                for (String uid : activeTeraItemUids) {
                    JSONObject item = new JSONObject();
                    item.put("uid", uid);
                    activeItems.put(item);
                }
            }
            context.put("tera_active_items", activeItems);

            return context.length() == 0 ? null : context;
        } catch (JSONException e) {
            return null;
        }
    }

    private JSONObject pointToJson(GeoPoint point) throws JSONException {
        JSONObject json = new JSONObject();
        json.put("lat", point.getLatitude());
        json.put("lon", point.getLongitude());
        if (point.isAltitudeValid()) {
            json.put("height_m", point.getAltitude());
        }
        return json;
    }

    private void showInfoPopup(View anchor) {
        showMessagePopup(anchor, pluginContext.getString(R.string.tera_info_title),
                pluginContext.getString(R.string.tera_info_message));
    }

    private void showMessagePopup(View anchor, String titleText, String messageText) {
        LinearLayout content = new LinearLayout(anchor.getContext());
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = dp(12);
        content.setPadding(padding, padding, padding, padding);
        content.setBackgroundResource(R.drawable.status_bar_bg);

        TextView title = new TextView(anchor.getContext());
        title.setText(titleText);
        title.setTextColor(Color.WHITE);
        title.setTextSize(15);
        title.setTypeface(null, android.graphics.Typeface.BOLD);

        TextView message = new TextView(anchor.getContext());
        message.setText(messageText);
        message.setTextColor(Color.WHITE);
        message.setTextSize(14);
        message.setLineSpacing(dp(2), 1.0f);
        message.setPadding(0, dp(8), 0, 0);

        Button close = new Button(anchor.getContext());
        close.setText("OK");
        close.setTextSize(12);

        content.addView(title);
        content.addView(message);
        content.addView(close, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        PopupWindow popup = new PopupWindow(content, dp(320), LinearLayout.LayoutParams.WRAP_CONTENT, true);
        popup.setOutsideTouchable(true);
        popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        close.setOnClickListener(v -> popup.dismiss());
        popup.showAtLocation(anchor.getRootView(), Gravity.CENTER, 0, 0);
    }

    private void hideKeyboard(View view) {
        InputMethodManager imm = (InputMethodManager) pluginContext.getSystemService(
                Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.hideSoftInputFromWindow(view.getWindowToken(), 0);
        }
    }

    private int dp(int value) {
        float density = pluginContext.getResources().getDisplayMetrics().density;
        return (int) (value * density + 0.5f);
    }

    private void scrollChatToBottom(ScrollView chatScroll) {
        chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN));
    }

    private void appendChatLine(StringBuilder chatHistory, String sender, String message) {
        if (chatHistory.length() > 0) {
            chatHistory.append("\n\n");
        }
        chatHistory.append(sender).append(": ").append(message);
    }
}
