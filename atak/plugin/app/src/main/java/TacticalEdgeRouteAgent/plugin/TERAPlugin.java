
package TacticalEdgeRouteAgent.plugin;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.text.InputType;
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

import com.atak.plugins.impl.PluginContextProvider;
import com.atak.plugins.impl.PluginLayoutInflater;

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
        final TextView status = teraView.findViewById(R.id.tera_status);
        final TextView response = teraView.findViewById(R.id.tera_response);
        final StringBuilder chatHistory = new StringBuilder();
        final StringBuilder hostState = new StringBuilder();
        final boolean[] ttsEnabled = new boolean[] { false };
        final boolean[] listening = new boolean[] { false };

        hostButton.setText(R.string.host_local);
        hostButton.setOnClickListener(v -> showHostPopup(hostButton, hostState, status));
        infoButton.setOnClickListener(v -> showInfoPopup(infoButton));
        voiceMessage.setOnClickListener(v -> toggleVoiceInput(
                voiceMessage, chatInput, status, listening));
        ttsToggle.setOnClickListener(v -> {
            ttsEnabled[0] = !ttsEnabled[0];
            ttsToggle.setBackgroundResource(ttsEnabled[0]
                    ? R.drawable.chat_icon_button_selected_bg
                    : R.drawable.chat_icon_button_bg);
            status.setText(ttsEnabled[0] ? "Text-to-speech enabled." : "Text-to-speech disabled.");
        });

        sendMessage.setOnClickListener(v -> {
            String message = chatInput.getText().toString().trim();
            if (message.isEmpty()) {
                return;
            }
            String host = hostState.toString();
            String endpoint = buildEndpoint(host);

            appendChatLine(chatHistory, host.isEmpty() ? "Operator (local)" : "Operator (" + host + ")", message);
            transcript.setText(chatHistory.toString());
            scrollChatToBottom(chatScroll);
            chatInput.setText("");
            sendMessage.setEnabled(false);
            connectionStatus.setText(R.string.connection_connecting);
            status.setText(R.string.status_sending);
            response.setText("");

            TeraPlanClient.requestPlan(
                    endpoint,
                    host.isEmpty() ? "local" : host,
                    message,
                    new TeraPlanClient.Callback() {
                        @Override
                        public void onComplete(boolean ok, String message) {
                            mainHandler.post(() -> {
                                sendMessage.setEnabled(true);
                                connectionStatus.setText(ok
                                        ? R.string.connection_online
                                        : R.string.connection_error);
                                status.setText(ok ? "Agent response received." : "Agent request failed.");
                                appendChatLine(chatHistory, ok ? "Agent" : "Error", message);
                                transcript.setText(chatHistory.toString());
                                scrollChatToBottom(chatScroll);
                            });
                        }
                    });
        });
    }

    private void showHostPopup(Button hostButton, StringBuilder hostState, TextView status) {
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

        LinearLayout actions = new LinearLayout(hostButton.getContext());
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(0, dp(10), 0, 0);

        Button apply = new Button(hostButton.getContext());
        apply.setText(R.string.host_popup_apply);
        apply.setTextSize(12);

        Button useLocal = new Button(hostButton.getContext());
        useLocal.setText(R.string.host_popup_local);
        useLocal.setTextSize(12);

        actions.addView(apply, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        actions.addView(useLocal, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        content.addView(title);
        content.addView(hostEdit, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(38)));
        content.addView(actions);

        PopupWindow popup = new PopupWindow(content, dp(300),
                LinearLayout.LayoutParams.WRAP_CONTENT, true);
        popup.setOutsideTouchable(true);
        popup.setClippingEnabled(false);
        popup.setInputMethodMode(PopupWindow.INPUT_METHOD_NEEDED);
        popup.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
                | WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
        popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));

        apply.setOnClickListener(v -> {
            hostState.setLength(0);
            hostState.append(hostEdit.getText().toString().trim());
            hostButton.setText(hostState.length() == 0
                    ? pluginContext.getString(R.string.host_local)
                    : hostState.toString());
            status.setText(hostState.length() == 0
                    ? "Host set to local."
                    : "Host set to " + hostState);
            popup.dismiss();
        });

        useLocal.setOnClickListener(v -> {
            hostState.setLength(0);
            hostButton.setText(R.string.host_local);
            status.setText("Host set to local.");
            popup.dismiss();
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

    private void toggleVoiceInput(View voiceButton, EditText chatInput, TextView status,
                                  boolean[] listening) {
        if (!SpeechRecognizer.isRecognitionAvailable(pluginContext)) {
            status.setText("Speech recognition is not available on this device.");
            return;
        }

        if (listening[0]) {
            if (speechRecognizer != null) {
                speechRecognizer.stopListening();
            }
            listening[0] = false;
            voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
            status.setText("Voice input stopped.");
            return;
        }

        if (speechRecognizer == null) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(pluginContext);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override
                public void onReadyForSpeech(Bundle params) {
                    status.setText(R.string.status_listening);
                }

                @Override
                public void onBeginningOfSpeech() {
                    status.setText("Listening...");
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
                    status.setText("Processing voice input...");
                }

                @Override
                public void onError(int error) {
                    listening[0] = false;
                    voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
                    status.setText("Voice input failed: " + speechErrorMessage(error));
                }

                @Override
                public void onResults(Bundle results) {
                    listening[0] = false;
                    voiceButton.setBackgroundResource(R.drawable.chat_icon_button_bg);
                    java.util.ArrayList<String> matches = results.getStringArrayList(
                            SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches == null || matches.isEmpty()) {
                        status.setText("No voice input detected.");
                        return;
                    }
                    chatInput.setText(matches.get(0));
                    chatInput.setSelection(chatInput.getText().length());
                    status.setText("Voice input added to chat.");
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
        status.setText(R.string.status_listening);
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
        if (!endpoint.endsWith(pluginContext.getString(R.string.endpoint_path))) {
            endpoint = endpoint + pluginContext.getString(R.string.endpoint_path);
        }
        return endpoint;
    }

    private void showInfoPopup(View anchor) {
        LinearLayout content = new LinearLayout(anchor.getContext());
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = dp(12);
        content.setPadding(padding, padding, padding, padding);
        content.setBackgroundResource(R.drawable.status_bar_bg);

        TextView title = new TextView(anchor.getContext());
        title.setText(R.string.tera_info_title);
        title.setTextColor(Color.WHITE);
        title.setTextSize(15);
        title.setTypeface(null, android.graphics.Typeface.BOLD);

        TextView message = new TextView(anchor.getContext());
        message.setText(R.string.tera_info_message);
        message.setTextColor(Color.WHITE);
        message.setTextSize(13);
        message.setPadding(0, dp(8), 0, 0);

        content.addView(title);
        content.addView(message);

        PopupWindow popup = new PopupWindow(content, dp(260), LinearLayout.LayoutParams.WRAP_CONTENT, true);
        popup.setOutsideTouchable(true);
        popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        popup.showAsDropDown(anchor, -dp(226), dp(6));
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
