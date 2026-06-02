[app]

# (str) Title of your application
title = Gasket Matcher Pro

# (str) Package name
package.name = gasketmatcher

# (str) Package domain (needed for android packaging)
package.domain = org.test

# (str) Application version (Hata veren eksik satır eklendi)
version = 1.0

# (str) Source code directory where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (list) Application requirements
# Python 3.11 ve OpenCV 4.9.0.80 sürümüne sabitlenerek Python 3.14 derleme hatası kökten çözüldü.
requirements = python3==3.11.9,kivy==2.3.0,numpy,opencv-python-headless==4.9.0.80

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# =============================================================================
# ANDROID AYARLARI (GÜNCEL REDMI VE MODERN ANDROID MODELLERİ İÇİN)
# =============================================================================

# (list) Permissions
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

# (int) Target Android API (Android 14 standardı)
android.api = 34

# (int) Minimum API (NumPy kütüphanesinin zorunlu kıldığı en alt sınır olan 24'e çekildi)
android.minapi = 24

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (list) Gradle dependencies (Klasör seçerken kullanılan AndroidX belge yönetim kütüphanesi)
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

# (bool) Enable AndroidX support. Required for modern dependencies.
android.enable_androidx = True

# (list) The Android architectures for which to build the APK
# Redmi Note 14 Pro tamamen 64-bit mimari kullandığı için sadece arm64-v8a derlenecek.
# Bu sayede RAM aşımı hatası engellendi ve derleme süresi yarı yarıya kısaltıldı.
android.archs = arm64-v8a

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# =============================================================================
# BUILDOZER SİSTEM AYARLARI
# =============================================================================

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1