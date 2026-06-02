[app]
title = Gasket Matcher
package.name = gasketmatcher
package.domain = org.aroskay
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
version = 1.0

# Bağımlılıklar (OpenCV dışarıda kalmaya devam ediyor, en güvenlisi bu)
requirements = python3, kivy, numpy, pyjnius, android

orientation = portrait
fullscreen = 0

android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# =============================================================================
# 🚀 MODERN GRADLE VE SUNUCU UYUMLULUK AYARLARI
# =============================================================================
android.api = 33
android.minapi = 24

# Sürümü boş bırakıyoruz ki GitHub sunucusundaki güncel NDK'yı otomatik kullansın
android.ndk = 
android.ndk_api = 24
android.ndk_stl = c++_shared

# İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# Java ve SAF klasör seçici bağımlılığı
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
