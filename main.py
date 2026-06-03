import sys
import os
import shutil
import threading
import time
import cv2
import numpy as np
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

# Android platformuna özel yerel kütüphaneler
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android import activity
    # DİKKAT: ByteArray içe aktarması (ImportError) çökme yaptığı için kaldırıldı!
    from jnius import autoclass, cast
    
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
else:
    from plyer import filechooser

Window.clearcolor = (0.1, 0.1, 0.1, 1)

class GasketMatcherMobile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
        # --- VERİTABANI HAZIRLIĞI ---
        self.db_folder = os.path.join(App.get_running_app().user_data_dir, "GasketDB")
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        self.query_image_path = None

        # --- ANDROID AKTİVİTE VE İZİN BAĞLANTILARI ---
        if platform == 'android':
            activity.bind(on_activity_result=self.handle_activity_result)
            Clock.schedule_once(self.request_android_permissions, 1)

        # --- ARAYÜZ (GUI) KURULUMU ---
        self.img_panel = BoxLayout(size_hint=(1, 0.45), spacing=10)
        box_query = BoxLayout(orientation='vertical')
        box_query.add_widget(Label(text="Aranan Conta", size_hint=(1, 0.1), bold=True))
        self.img_query = KivyImage(source='', allow_stretch=True, keep_ratio=True)
        box_query.add_widget(self.img_query)
        
        box_match = BoxLayout(orientation='vertical')
        box_match.add_widget(Label(text="Eşleşen Conta", size_hint=(1, 0.1), bold=True))
        self.img_match = KivyImage(source='', allow_stretch=True, keep_ratio=True)
        box_match.add_widget(self.img_match)
        
        self.img_panel.add_widget(box_query)
        self.img_panel.add_widget(box_match)
        self.add_widget(self.img_panel)

        self.lbl_status = Label(
            text=f"Sistem Hazır. DB'de {len(os.listdir(self.db_folder))} conta var.",
            size_hint=(1, 0.15), halign="center", valign="middle", color=(0.2, 0.8, 0.5, 1)
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        self.add_widget(self.lbl_status)

        btn_grid = GridLayout(cols=2, size_hint=(1, 0.25), spacing=10)
        btn_grid.add_widget(Button(text="📷 Kameradan Tara", background_color=(0.17, 0.78, 0.52, 1), on_press=self.open_camera_plyer))
        btn_grid.add_widget(Button(text="🖼️ Galeriden Seç", background_color=(0.12, 0.41, 0.64, 1), on_press=self.open_gallery_native))
        btn_grid.add_widget(Button(text="📂 Çoklu Görsel Seç (DB'ye)", background_color=(0.7, 0.4, 0.1, 1), on_press=self.bulk_import_native))
        btn_grid.add_widget(Button(text="🗑️ Veritabanını Temizle", background_color=(0.8, 0.2, 0.2, 1), on_press=self.show_clear_db_popup))
        self.add_widget(btn_grid)

        nav_panel = BoxLayout(size_hint=(1, 0.15), spacing=10)
        nav_panel.add_widget(Button(text="◀ Önceki", on_press=self.show_prev_result))
        self.lbl_index = Label(text="Sonuç: 0 / 0", bold=True)
        nav_panel.add_widget(self.lbl_index)
        nav_panel.add_widget(Button(text="Sonraki ▶", on_press=self.show_next_result))
        self.add_widget(nav_panel)

    def request_android_permissions(self, dt):
        try:
            # Hem eski sürümler (API < 33) hem de yeni sürümler (API 33+) için garanti izinler
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.READ_MEDIA_IMAGES]
            request_permissions(permissions)
        except Exception as e: 
            print(f"İzin hatası: {e}")

    def open_camera_plyer(self, instance):
        self.query_image_path = os.path.join(App.get_running_app().user_data_dir, "temp_query.jpg")
        try:
            from plyer import camera
            camera.take_picture(filename=self.query_image_path, on_complete=self.on_camera_complete)
        except Exception as e:
            self.lbl_status.text = f"Kamera Başlatılamadı: {e}"

    def on_camera_complete(self, filename):
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            Clock.schedule_once(lambda dt: self.process_new_query(filename), 0)

    def open_gallery_native(self, instance):
        if platform == 'android':
            try:
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("image/*")
                PythonActivity.mActivity.startActivityForResult(intent, 1002)
            except Exception as e:
                self.lbl_status.text = f"Galeri açma hatası: {e}"
        else:
            filechooser.open_file(on_selection=lambda s: self.process_new_query(s[0]) if s else None)

    def bulk_import_native(self, instance):
        if platform == 'android':
            try:
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("image/*")
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
                PythonActivity.mActivity.startActivityForResult(intent, 1003)
            except Exception as e:
                self.lbl_status.text = f"Çoklu seçim arayüzü hatası: {e}"
        else:
            filechooser.open_file(multiple=True, on_selection=self.handle_desktop_bulk_import)

    def handle_desktop_bulk_import(self, selection):
        if not selection: return
        threading.Thread(target=self.run_desktop_bulk_import, args=(selection,), daemon=True).start()

    def run_desktop_bulk_import(self, paths):
        count = 0
        for path in paths:
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                filename = os.path.basename(path)
                shutil.copyfile(path, os.path.join(self.db_folder, filename))
                count += 1
        self.update_status_from_thread(f"Başarılı! {count} kayıt eklendi. Toplam: {len(os.listdir(self.db_folder))}")

    def handle_activity_result(self, request_code, result_code, intent):
        if result_code != -1: # Android Activity.RESULT_OK
            return
        
        if request_code == 1002:
            if intent is not None:
                uri = intent.getData()
                if uri is not None:
                    self.lbl_status.text = "Görsel yükleniyor..."
                    threading.Thread(target=self.process_android_uri_query, args=(uri,), daemon=True).start()
                    
        elif request_code == 1003:
            if intent is not None:
                uris = []
                clip_data = intent.getClipData()
                if clip_data is not None:
                    for i in range(clip_data.getItemCount()):
                        uris.append(clip_data.getItemAt(i).getUri())
                else:
                    uri = intent.getData()
                    if uri is not None:
                        uris.append(uri)
                
                if uris:
                    self.lbl_status.text = f"{len(uris)} görsel aktarılıyor, lütfen bekleyin..."
                    threading.Thread(target=self.process_android_uris_bulk, args=(uris,), daemon=True).start()

    def copy_uri_to_local_file(self, uri, dest_path):
        """
        Android Saf içerik URI'sini Java byte dizileriyle çökmeden, 
        güvenli bir şekilde kopyalama yordamı.
        """
        try:
            context = PythonActivity.mActivity
            content_resolver = context.getContentResolver()
            input_stream = content_resolver.openInputStream(uri)
            
            FileOutputStream = autoclass('java.io.FileOutputStream')
            out_stream = FileOutputStream(dest_path)
            
            Build = autoclass('android.os.Build$VERSION')
            
            # API 29 (Android 10) ve sonrası yerleşik kopyalama desteği
            if Build.SDK_INT >= 29:
                FileUtils = autoclass('android.os.FileUtils')
                FileUtils.copy(input_stream, out_stream)
            else:
                # Eski API'ler için güvenli Bitmap Decode kopyalama
                BitmapFactory = autoclass('android.graphics.BitmapFactory')
                CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
                bitmap = BitmapFactory.decodeStream(input_stream)
                bitmap.compress(CompressFormat.JPEG, 100, out_stream)
                
            out_stream.flush()
            out_stream.close()
            input_stream.close()
            return True
        except Exception as e:
            print(f"Kopyalama Hatası: {e}")
            return False

    def process_android_uri_query(self, uri):
        local_path = os.path.join(App.get_running_app().user_data_dir, "temp_query.jpg")
        if self.copy_uri_to_local_file(uri, local_path):
            Clock.schedule_once(lambda dt: self.process_new_query(local_path), 0)
        else:
            self.update_status_from_thread("Hata: Görsel kopyalanamadı.")

    def process_android_uris_bulk(self, uris):
        count = 0
        for i, uri in enumerate(uris):
            filename = f"gasket_{int(time.time())}_{i}.jpg"
            dest_path = os.path.join(self.db_folder, filename)
            if self.copy_uri_to_local_file(uri, dest_path):
                count += 1
        self.update_status_from_thread(f"Başarılı! {count} görsel eklendi. Toplam: {len(os.listdir(self.db_folder))}")

    def show_clear_db_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text="Tüm contalar silinecek. Emin misiniz?"))
        btn_layout = BoxLayout(size_hint=(1, 0.4), spacing=10)
        btn_yes = Button(text="Evet, Sil")
        btn_yes.bind(on_release=lambda x: [threading.Thread(target=self.confirm_clear_database, daemon=True).start(), popup.dismiss()])
        btn_no = Button(text="İptal", on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_yes); btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup = Popup(title="Onay", content=content, size_hint=(0.85, 0.4))
        popup.open()

    def confirm_clear_database(self):
        try:
            for f in os.listdir(self.db_folder): 
                os.remove(os.path.join(self.db_folder, f))
            self.update_status_from_thread("Veritabanı temizlendi.")
        except Exception as e:
            self.update_status_from_thread(f"Silme hatası: {e}")

    def process_new_query(self, path):
        self.query_image_path = path
        self.img_query.source = path
        self.img_query.reload()
        self.lbl_status.text = "Görüntü işleniyor ve eşleştiriliyor..."
        self.start_matching_thread()

    def preprocess_to_edges(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)
        v = np.median(enhanced)
        edges = cv2.Canny(enhanced, int(max(0, (1.0 - 0.33) * v)), int(min(255, (1.0 + 0.33) * v)))
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        
        cropped = edges[y:y+h, x:x+w]
        if cropped.size == 0: return None
        return cv2.resize(cropped, (400, 400), interpolation=cv2.INTER_NEAREST)

    def generate_query_variations(self, mask):
        return [cv2.warpAffine(mask, cv2.getRotationMatrix2D((200, 200), a, 1.0), (400, 400)) for a in range(0, 360, 10)]

    def start_matching_thread(self): 
        threading.Thread(target=self.find_best_match, daemon=True).start()

    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not db_files:
            self.update_status_from_thread("Hata: Veritabanında karşılaştırılacak conta yok.")
            return

        q_mask = self.preprocess_to_edges(self.query_image_path)
        if q_mask is None:
            self.update_status_from_thread("Hata: Aranan contanın kenarları tespit edilemedi.")
            return
            
        q_vars = self.generate_query_variations(q_mask)
        best_score, best_file = 0.0, ""
        
        for f in db_files:
            db_mask = self.preprocess_to_edges(os.path.join(self.db_folder, f))
            if db_mask is not None:
                for var in q_vars:
                    intersection = np.count_nonzero(cv2.bitwise_and(var, db_mask))
                    union = np.count_nonzero(cv2.bitwise_or(var, db_mask))
                    if union == 0: continue
                    score = intersection / union
                    if score > best_score: 
                        best_score, best_file = score, f
                        
        if best_file:
            Clock.schedule_once(lambda dt: self.finalize_matching(best_file, best_score), 0)
        else:
            self.update_status_from_thread("Eşleşme bulunamadı.")

    def finalize_matching(self, filename, score):
        path = os.path.join(self.db_folder, filename)
        self.img_match.source = path
        self.img_match.reload()
        self.lbl_status.text = f"Eşleşme: {filename} (%{score*100:.1f})"

    def update_status_from_thread(self, text): 
        Clock.schedule_once(lambda dt: setattr(self.lbl_status, 'text', text), 0)
        
    def show_prev_result(self, instance): pass
    def show_next_result(self, instance): pass

class GasketApp(App):
    def build(self): 
        return GasketMatcherMobile()

if __name__ == "__main__": 
    GasketApp().run()
