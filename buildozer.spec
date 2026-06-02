[app]
# (str) Uygulamanın adı
title = Gasket Matcher

# (str) Paket adı ve domain
package.name = gasketmatcher
package.domain = org.aroskay

# (str) Kaynak kod dizini
source.dir = .

# (list) Dahil edilecek dosya uzantıları (Resimleri de ekledik)
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (str) Uygulama versiyonu
version = 1.0

# (list) GEREKSİNİMLER (En Kritik Kısım)
# DÜZELTME: opencv-python yerine sadece "opencv" kullanılmalıdır. Buildozer'ın kendi OpenCV reçetesi vardır.
requirements = python3, kivy, opencv, numpy, pyjnius, android

# (str) Ekrana sığdırma ve yönlendirme
orientation = portrait
fullscreen = 0

# (list) Android İzinleri
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Hedef Android API ve Minimum API
android.api = 33
android.minapi = 21

# (list) Desteklenen CPU Mimarileri (Modern ve eski cihazlar için)
android.archs = arm64-v8a, armeabi-v7a

# (list) Gradle Bağımlılıkları
# DÜZELTME: main.py'deki klasör seçme (SAF) özelliği için DocumentFile bağımlılığı eklendi.
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1

# (bool) Yedeklemeye izin ver
android.allow_backup = True

[buildozer]
# Log seviyesi (Hataları görmek için 2 yapıldı)
log_level = 2
warn_on_root = 1
