#include "com_atakmap_android_hellojni_plugin_HelloJNITool.h"

JNIEXPORT jstring JNICALL Java_com_atakmap_android_hellojni_plugin_HelloJNITool_myNativeMethod
  (JNIEnv *env, jclass clazz)
{
    return env->NewStringUTF("Hello JNI!");
}
