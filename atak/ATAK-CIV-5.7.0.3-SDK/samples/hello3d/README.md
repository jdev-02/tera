Hello3D Plugin
_________________________________________________________________
PURPOSE AND CAPABILITIES

Demonstrates various examples leveraging the 3D capabilities of ATAK.

_________________________________________________________________
STATUS

Currently in development.

_________________________________________________________________
ATAK VERSIONS

Development

_________________________________________________________________
POINT OF CONTACTS

PAR Contact:           Chris Lawrence.  chris_lawrence@partech.com / 315-525-5895

_________________________________________________________________
USER GROUPS

SOCOM

_________________________________________________________________
EQUIPMENT REQUIRED


_________________________________________________________________
EQUIPMENT SUPPORTED

_________________________________________________________________
COMPILATION

These steps assume that you have Android SDK tools, as well as the JDK and
Ant, properly installed, configured, and in your PATH.

1. Update the project for your local environment.  This application is
tested and targeted against Android API level 15 (Android 4.0.4):
    android update project -p <directory with this file> -t android-15


      easy method on linux:

             android update project -p `pwd` -t android-15


2. Build the project and install it to the default device:
    ant debug install

_________________________________________________________________
DEVELOPER NOTES
