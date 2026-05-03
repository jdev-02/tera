VideoCollections Plugin
_________________________________________________________________
PURPOSE AND CAPABILITIES

Implements support for the [VideoCollections CoT detail schema](https://git.tak.gov/standards/takvideo/). This functionality does not replace the `<__video>` detail functionality, allowing for either or both schemas to be utilized.

_________________________________________________________________
STATUS

In Review

_________________________________________________________________
POINT OF CONTACTS

marc_egan@partech.com  
devin_barillari@partech.com  
jasper_andrew@partech.com (development)

_________________________________________________________________
DEVELOPER NOTES

- I use `video-collections-cot.xml` to test, sending with the command:  
  ```netcat -w 1 -v -u -s <ip-of-computer> <ip-of-phone> 6969 < <path-to-xml>```
- Much of the code for dynamically managing radial menus is deprecated as of ATAK v4.9, so it will probably need to be updated whenever that system is replaced in Core.
- Areas in need of further development:
  - The dialogs for adding new feeds/collections don't expose all of the possible fields, only the required ones.
  - The VideoCollection info view could use improvement, it's a bit noisy.