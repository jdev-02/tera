
package com.atakmap.android.sampledetailtester;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.cot.detail.CotDetailHandler;
import com.atakmap.android.cot.detail.CotDetailManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;

import com.atakmap.android.sampledetailtester.plugin.R;
import com.atakmap.android.sampledetailtester.proto.Period;
import com.atakmap.android.sampledetailtester.proto.Student;
import com.atakmap.commoncommo.CommoException;
import com.atakmap.comms.CotDetailExtensionException;
import com.atakmap.coremap.log.Log;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.StringBufferInputStream;
import java.io.StringWriter;
import java.nio.ByteBuffer;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

public class StudentMapComponent extends DropDownMapComponent {

    private static final String TAG = "CommsMap" + "StudentMapComponent";

    private Context pluginContext;

    private CotDetailHandler cotDetailHandler;

    
    private static class StudentExt implements com.atakmap.comms.CotDetailExtension {
        public byte[] encode(String xml) throws CotDetailExtensionException {
            Log.d(TAG, "ENCODE ENTER");
            
            try {
                DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
                DocumentBuilder db = dbf.newDocumentBuilder();
                Document doc = db.parse(new StringBufferInputStream(xml));
                Element studentElement = doc.getDocumentElement();

                if (!studentElement.getTagName().equals("student"))
                    throw new IllegalArgumentException("Wrong root element?");

                Student.Builder student = Student.newBuilder();

                student.setFirstname(studentElement.getAttribute("firstname"));
                student.setSurname(studentElement.getAttribute("surname"));
                student.setGrade(Integer.parseInt(studentElement.getAttribute("grade")));
                
                NodeList nl = studentElement.getElementsByTagName("period");
                for (int i = 0; i < nl.getLength(); i++) {
                    Period.Builder pb = Period.newBuilder();
                    Element period = (Element)nl.item(i);
                    pb.setNumber(Integer.parseInt(period.getAttribute("number")));
                    pb.setAbsences(Integer.parseInt(period.getAttribute("absences")));
                    pb.setTeacher(period.getAttribute("teacher"));
                    pb.setGps(Double.parseDouble(period.getAttribute("gps")));
                    pb.setRoom(period.getAttribute("room"));
                    student.addPeriod(pb);
                }
                Student s = student.build();
                byte[] b = s.toByteArray();
                Log.i(TAG, "Encoding compression " + xml.length() + " -> " + b.length);
                return b;
            } catch (Exception ex) {
                Log.e(TAG, "Could not encode given details document", ex);
                throw new CotDetailExtensionException("Could not encode given details document");
            }

        }

        public String decode(byte[] encoded) throws CotDetailExtensionException {
            try {
                Student s = Student.parseFrom(encoded);

                DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
                DocumentBuilder db = dbf.newDocumentBuilder();
                Document doc = db.newDocument();
                Element student = doc.createElement("student");
                doc.appendChild(student);
                student.setAttribute("firstname", s.getFirstname());
                student.setAttribute("surname", s.getSurname());
                student.setAttribute("grade", String.valueOf(s.getGrade()));

                int nClasses = s.getPeriodCount();
                if (nClasses > 0) {
                    Element c = doc.createElement("classes");
                    student.appendChild(c);
                    for (int i = 0; i < nClasses; ++i) {
                        Element period = doc.createElement("period");
                        Period p = s.getPeriod(i);
                        c.appendChild(period);
                        period.setAttribute("number", String.valueOf(p.getNumber()));
                        period.setAttribute("absences", String.valueOf(p.getAbsences()));
                        period.setAttribute("teacher", p.getTeacher());
                        period.setAttribute("gps", String.valueOf(p.getGps()));
                        period.setAttribute("room", p.getRoom());
                    }
                }

                TransformerFactory tf = TransformerFactory.newInstance();
                Transformer t = tf.newTransformer();
                DOMSource dom = new DOMSource(doc);
                StringWriter swriter = new StringWriter();
                StreamResult sr = new StreamResult(swriter);
                t.transform(dom, sr);
                return swriter.toString();
            } catch (Exception ex) {
                Log.e(TAG, "Could not decode given extension data", ex);
                throw new CotDetailExtensionException("Could not decode given extension data");
            }
        }
    }

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        pluginContext = context;
        if (com.atakmap.comms.CommsMapComponent.getInstance().registerCotDetailExtension(1, "student", new StudentExt()))
            Log.i(TAG, "Registered details extension successfully");
       else
           Log.e(TAG, "Could not register our details extension handler");

        CotDetailManager.getInstance().registerHandler(
                cotDetailHandler = new StudentDetailHandler());



    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);

        com.atakmap.comms.CommsMapComponent.getInstance().unregisterCotDetailExtension(1);

        CotDetailManager.getInstance().unregisterHandler(cotDetailHandler);


    }

}
