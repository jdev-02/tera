
package com.atakmap.android.plugins;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.graphics.drawable.Drawable;
import android.text.Html;
import android.util.AttributeSet;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.TextView;

import com.atakmap.coremap.log.Log;
import com.atakmap.android.math.MathUtils;
import com.atakmap.android.plugins.VideoOverlay.R;

import org.apache.commons.lang.StringUtils;

import java.io.File;
import java.io.FilenameFilter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

/**
 * Extended version of the ImportFileBrowser that can be used to select multiple files
 * and includes an up button within the view instead of requiring an external one.
 */
public class VideoOverlayManagerFileBrowser extends
        VideoOverlayImportFileBrowser implements
        DialogInterface.OnKeyListener {
    private static final String TAG = "ImportManagerFileBrowser";

    private Set<File> selectedItems = new HashSet<File>();

    public VideoOverlayManagerFileBrowser(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    public VideoOverlayManagerFileBrowser(Context context) {
        super(context);
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();

        // After the view finishes inflating, attach an on click
        // handler to the up/back button next to the current directory.
        Button upButton = (Button) this
                .findViewById(R.id.importManagerFileBrowserUpButton);
        if (upButton != null) {
            setUpButton(upButton);
        }
    }

    @Override
    protected void _createAdapter() {
        // Create an adapter that can handle selection via check boxes.
        _adapter = new FileItemAdapter(getContext(),
                R.layout.import_manager_file_browser_fileitem,
                _fileList);
    }

    @Override
    public void setAlertDialog(AlertDialog alert) {
        super.setAlertDialog(alert);

        // This will take over the handling of events for the Back
        // button while the dialog is opened.
        alert.setOnKeyListener(this);
    }

    /**
     * Returns a list containing all of the files and directories
     * that the user has selected using this dialog. If no items
     * have been selected, an empty list will be returned.
     * @return List of selected files, or empty list if nothing was 
     * selected.
     */
    public List<File> getSelectedFiles() {
        List<File> returnVal = new ArrayList<File>();
        returnVal.addAll(selectedItems);

        return returnVal;
    }

    @Override
    public boolean onKey(DialogInterface dialog, int keyCode, KeyEvent event) {
        // Handle the "UP" event for the device's back button. This hijacks the
        // "Cancel" behavior that is normally present in a dialog, and instead
        // treats a press as an indication that the user would like to move
        // up one directory.
        if (keyCode == KeyEvent.KEYCODE_BACK
                && event.getAction() == KeyEvent.ACTION_UP) {
            _navigateUpOneDirectory();
            return true;
        }
        return false;
    }

    private class FileItemAdapter extends ArrayAdapter<FileItem> {

        private Context context;
        private Drawable folderDrawable;
        private Drawable fileDrawable;

        public FileItemAdapter(Context context, int resourceId,
                List<FileItem> items) {
            super(context, resourceId, items);
            this.context = context;

            // Create drawables once so that they can be reused.
            folderDrawable = context.getResources().getDrawable(
                    R.drawable.import_folder_icon);
            fileDrawable = context.getResources().getDrawable(
                    R.drawable.import_file_icon);
        }

        // Check to see if a checkbox is checked or not, and update
        // the selectedItems set accordingly.
        private void recordCheckBox(CheckBox c, FileItem fileItem) {
            boolean isChecked = c.isChecked();
            try {
                File selectedFile = new File(_path, fileItem.file)
                        .getCanonicalFile();
                if (isChecked) {
                    // If the newly checked file is the parent of a file that
                    // is already in the selectedItems list, remove that item
                    // from the selectedItems list to avoid importing items
                    // twice.
                    for (Iterator<File> it = selectedItems.iterator(); it
                            .hasNext();) {
                        File next = it.next();
                        if (isParent(selectedFile, next)) {
                            it.remove();
                        }
                    }

                    selectedItems.add(selectedFile);
                } else {
                    selectedItems.remove(selectedFile);
                }
            } catch (IOException e) {
                Log.e(TAG, "Couldn't find canonical file.", e);
            }
        }

        private boolean isParent(File possibleParent, File file) {
            if (!possibleParent.exists() || !possibleParent.isDirectory() ||
                    possibleParent.equals(file)) {
                // this cannot possibly be the parent
                return false;
            }

            File possibleChild = file.getParentFile();
            while (possibleChild != null) {
                if (possibleChild.equals(possibleParent)) {
                    return true;
                }
                possibleChild = possibleChild.getParentFile();
            }

            // No match found, and we've hit the root directory
            return false;
        }

        private boolean isParentSelected(FileItem item) {
            try {
                File fileToTest = new File(_path, item.file).getCanonicalFile();
                for (File f : selectedItems) {
                    if (isParent(f, fileToTest)) {
                        return true;
                    }
                }
                return false;
            } catch (IOException e) {
                Log.e(TAG, "Couldn't check for parent.", e);
                return false;
            }
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            final FileItem fileItem = getItem(position);

            LayoutInflater mInflater = (LayoutInflater) context
                    .getSystemService(Activity.LAYOUT_INFLATER_SERVICE);
            if (convertView == null) {
                convertView = mInflater.inflate(
                        R.layout.import_manager_file_browser_fileitem, null);
            }

            // Find all of our widgets so that we can refer to them by a shortened name
            Button iconButton = ((Button) convertView
                    .findViewById(R.id.importManagerBrowserIcon));
            TextView fileNameView = ((TextView) convertView
                    .findViewById(R.id.importManagerBrowserFileName));
            TextView fileInfoView = ((TextView) convertView
                    .findViewById(R.id.importManagerBrowserFileInfo));
            CheckBox selectedCheckBox = ((CheckBox) convertView
                    .findViewById(R.id.importManagerBrowserFileSelected));

            // Handle the special case where a directory does not contain any files.
            // This changes the list to simply display an item that says "Directory is Empty"
            // without checkboxes or icons.
            if (_directoryEmpty) {
                iconButton.setBackgroundDrawable(null);
                fileNameView.setText(Html.fromHtml("<i>" + fileItem.file
                        + "</i>"));
                fileInfoView.setText("");
                selectedCheckBox.setVisibility(View.INVISIBLE);

                convertView.setOnClickListener(null);

                return convertView;
            } else {
                selectedCheckBox.setVisibility(View.VISIBLE);
            }

            // We don't want the iconButton to handle click events because it prevents them
            // from makeing it to the click handler we will be adding later.
            iconButton.setClickable(false);

            // If this item has been selected, update the checkbox state,
            // otherwise uncheck it.
            selectedCheckBox.setChecked(selectedItems.contains(new File(_path,
                    fileItem.file)));

            // If one of the file's parents has been selected, disable the checkbox
            // so that it can't be toggled by itself. also make the box checked
            // to indicate that the user can't mess with them independent of the
            // parent.
            if (isParentSelected(fileItem)) {
                selectedCheckBox.setChecked(true);
                selectedCheckBox.setEnabled(false);
            } else {
                selectedCheckBox.setEnabled(true);
            }

            File f = new File(_path, fileItem.file);

            fileNameView.setText(f.getName());

            if (fileItem.type == FileItem.DIRECTORY) {
                iconButton.setBackgroundDrawable(folderDrawable);

                // Filter out undesired file types
                FilenameFilter filter = new FilenameFilter() {
                    public boolean accept(File dir, String fileName) {
                        File sel = new File(dir, fileName);
                        String ext = StringUtils.substringAfterLast(fileName,
                                ".");
                        if (sel.isFile()) {
                            return (_testExtension(ext)) && sel.canRead();
                        }
                        return sel.canRead() && sel.isDirectory();
                    }
                };

                String[] children = f.list(filter);
                if (children == null || children.length < 1) {
                    fileInfoView.setText("");
                } else {
                    fileInfoView.setText(String.format("%d items",
                            children.length));
                }

            } else {
                iconButton.setBackgroundDrawable(fileDrawable);
                fileInfoView.setText(MathUtils.GetLengthString(f.length()));
            }

            selectedCheckBox.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (v instanceof CheckBox) {
                        recordCheckBox((CheckBox) v, fileItem);
                    }
                }
            });

            convertView.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View v) {
                    _currFile = fileItem.file;
                    File sel = new File(_path, _currFile);
                    if (sel.isDirectory()) {
                        if (sel.canRead()) {
                            _pathDirsList.add(_currFile);
                            _path = new File(sel + "");
                            _loadFileList();
                            _adapter.notifyDataSetChanged();
                            _updateCurrentDirectoryTextView();

                            _scrollListToTop();
                        }
                    } else {
                        // Clicking on an item that is not a directory
                        // treats the click the same as if the user had clicked
                        // on the entry's checkbox.
                        CheckBox c = (CheckBox) v
                                .findViewById(
                                        R.id.importManagerBrowserFileSelected);
                        if (c != null) {
                            c.toggle();
                            recordCheckBox(c, fileItem);
                        }
                    }
                }
            });

            // Long clicking on any item treats the click the same as if
            // the user had clicked on the item's checkbox.
            convertView.setOnLongClickListener(new OnLongClickListener() {
                @Override
                public boolean onLongClick(View v) {
                    _currFile = fileItem.file;
                    CheckBox c = (CheckBox) v
                            .findViewById(
                                    R.id.importManagerBrowserFileSelected);
                    if (c != null) {
                        c.toggle();
                        recordCheckBox(c, fileItem);
                    }
                    return true;
                }
            });

            return convertView;
        }
    }

}
