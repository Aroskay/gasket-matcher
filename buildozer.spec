[app]

# (str) Uygulama Başlığı
title = Gasket Matcher

# (str) Paket adı ve domain bilgisi
package.name = gasketmatcher
package.domain = org.aroskay

# (str) Kaynak kodların olduğu dizin (.) ana dizini temsil eder
source.dir = .

# (list) Pakete dahil edilecek uzantılar
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (str) Uygulama versiyonu
version = 1.0

# (list) Uygulama Bağımlılıkları
# DÜZELTME: opencv tekrar buraya eklendi. Artık paket içine gömülü derlenecek.
requirements = python3, kivy, opencv, numpy, pyjnius, android

# (str) Ekran yönü (Dikey)
orientation = portrait
fullscreen = 0

# (list) Android İzinleri - Yeni Android sürümleri için medya izinleri eklendi

android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES, READ_MEDIA_VIDEO

# =============================================================================
# 🚨 GİTHUB ACTIONS SUNUCU VE SÜRÜM UYUMLULUK AYARLARI
# =============================================================================
# (int) Hedef Android API Seviyesi
android.api = 33

# (int) Minimum API Seviyesi (NumPy kütüphanesi için en az 24 olmalıdır)
android.minapi = 24

# (str) Android NDK Sürümü
# Google sunucularından 404 hatası almamak için resmi kararlı sürüm yazıldı.
android.ndk = 27.3.13750724

# (int) NDK API Seviyesi
android.ndk_api = 33

# C++ paylaşımlı kütüphane çakışmalarını engellemek için STL yapısı zorunlu kılınıyor
android.ndk_stl = c++_shared

# (list) Desteklenen İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# =============================================================================
# 🛠️ GRADLE VE SİSTEM AYARLARI
# =============================================================================
# (list) Android Gradle bağımlılıkları
# Hataya sebep olan 'androidx.documentfile:documentfile:1.0.1' kütüphanesini açıkça ekledik.
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1, androidx.core:core:1.6.0

# (bool) Android yedekleme izni
android.allow_backup = True

[buildozer]
# (int) Log seviyesi (Hataları detaylı görmek için en yüksek seviye olan 2 yapıldı)
log_level = 2
# (int) Ccache kullanımı (1: Aktif, 0: Pasif)
ccache = 1
warn_on_root = 1
