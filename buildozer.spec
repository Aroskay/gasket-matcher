[app]
# (str) Uygulama Başlığı
title = Gasket Matcher

# (str) Paket adı ve domain bilgisi
package.name = gasketmatcher
package.domain = org.aroskay

# (str) Kaynak kodların olduğu dizin
source.dir = .

# (list) Pakete dahil edilecek uzantılar
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (str) Uygulama versiyonu
version = 1.0

# (list) Uygulama Bağımlılıkları
# DÜZELTME: "opencv-python" silindi, Buildozer uyumlu "opencv" eklendi.
requirements = python3, kivy, opencv, numpy, pyjnius, android

# (str) Ekran yönü
orientation = portrait
fullscreen = 0

# (list) Android İzinleri (Kamera ve Depolama)
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Hedef Android API Seviyeleri
android.api = 33
android.minapi = 21

# =============================================================================
# 🚨 NDK ÇÖKME DÜZELTMESİ (CRITICAL FIX)
# GitHub Actions'ın indirdiği uyumsuz r28c yerine kararlı 25b sürümünü dayatıyoruz.
# =============================================================================
android.ndk = 25b
android.ndk_api = 21

# (list) Desteklenen İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# (list) Gradle Bağımlılıkları
# DÜZELTME: main.py içindeki SAF klasör seçme kodunun çalışması için eklendi.
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

# (bool) Android yedekleme izni
android.allow_backup = True

[buildozer]
# Log seviyesi (Hataları detaylı görmek için)
log_level = 2
warn_on_root = 1
