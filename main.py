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

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android import activity
    from jnius import autoclass
    
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    MediaStore = autoclass('android.provider.MediaStore')
    File = autoclass('java.io.File')
    
    # Kamera kilitlenmesini çözen StrictMode Protokolü
    StrictMode = autoclass('android.os.StrictMode')
    StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().permitAll().build())
else:
    from plyer import filechooser

Window.clearcolor = (0.1, 0.1, 0.1, 1)

class GasketMatcherMobile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
        # --- DEĞİŞKENLER ---
        self.db_folder = os.path.join(App.get_running_app().user_data_dir, "GasketDB")
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        self.query_image_path = None
        self.match_results = []
        self.current_result_index = 0
        self.camera_file_path = None

        if platform == 'android':
            activity.bind(on_activity_result=self.handle_activity_result)
            Clock.schedule_once(self.request_android_permissions, 1)

        # --- ARAYÜZ (GUI) TASARIMI ---
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
        btn_grid.add_widget(Button(text="Kameradan Tara", background_color=(0.17, 0.78, 0.52, 1), on_press=self.open_camera_native))
        btn_grid.add_widget(Button(text="Galeriden Seç", background_color=(0.12, 0.41, 0.64, 1), on_press=self.open_gallery_native))
        btn_grid.add_widget(Button(text="Çoklu Görsel Seç (DB'ye)", background_color=(0.7, 0.4, 0.1, 1), on_press=self.bulk_import_native))
        btn_grid.add_widget(Button(text="Veritabanını Temizle", background_color=(0.8, 0.2, 0.2, 1), on_press=self.show_clear_db_popup))
        self.add_widget(btn_grid)

        nav_panel = BoxLayout(size_hint=(1, 0.15), spacing=10)
        nav_panel.add_widget(Button(text="Önceki", on_press=self.show_prev_result))
        self.lbl_index = Label(text="Sonuç: 0 / 0", bold=True)
        nav_panel.add_widget(self.lbl_index)
        nav_panel.add_widget(Button(text="Sonraki", on_press=self.show_next_result))
        self.add_widget(nav_panel)

    def request_android_permissions(self, dt):
        try:
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            request_permissions(permissions)
        except Exception as e: 
            print(f"İzin hatası: {e}")

    def get_uri_filename(self, uri):
        if platform == 'android':
            try:
                context = PythonActivity.mActivity
                content_resolver = context.getContentResolver()
                MediaColumns = autoclass('android.provider.MediaStore$MediaColumns')
                
                cursor = content_resolver.query(uri, None, None, None, None)
                if cursor is not None and cursor.moveToFirst():
                    name_index = cursor.getColumnIndex(MediaColumns.DISPLAY_NAME)
                    filename = cursor.getString(name_index)
                    cursor.close()
                    return filename
            except Exception as e:
                print(f"Orijinal isim alınamadı: {e}")
        return f"gasket_{int(time.time())}.jpg"

    def open_camera_native(self, instance):
        """StrictMode Bypass ile çalışan kesin çözümlü kamera tetikleyicisi"""
        if platform == 'android':
            try:
                self.camera_file_path = os.path.join(App.get_running_app().user_data_dir, "camera_query.jpg")
                if os.path.exists(self.camera_file_path):
                    os.remove(self.camera_file_path)
                    
                image_file = File(self.camera_file_path)
                camera_uri = Uri.fromFile(image_file)
                
                intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                intent.putExtra(MediaStore.EXTRA_OUTPUT, camera_uri)
                PythonActivity.mActivity.startActivityForResult(intent, 1001)
            except Exception as e:
                self.lbl_status.text = f"Kamera Başlatılamadı:\n{str(e)}"
        else:
            self.lbl_status.text = "Kamera özelliği sadece Android cihazlarda aktiftir."

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
                self.lbl_status.text = f"Çoklu seçim hatası: {e}"
        else:
            filechooser.open_file(multiple=True, on_selection=self.handle_desktop_bulk_import)

    def handle_desktop_bulk_import(self, selection):
        if not selection: return
        count = 0
        for path in selection:
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                filename = os.path.basename(path)
                shutil.copyfile(path, os.path.join(self.db_folder, filename))
                count += 1
        self.lbl_status.text = f"Başarılı! {count} kayıt eklendi. Toplam: {len(os.listdir(self.db_folder))}"

    def handle_activity_result(self, request_code, result_code, intent):
        if result_code != -1: 
            return
        
        if request_code == 1001: # Kamera dönüşü
            if self.camera_file_path and os.path.exists(self.camera_file_path):
                self.lbl_status.text = "Kamera görüntüsü işleniyor..."
                Clock.schedule_once(lambda dt: self.process_new_query(self.camera_file_path), 0)
            else:
                self.lbl_status.text = "Hata: Kamera resmi hafızaya kaydedilemedi."

        elif request_code == 1002: # Tekli Galeri dönüşü
            if intent is not None and intent.getData() is not None:
                self.lbl_status.text = "Görsel yükleniyor..."
                threading.Thread(target=self.process_android_uri_query, args=(intent.getData(),), daemon=True).start()
                    
        elif request_code == 1003: # DB Çoklu aktarım dönüşü
            if intent is not None:
                uris_with_names = []
                clip_data = intent.getClipData()
                if clip_data is not None:
                    for i in range(clip_data.getItemCount()):
                        uri = clip_data.getItemAt(i).getUri()
                        uris_with_names.append((uri, self.get_uri_filename(uri)))
                else:
                    uri = intent.getData()
                    if uri is not None:
                        uris_with_names.append((uri, self.get_uri_filename(uri)))
                
                if uris_with_names:
                    threading.Thread(target=self.process_android_uris_bulk, args=(uris_with_names,), daemon=True).start()

    def copy_uri_to_local_file(self, uri, dest_path):
        try:
            context = PythonActivity.mActivity
            content_resolver = context.getContentResolver()
            input_stream = content_resolver.openInputStream(uri)
            FileOutputStream = autoclass('java.io.FileOutputStream')
            out_stream = FileOutputStream(dest_path)
            
            buffer = bytearray(4096)
            while True:
                bytes_read = input_stream.read(buffer)
                if bytes_read == -1:
                    break
                out_stream.write(buffer, 0, bytes_read)
                
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

    # --- ANLIK AKTARIM YÜZDESİ GÖSTEREN MOTOR ---
    def process_android_uris_bulk(self, uris_with_names):
        total = len(uris_with_names)
        count = 0
        for idx, (uri, orig_name) in enumerate(uris_with_names):
            dest_path = os.path.join(self.db_folder, orig_name)
            if self.copy_uri_to_local_file(uri, dest_path):
                count += 1
            
            # Anlık yüzde hesabı yapılıp ekrana basılıyor
            progress = ((idx + 1) / total) * 100
            self.update_status_from_thread(f"Dosyalar aktarılıyor: {idx+1} / {total} (%{progress:.1f})\nKayıt: {orig_name}")
            time.sleep(0.02) # Arayüzün donmaması için nefes alma süresi
            
        self.update_status_from_thread(f"Başarılı! {count} adet orijinal isimli conta eklendi.\nToplam DB: {len(os.listdir(self.db_folder))}")

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
        self.lbl_status.text = "Geometri analiz ediliyor..."
        threading.Thread(target=self.find_best_match, daemon=True).start()

    def load_image_and_optimize(self, img_path):
        """Görseli yükler, yönünü düzeltir ve donmayı engellemek için küçültür"""
        img = cv2.imread(img_path)
        if img is None: 
            return None
        
        # Android Yön Sensörü Düzeltmesi
        if platform == 'android':
            try:
                ExifInterface = autoclass('android.media.ExifInterface')
                exif = ExifInterface(img_path)
                orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
                if orientation == ExifInterface.ORIENTATION_ROTATE_90:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif orientation == ExifInterface.ORIENTATION_ROTATE_180:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif orientation == ExifInterface.ORIENTATION_ROTATE_270:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            except:
                pass
                
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # DONMAYI ENGELLEYEN KRİTİK ADIM: Çözünürlüğü optimize et (Max 600px)
        max_pixel = 600
        h, w = img_gray.shape[:2]
        if max(h, w) > max_pixel:
            scale = max_pixel / max(h, w)
            img_gray = cv2.resize(img_gray, (int(w * scale), int(h * scale)))
            
        return img_gray

    def extract_gasket_contour(self, img_gray):
        blurred = cv2.GaussianBlur(img_gray, (7, 7), 0)
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, thresh2 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        best_contour = None
        max_area = 0
        img_area = img_gray.shape[0] * img_gray.shape[1]
        
        for thresh in [thresh1, thresh2]:
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                area = cv2.contourArea(c)
                if 0.04 * img_area < area < 0.95 * img_area:
                    if area > max_area:
                        max_area = area
                        best_contour = c
                        
        if best_contour is None:
            edged = cv2.Canny(blurred, 30, 130)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                area = cv2.contourArea(c)
                if 0.04 * img_area < area < 0.95 * img_area:
                    if area > max_area:
                        max_area = area
                        best_contour = c
        return best_contour

    # --- ANLIK TARAMA YÜZDESİ GÖSTEREN MOTOR (DONMAZ) ---
    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not db_files:
            self.update_status_from_thread("Hata: Veritabanında karşılaştırılacak conta yok.")
            return

        query_img = self.load_image_and_optimize(self.query_image_path)
        if query_img is None:
            self.update_status_from_thread("Hata: Aranan resim yüklenemedi.")
            return

        c_query = self.extract_gasket_contour(query_img)
        if c_query is None:
            self.update_status_from_thread("Hata: Fotoğrafta net bir conta kalıbı bulunamadı.")
            return

        results = []
        total_files = len(db_files)
        
        for idx, f in enumerate(db_files):
            db_path = os.path.join(self.db_folder, f)
            db_img = cv2.imread(db_path, cv2.IMREAD_GRAYSCALE)
            if db_img is None: 
                continue
                
            # DB görsellerini de tarama anında optimize boyutlara çekiyoruz (Yıldırım hızı)
            max_pixel = 600
            h_d, w_d = db_img.shape[:2]
            if max(h_d, w_d) > max_pixel:
                scale_d = max_pixel / max(h_d, w_d)
                db_img = cv2.resize(db_img, (int(w_d * scale_d), int(h_d * scale_d)))
                
            _, db_thresh = cv2.threshold(db_img, 15, 255, cv2.THRESH_BINARY)
            db_contours, _ = cv2.findContours(db_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not db_contours: 
                continue
            c_db = max(db_contours, key=cv2.contourArea)

            # Şekil eşleştirme
            score = cv2.matchShapes(c_query, c_db, cv2.CONTOUR_MATCH_I1, 0)
            results.append((db_path, score))
            
            # ANLIK TARAMA YÜZDESİ GÖSTERİMİ
            progress = ((idx + 1) / total_files) * 100
            self.update_status_from_thread(f"Geometri analiz ediliyor: {idx+1} / {total_files} (%{progress:.1f})\nKarşılaştırılan: {f}")
            time.sleep(0.005) # İşlemciyi kilitlemeyip arayüzü tazelemek için kritik milisaniyelik uyku
                        
        results.sort(key=lambda x: x[1])
        filtered_results = [r for r in results if r[1] < 1.9]
        
        if filtered_results:
            self.match_results = filtered_results
            self.current_result_index = 0
            Clock.schedule_once(lambda dt: self.update_result_display(), 0)
        else:
            self.match_results = []
            Clock.schedule_once(lambda dt: self.set_no_match_ui(), 0)

    def set_no_match_ui(self):
        self.img_match.source = ''
        self.img_match.reload()
        self.lbl_status.text = "Sistemde benzer geometriye sahip conta bulunamadı."
        self.lbl_index.text = "Sonuç: 0 / 0"

    def update_result_display(self):
        if not self.match_results:
            return
            
        file_path, score = self.match_results[self.current_result_index]
        confidence = max(0.0, min(100.0, (1.0 - score) * 100))
        
        self.img_match.source = file_path
        self.img_match.reload()
        
        code_name = os.path.basename(file_path)
        self.lbl_status.text = f"Sonuç {self.current_result_index + 1}: {code_name}\nHata Puanı: {score:.3f} (Uyum: %{confidence:.1f})"
        self.lbl_index.text = f"Sonuç: {self.current_result_index + 1} / {len(self.match_results)}"

    def show_prev_result(self, instance):
        if not self.match_results: return
        if self.current_result_index > 0:
            self.current_result_index -= 1
            self.update_result_display()

    def show_next_result(self, instance):
        if not self.match_results: return
        if self.current_result_index < len(self.match_results) - 1:
            self.current_result_index += 1
            self.update_result_display()

    def update_status_from_thread(self, text): 
        Clock.schedule_once(lambda dt: setattr(self.lbl_status, 'text', text), 0)

class GasketApp(App):
    def build(self): 
        return GasketMatcherMobile()

if __name__ == "__main__": 
    GasketApp().run()
