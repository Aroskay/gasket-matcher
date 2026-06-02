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
# DÜZELTME: Kütüphane çakışmalarını engellemek için opencv kaldırıldı, 
# main.py içinden dinamik yüklenecek. NumPy ve pyjnius korundu.
requirements = python3, kivy, numpy, pyjnius, android

# (str) Ekran yönü (Dikey)
orientation = portrait
fullscreen = 0

# (list) Android İzinleri (Kamera ve Depolama izinleri)
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# =============================================================================
# 🚨 GİTHUB ACTIONS SUNUCU VE SÜRÜM UYUMLULUK AYARLARI
# =============================================================================
# (int) Hedef Android API Seviyesi
android.api = 33

# (int) Minimum API Seviyesi (NumPy kütüphanesi için en az 24 olmalıdır)
android.minapi = 24

# (str) Android NDK Sürümü
# DÜZELTME: 'NoneType' hatasını çözmek için GitHub sunucusunda kurulu olan
# yerleşik NDK sürüm kodunu doğrudan buraya dikte ediyoruz.
android.ndk = 27.3.13750724

# (int) NDK API Seviyesi
android.ndk_api = 24

# C++ paylaşımlı kütüphane çakışmalarını engellemek için STL yapısı zorunlu kılınıyor
android.ndk_stl = c++_shared

# (list) Desteklenen İşlemci Mimarileri
android.archs = arm64-v8a, armeabi-v7a

# =============================================================================
# 🛠️ GRADLE VE SİSTEM AYARLARI
# =============================================================================
# (list) Gradle Bağımlılıkları (main.py içindeki SAF klasör seçimi için zorunlu)
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

# (bool) Android yedekleme izni
android.allow_backup = True

[buildozer]
# (int) Log seviyesi (Hataları detaylı görmek için en yüksek seviye olan 2 yapıldı)
log_level = 2
warn_on_root = 1
