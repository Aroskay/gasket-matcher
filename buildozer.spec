[app]

# (str) Title of your application
title = Gasket Matcher

# (str) Package name
package.name = gasketmatcher

# (str) Package domain (needed for android packaging)
package.domain = org.aroskay

# (str) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# OpenCV, NumPy ve Android yerel katman entegrasyonu için pyjnius zorunludur.
requirements = python3,kivy,plyer,opencv,numpy,pyjnius,android

# (str) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Android permissions
# Android 13+ (API 33) için READ_EXTERNAL_STORAGE yerine READ_MEDIA_IMAGES kullanılmalıdır.
android.permissions = CAMERA, READ_MEDIA_IMAGES

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 24

# (str) Android NDK STL to use
android.ndk_stl = c++_shared

# (list) Architectures to build for (arm64-v8a Google Play için zorunludur)
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (int) Cache build tools (0 = False, 1 = True)
ccache = 1
