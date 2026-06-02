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
requirements = python3, kivy, opencv, numpy, pyjnius, android

# (str) Ekran yönü
orientation = portrait
fullscreen = 0

# (list) Android İzinleri (Kamera ve Depolama)
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Hedef Android API Seviyesi
android.api = 33

# =============================================================================
# 🚨 NUMPY VE NDK ÇÖKME DÜZELTMELERİ (CRITICAL FIXES)
# =============================================================================
# NumPy'ın hata vermemesi için minapi değerini 24 yapıyoruz.
android.minapi = 24

# Kivy için en kararlı NDK sürümü ve NDK API seviyesi ayarları
android.ndk = 25b
android.ndk_api = 24
# =============================================================================

# (list) Desteklenen İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# (list) Gradle Bağımlılıkları
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

# (bool) Android yedekleme izni
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
