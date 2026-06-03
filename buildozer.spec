[app]
title = Gasket Matcher
package.name = gasketmatcher
package.domain = org.aroskay
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
version = 1.0
requirements = python3,kivy,plyer,opencv,numpy,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES
android.api = 33
android.minapi = 24
android.ndk_stl = c++_shared
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
ccache = 1
