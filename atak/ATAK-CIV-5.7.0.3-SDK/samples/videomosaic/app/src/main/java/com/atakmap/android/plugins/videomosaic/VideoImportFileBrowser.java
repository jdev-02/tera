
package com.atakmap.android.plugins.videomosaic;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.os.Environment;
import android.util.AttributeSet;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.android.math.MathUtils;
import com.atakmap.android.plugins.VideoOverlay.R;

import org.apache.commons.lang.StringUtils;

import java.io.File;
import java.io.FilenameFilter;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import com.atakmap.coremap.locale.LocaleUtil;
import java.util.TimeZone;

//Based on code from
//https://github.com/mburman/Android-File-Explore

public class VideoImportFileBrowser extends LinearLayout {

    /*************************** CONSTRUCTORS **************************/

    public VideoImportFileBrowser(Context context) {
        super(context);
    }

    public VideoImportFileBrowser(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    /*************************** PUBLIC METHODS **************************/

    public void setUpButton(Button up) {
        _up = up;
        _up.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View arg0) {
                _navigateUpOneDirectory();
            }
        });
    }

    public File getReturnFile() {
        return _retFile;
    }

    public void setAlertDialog(AlertDialog alert) {
        _alert = alert;
    }

    /** 
     * Clears a previously selected file.
     */
    public void clear() {
        _retFile = null;
    }

    public void allowAnyExtenstionType() {
        this.setExtensionType(WILDCARD);
    }

    /**
     * Note must currently be called before _init();
     * 
     * @param path
     */
    public void setStartDirectory(String path) {
        _userStartDirectory = path;
    }

    public void setExtensionType(String extension) {
        this.setExtensionTypes(new String[] {
                extension
        });
    }

    public void setExtensionTypes(String[] extensions) {
        _extensions = extensions;
        _init();
    }

    public static String getModifiedDate(File file) {
        return getModifiedDate(file.lastModified());
    }

    public static String getModifiedDate(Long time) {
        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM yyyy HH:mm:ss",
                LocaleUtil.getCurrent());
        sdf.setTimeZone(TimeZone.getTimeZone("GMT"));
        return sdf.format(time);
    }

    /*************************** PROTECTED METHODS **************************/

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();
        if (_extensions != null) {
            _init();
        }
    }

    protected void _init() {
        _setInitialDirectory();
        _parseDirectoryPath();
        _loadFileList();
        _createAdapter();
        _initButtons();
        _initFileListView();
        _updateCurrentDirectoryTextView();
    }

    protected void _loadFileList() {
        _fileList.clear();
        if (_path.exists() && _path.canRead()) {
            FilenameFilter filter = new FilenameFilter() {
                public boolean accept(File dir, String fileName) {
                    File sel = new File(dir, fileName);
                    String ext = StringUtils.substringAfterLast(fileName, ".");
                    if (ext != null && sel.isFile()) {
                        return (_testExtension(ext.toLowerCase(LocaleUtil
                                .getCurrent())))
                                && sel.canRead();
                    }
                    return sel.canRead() && sel.isDirectory();
                }
            };
            String[] fList = _path.list(filter);
            _directoryEmpty = false;

            if (fList != null) {
                for (String f : fList) {
                    int id = R.drawable.import_file_icon;
                    int type = FileItem.FILE;
                    File sel = new File(_path, f);
                    if (sel.isDirectory()) {
                        id = R.drawable.import_folder_icon;
                        type = FileItem.DIRECTORY;
                    }
                    _fileList.add(new FileItem(f, id, type));
                }
            }
            if (_fileList.size() == 0) {
                _directoryEmpty = true;
                _fileList.add(new FileItem("Directory is empty", -1,
                        FileItem.FILE));
            } else {
                Collections.sort(_fileList, new FileItemComparator());
            }
        }
    }

    protected void _updateCurrentDirectoryTextView() {
        StringBuilder currDirString = new StringBuilder("");
        for (String d : _pathDirsList) {
            currDirString.append(d + FILE_SEPARATOR);
        }
        if (_pathDirsList.size() == 0) {
            if (_up != null)
                _up.setEnabled(false);
        } else {
            if (_up != null)
                _up.setEnabled(true);
        }
        ((TextView) this.findViewById(R.id.importBrowserCurrentDirectory))
                .setText("Current directory: " + currDirString.toString());
    }

    protected boolean _testExtension(String ext) {
        for (String e : _extensions) {
            if (e.equals(WILDCARD) || e.equalsIgnoreCase(ext))
                return true;
        }
        return false;
    }

    protected void _scrollListToTop() {
        ListView lv = (ListView) this
                .findViewById(R.id.importBrowserFileItemList);
        if (lv != null) {
            lv.setSelectionFromTop(0, 0);
        }
    }

    protected void _createAdapter() {
        _adapter = new FileItemAdapter(getContext(),
                R.layout.import_file_browser_fileitem,
                _fileList);
    }

    protected void _navigateUpOneDirectory() {
        _loadDirectoryUp();
        _loadFileList();
        _adapter.notifyDataSetChanged();
        _updateCurrentDirectoryTextView();

        _scrollListToTop();
    }

    /*************************** PRIVATE METHODS **************************/

    private void _setInitialDirectory() {
        // first check if user provided a directory to start in
        if (_userStartDirectory != null && _userStartDirectory.length() > 0) {
            File userDir = new File(_userStartDirectory);
            if (userDir.exists() && userDir.isDirectory()) {
                _path = userDir;
                return;
            }
        }

        // start in default directory
        File temp = new File(INITIAL_DIRECTORY);
        if (temp.isDirectory())
            _path = temp;
        if (_path == null) {
            if (Environment.getExternalStorageDirectory().isDirectory()
                    && Environment.getExternalStorageDirectory().canRead()) {
                _path = Environment.getExternalStorageDirectory();
            } else {
                _path = new File("/");
            }
        }
    }

    private void _parseDirectoryPath() {
        _pathDirsList.clear();
        String pathString = _path.getAbsolutePath();
        String[] parts = pathString.split(FILE_SEPARATOR);
        for (String p : parts)
            _pathDirsList.add(p);
    }

    private void _initButtons() {
        if (_up != null) {
            _up.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View arg0) {
                    _navigateUpOneDirectory();
                }
            });
        }
    }

    private void _loadDirectoryUp() {
        if (_pathDirsList.size() <= 1)
            return;
        String s = _pathDirsList.remove(_pathDirsList.size() - 1);
        _path = new File(_path.toString().substring(0,
                _path.toString().lastIndexOf(s)));
        _fileList.clear();
    }

    private void _initFileListView() {
        ListView list = (ListView) this
                .findViewById(R.id.importBrowserFileItemList);
        list.setAdapter(_adapter);
    }

    private void _returnFile(File file) {
        _retFile = file;
        _alert.dismiss();
    }

    /*************************** PRIVATE FIELDS **************************/
    private String[] _extensions;
    private String _userStartDirectory;
    private File _retFile;
    private Button _up;
    private static final String FILE_SEPARATOR = System
            .getProperty("file.separator");
    private static final String INITIAL_DIRECTORY = FileSystemUtils.getRoot()
            + FILE_SEPARATOR;
    private AlertDialog _alert;

    /*************************** PROTECTED FIELDS **************************/
    protected ArrayList<String> _pathDirsList = new ArrayList<String>();
    protected List<FileItem> _fileList = new ArrayList<FileItem>();
    protected File _path;
    protected String _currFile;
    protected ArrayAdapter<FileItem> _adapter;
    protected boolean _directoryEmpty;

    /*************************** PUBLIC FIELDS **************************/
    public static String WILDCARD = "*";

    /*************************** PROTECTED CLASSES **************************/

    protected class FileItem {
        public String file;
        public int icon;
        public static final int FILE = 0x1;
        public static final int DIRECTORY = 0x1 << 1;
        public int type;

        public FileItem(String file, Integer icon, Integer type) {
            this.file = file;
            this.icon = icon;
            this.type = type;
        }

        @Override
        public String toString() {
            return file;
        }

    }

    /*************************** PRIVATE CLASSES **************************/

    private static class FileItemComparator implements Comparator<FileItem> {
        public int compare(FileItem i0, FileItem i1) {
            if (i0.type == i1.type) {
                return i0.file.toLowerCase(LocaleUtil.getCurrent()).compareTo(
                        i1.file.toLowerCase(LocaleUtil.getCurrent()));
            } else if (i0.type == FileItem.FILE) {
                return -1;
            } else if (i0.type == FileItem.DIRECTORY) {
                return 1;
            }
            return i0.file.toLowerCase(LocaleUtil.getCurrent()).compareTo(
                    i1.file.toLowerCase(LocaleUtil.getCurrent()));
        }
    }

    /**
     * @author byoung
     */
    private class FileItemAdapter extends ArrayAdapter<FileItem> {

        Context context;

        public FileItemAdapter(Context context, int resourceId,
                List<FileItem> items) {
            super(context, resourceId, items);
            this.context = context;
        }

        /* private view holder class */
        private class ViewHolder {
            Button icon;
            TextView txtFilename;
            TextView txtModifiedDate;
        }

        public View getView(int position, View convertView, ViewGroup parent) {
            ViewHolder holder = null;
            final FileItem fileItem = getItem(position);

            LayoutInflater mInflater = (LayoutInflater) context
                    .getSystemService(Activity.LAYOUT_INFLATER_SERVICE);
            if (convertView == null) {
                convertView = mInflater.inflate(
                        R.layout.import_file_browser_fileitem, null);
                holder = new ViewHolder();
                holder.txtFilename = (TextView) convertView
                        .findViewById(R.id.importBrowserFileName);
                holder.txtModifiedDate = (TextView) convertView
                        .findViewById(R.id.importBrowserModifiedDate);
                holder.icon = (Button) convertView
                        .findViewById(R.id.importBrowserIcon);
                convertView.setTag(holder);
            } else
                holder = (ViewHolder) convertView.getTag();

            File f = new File(_path, fileItem.file);
            holder.txtFilename.setText(f.getName());
            if (f.exists())
                holder.txtModifiedDate.setText(getModifiedDate(f));
            else
                holder.txtModifiedDate.setText("");
            int drawable = 0;
            if (_fileList.get(position).icon != -1) {
                drawable = fileItem.icon;
            }
            holder.icon.setCompoundDrawablesWithIntrinsicBounds(0, drawable, 0,
                    0);
            if (fileItem.type == FileItem.FILE) {
                if (f.exists())
                    holder.icon.setText(MathUtils.GetLengthString(f.length()));
                else {
                    holder.icon.setText("");
                    holder.txtModifiedDate.setText("");
                }
            } else {
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
                    holder.icon.setText("");
                } else {
                    holder.icon.setText(String.format("%d items",
                            children.length));
                }
            }

            // handle user clicks
            holder.icon.setClickable(false);
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
                        if (!_directoryEmpty) {
                            _returnFile(sel);
                        }
                    }
                }
            });
            return convertView;
        }
    }

}
