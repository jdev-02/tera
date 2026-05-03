package com.atakmap.android.cotinjector;

import com.atakmap.comms.CotDispatcher;
import com.atakmap.coremap.cot.event.CotEvent;
import com.atakmap.coremap.log.Log;
import com.atakmap.util.Diagnostic;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Random;
import java.util.TimeZone;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

import gov.tak.api.engine.map.coords.GeoPoint;

public class CotInjector {
   private final String TAG = CotInjector.class.getSimpleName();
   private final char[] AFFINITY = {'f', 'n', 'h', 'u'};
   private final char[] DIMENSION = {'P', 'A', 'G', 'S', 'U'};
   private final CotDispatcher internal = com.atakmap.android.cot.CotMapComponent.getInternalDispatcher();

   private double minLat;
   private double minLon;
   private double maxLat;
   private double maxLon;
   private AtomicInteger count = new AtomicInteger();
   private int interval;
   private int threads;
   private double deltaLat;
   private double deltaLon;
   private boolean cancelled;
   private Random random = new Random();
   private String updateUID;

   /**
    * Base constructor.
    *
    * @param lat1 Latitude of lower left corner of bounding rectangle
    * @param lon1 Longitude of lower left corner of bounding rectangle
    * @param lat2 Latitude of upper right corner of bounding rectangle
    * @param lon2 Longitude of upper right corner of bounding rectangle
    * @param count Number of CoT entities to generate
    * @param interval Amount of time between entity generation
    */
   public CotInjector(double lat1, double lon1,
                      double lat2, double lon2,
                      int count, int interval, int threads,
                      boolean updates) {
      setBounds(lat1, lon1, lat2, lon2);
      this.count.set(count);
      this.interval = interval;
      this.threads = threads;
      if (updates)
         updateUID = UUID.randomUUID().toString();
   }

   public void setUpdates(boolean updates) {
      if (!updates)
         updateUID = null;
      else
         updateUID = UUID.randomUUID().toString();
   }

   private class InjectorThread {

      InjectorThread(int threadIndex) {
         thread = new Thread(new Runnable() {
            @Override
            public void run() {
               while (!cancelled) {
                  final int countValue = count.get();
                  if (countValue == 0) {
                     completed = true;
                     break;
                  }
                  if (count.compareAndSet(countValue, countValue - 1)) {
                     String cotMsg = generateCotMessage(
                             updateUID != null ? updateUID : UUID.randomUUID().toString(), getRandomType(), getRandomPoint());
                     diagnostic.start();
                     sendCot(cotMsg);
                     diagnostic.stop();
                     try {
                        if (interval > 0) // prevents a thread yield
                           Thread.sleep(interval);
                     } catch (Exception ignored) {
                     }
                  }
               }
               Log.d("CotInjector", "diagnostic " + threadIndex + ": total= " + ((double) diagnostic.getDuration() / 1.e9) + " sec"
                       + ", count= " + diagnostic.getCount()
                       + ", avg= " + (((double) diagnostic.getDuration() / diagnostic.getCount()) / 1000.0) + " microsec");
            }
         }, "CotInjector-" + threadIndex);
      }

      void start() {
         thread.start();
      }

      Diagnostic diagnostic = new Diagnostic();
      final Thread thread;

      boolean completed;
   }

   /**
    * Start background thread to randomly generate CoT entities based on the parameters entered.
    */
   public void start() {
      cancelled = false;

      // create threads and diagnostics for each thread
      final  List<InjectorThread> threadList = new ArrayList<>();
      for (int threadIndex = 0; threadIndex < threads; ++threadIndex) {
         threadList.add(new InjectorThread(threadIndex));
      }

      // start all threads
      for (InjectorThread thread : threadList) {
         thread.start();
      }

      final int threadListSize = threadList.size();
      if (threadList.size() > 1) {
         new Thread(new Runnable() {
            @Override
            public void run() {
               double maxThreadDuration = 0.0;
               double minThreadDuration = Double.MAX_VALUE;
               double totalThreadDuration = 0.0;
               int totalCount = 0;
               for (InjectorThread thread : threadList) {
                  try {
                     thread.thread.join();
                  } catch (InterruptedException e) {
                     // ignore
                  }
                  double thisThreadDuration = thread.diagnostic.getDuration();
                  if (thisThreadDuration > maxThreadDuration)
                     maxThreadDuration = thisThreadDuration;
                  if (thisThreadDuration < minThreadDuration)
                     minThreadDuration = thisThreadDuration;
                  totalThreadDuration += thisThreadDuration;
                  totalCount += thread.diagnostic.getCount();
               }
               double average = ((totalThreadDuration / threadListSize) / 1.e9);
               Log.d("CotInjector", "diagnostic ALL: fastest_thread= " + ((double) minThreadDuration / 1.e9) + " sec"
                       + ", slowest_thread= " + (maxThreadDuration / 1.e9) + " sec"
                       + ", average_thread= " + average + " sec"
                       + ", count= " + totalCount
                       + ", approx_rate= " + ((double)totalCount / average) + " events/s");
            }
         }).start();
      }
   }

   /**
    * Stop CoT entity generation
    */
   public void stop()
   {
      cancelled = true;
   }

   public void setCount(int count)
   {
      this.count.set(count);
   }

   public void setInterval(int interval)
   {
      this.interval = interval;
   }

   public void setThreads(int threads)
   {
      this.threads = threads;
   }

   public void setBounds(double lat1, double lon1,
                         double lat2, double lon2)
   {
      this.minLat = Math.min(lat1, lat2);
      this.minLon = Math.min(lon1, lon2);
      this.maxLat = Math.max(lat1, lat2);
      this.maxLon = Math.max(lon1, lon2);

      deltaLat = maxLat - minLat;
      deltaLon = maxLon - minLon;
   }

   public int getCount()
   {
      return count.get();
   }

   /**
    * Provide a random point to place CoT marker.
    *
    * @return Random GeoPoint.
    */
   public GeoPoint getRandomPoint()
   {
      double latitude = minLat + random.nextDouble() * deltaLat;
      double longitude = minLon + random.nextDouble() * deltaLon;
      return new GeoPoint(latitude, longitude);
   }

   /**
    * Generate a random CoT entity type
    *
    * @return Random CoT entity type
    */
   public String getRandomType()
   {
      return "a-" + AFFINITY[random.nextInt(4)] + "-" + DIMENSION[random.nextInt(5)];
   }

   /**
    * Generate CoT message based of of user supplied inputs.
    *
    * @param uid UUID of CoT entity
    * @param type CoT type
    * @param loc Location of CoT entity
    *
    * @return Properfly formatted CoT message based off of function parameters
    */
   public String generateCotMessage(String uid, String type, GeoPoint loc)
   {
      String callsign = "Maverick";
      long now = System.currentTimeMillis();

      SimpleDateFormat isoDateFormat = new SimpleDateFormat(
              "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
      isoDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

      Date nowDate = new Date();
      String nowDateString = isoDateFormat.format(nowDate);

      // set the stale time 5 minutes from now
      nowDate.setTime(nowDate.getTime() + 5 * 60 * 1000);
      String staleDateString = isoDateFormat.format(nowDate);

      StringBuilder sb = new StringBuilder();
      sb.append(
              "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
              .append("<event version=\"2.0\" uid=\"")
              .append(uid)
              .append("\" type=\"")
              .append(type)
              .append("\" time=\"")
              .append(nowDateString)
              .append("\" start=\"")
              .append(nowDateString)
              .append("\" stale=\"")
              .append(staleDateString)
              .append("\" how=\"m-g\">")
              .append("<point lat=\"")
              .append(loc.getLatitude())
              .append("\" lon=\"")
              .append(loc.getLongitude())
              .append("\" hae=\"")
              .append(loc.getAltitude())
              .append("\" ce=\"9999999\" le=\"9999999\"/>")
              .append("<detail>")
              .append("<contact callsign=\"" + callsign + "\"/>")
              .append("</detail>")
              .append("</event>");
      return sb.toString();
   }

   /**
    * Send CoT message over the internal pipeline
    *
    * @param msg CoT message to be sent
    */
   private void sendCot(String msg)
   {
      internal.dispatch(CotEvent.parse(msg));
   }
}
