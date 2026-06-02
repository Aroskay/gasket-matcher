[app]
# (str) Uygulama Başlığı
title = Gasket Matcher
package.name = gasketmatcher
package.domain = org.aroskay
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
version = 1.0

# (list) Uygulama Bağımlılıkları
requirements = python3, kivy, opencv, numpy, pyjnius, android

orientation = portrait
fullscreen = 0

# (list) Android İzinleri
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Android API Ayarları (NumPy için 24 yapıldı)
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24

# (list) Desteklenen İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# =============================================================================
# 🚨 OPENCV & NUMPY UYUMLULUK DÜZELTMESİ
# =============================================================================
# C++ paylaşımlı kütüphane çakışmalarını engellemek için STL'i zorunlu kılıyoruz
android.ndk_stl = c++_shared

# (list) Gradle Bağımlılıkları
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
