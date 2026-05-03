package com.atakmap.android.demoflavor;


/**
 * Demonstrates a complete class that would exist in each flavor.
 */
public class FlavorSpecificClass {

   public FlavorSpecificClass() {

       DemoFlavorMapComponent.setCalculationProvider(new DemoFlavorMapComponent.CalculationProvider() {
           @Override
           public int calculate() {
               return 0;
           }
       });

   } 

   public String getString() {
       return "Gracias";
   }


}

