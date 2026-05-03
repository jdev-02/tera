package com.atakmap.android.sampledetailtester;

import com.atakmap.android.cot.detail.CotDetailHandler;
import com.atakmap.android.maps.MapItem;
import com.atakmap.comms.CommsMapComponent;
import com.atakmap.coremap.cot.event.CotDetail;
import com.atakmap.coremap.cot.event.CotEvent;
import com.atakmap.coremap.log.Log;

class StudentDetailHandler extends CotDetailHandler {
    private final String TAG = "StudentDetailHandler";

    public StudentDetailHandler() {
        super("__student");
    }

    @Override
    public CommsMapComponent.ImportResult toItemMetadata(
            MapItem item, CotEvent event, CotDetail detail) {
        Log.d(TAG, "detail received: " + detail + " in:  "
                + event);

        String firstname = detail.getAttribute("firstname");
        String surname = detail.getAttribute("surname");
        int grade = Integer.parseInt(detail.getAttribute("grade"));

        CotDetail classes = detail.getChild("classes");
        for (int i = 0; i < classes.childCount(); ++i) {
            CotDetail period = classes.getChild(i);
            parsePeriod(period);
        }

        return CommsMapComponent.ImportResult.SUCCESS;
    }

    @Override
    public boolean toCotDetail(MapItem item, CotEvent event,
                               CotDetail root) {
        Log.d(TAG, "converting to cot detail from: "
                + item.getUID());


        CotDetail student = new CotDetail("student");
        student.setAttribute("firstname", "Robert");
        student.setAttribute("surname", "Robertson");
        student.setAttribute("grade", "11");

        CotDetail classes = new CotDetail("classes");

        classes.addChild(makePeriod(1, "Mr. Roseboom", "21A", 3.14, "English", 1));
        classes.addChild(makePeriod(2, "Ms. Samuelson", "11C", 3.04, "Chemistry", 1));
        classes.addChild(makePeriod(3, "Mr. Smith", "121B", 3.50, "History", 1));

        student.addChild(classes);
        root.addChild(student);

        return true;
    }


    private CotDetail makePeriod(int period, String name, String room, double grade, String subject, int absences) {
        CotDetail periodDetail = new CotDetail("period");
        periodDetail.setAttribute("number", Integer.toString(period));
        periodDetail.setAttribute("teacher", name);
        periodDetail.setAttribute("room", room);
        periodDetail.setAttribute("gps", Double.toString(grade));
        periodDetail.setAttribute("subject", subject);
        // note V2 of the period contains absences
        periodDetail.setAttribute("absences", Integer.toString(absences));
        return periodDetail;
    }

    private void parsePeriod(CotDetail periodDetail) {
        int period = Integer.parseInt(periodDetail.getAttribute("number"));
        String teacher = periodDetail.getAttribute("teacher");
        String room = periodDetail.getAttribute("room");

        double grade = Double.parseDouble(periodDetail.getAttribute("grade"));
        String subject = periodDetail.getAttribute("subject");

        // note V2 of the period contains absences
        if (periodDetail.getAttribute("absences") != null) {
            int absences = Integer.parseInt(periodDetail.getAttribute("absences"));
        }
    }

}
