[app]

title = Gasket Matcher Pro

package.name = gasketmatcher
package.domain = org.test

source.dir = .

source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 1.0

requirements = python3==3.11.9,kivy==2.3.0,numpy,opencv,pillow

orientation = portrait

fullscreen = 0

android.permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.api = 34
android.minapi = 24

android.accept_sdk_license = True

android.private_storage = True

android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

android.enable_androidx = True

android.archs = arm64-v8a

android.logcat_filters = *:S python:D

p4a.bootstrap = sdl2

android.ndk = 25b

[buildozer]

log_level = 2

warn_on_root = 1