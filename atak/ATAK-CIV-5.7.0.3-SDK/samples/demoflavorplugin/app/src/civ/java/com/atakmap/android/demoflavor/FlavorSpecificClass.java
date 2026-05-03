package com.atakmap.android.demoflavor;


/**
 * Demonstrates a complete class that would exist in each flavor.
 */
public class FlavorSpecificClass {

   public FlavorSpecificClass() {

       DemoFlavorMapComponent.setCalculationProvider(new DemoFlavorMapComponent.CalculationProvider() {
           @Override
           public int calculate() {
               return 180;
           }
       });

   } 

   public String getString() {
       return "This is a return from the civil build of the plugin";
   }


}

