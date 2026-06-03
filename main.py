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
    from jnius import autoclass, cast
    
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    MediaStore = autoclass('android.provider.MediaStore')
else:
    from plyer import filechooser

Window.clearcolor = (0.1, 0.1, 0.1, 1)

class GasketMatcherMobile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
        # --- VERİTABANI VE GEZGİN DEĞİŞKENLERİ ---
        self.db_folder = os.path.join(App.get_running_app().user_data_dir, "GasketDB")
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        self.query_image_path = None
        self.match_results = []
        self.current_result_index = 0
        self.camera_uri = None 

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
        btn_grid.add_widget(Button(text="Kameradan Tara", background_color=(0.17, 0.78, 0.52, 1), on_press=self.open_camera_native))
        btn_grid.add_widget(Button(text="Galeriden Seç", background_color=(0.12, 0.41, 0.64, 1), on_press=self.open_gallery_native))
        btn_grid.add_widget(Button(text="Çoklu Görsel Seç (DB'ye)", background_color=(0.7, 0.4, 0.1, 1), on_press=self.bulk_import_native))
        btn_grid.add_widget(Button(text="Veritabanını Temizle", background_color=(0.8, 0.2, 0.2, 1), on_press=self.show_clear_db_popup))
        self.add_widget(btn_grid)

        nav_panel = BoxLayout(size_hint=(1, 0.15), spacing=10)
        nav_panel.add_widget(Button(text="Onceki", on_press=self.show_prev_result))
        self.lbl_index = Label(text="Sonuç: 0 / 0", bold=True)
        nav_panel.add_widget(self.lbl_index)
        nav_panel.add_widget(Button(text="Sonraki", on_press=self.show_next_result))
        self.add_widget(nav_panel)

    def request_android_permissions(self, dt):
        try:
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_MEDIA_IMAGES]
            request_permissions(permissions)
        except Exception as e: 
            print(f"İzin hatası: {e}")

    def open_camera_native(self, instance):
        """Android API 29+ uyumlu güvenli MediaStore Kamera Intent tetikleyicisi"""
        if platform == 'android':
            try:
                ContentValues = autoclass('android.content.ContentValues')
                Media = autoclass('android.provider.MediaStore$Images$Media')
                String = autoclass('java.lang.String')
                Integer = autoclass('java.lang.Integer')
                
                context = PythonActivity.mActivity
                content_resolver = context.getContentResolver()
                
                values = ContentValues()
                filename = f"gasket_{int(time.time())}.jpg"
                values.put(Media.DISPLAY_NAME, String(filename))
                values.put(Media.MIME_TYPE, String("image/jpeg"))
                
                # Android 10+ için klasör belirterek parcel hatasını engelliyoruz
                Build = autoclass('android.os.Build$VERSION')
                if Build.SDK_INT >= 29:
                    values.put(Media.RELATIVE_PATH, String("Pictures/GasketMatcher"))
                    values.put(Media.IS_PENDING, Integer(1)) # Yazma işlemi bitene kadar kilitle
                
                self.camera_uri = content_resolver.insert(Media.EXTERNAL_CONTENT_URI, values)
                
                if self.camera_uri is None:
                    self.lbl_status.text = "Hata: MediaStore URI oluşturulamadı."
                    return
                    
                intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                intent.putExtra(MediaStore.EXTRA_OUTPUT, self.camera_uri)
                PythonActivity.mActivity.startActivityForResult(intent, 1001)
            except Exception as e:
                self.lbl_status.text = f"Kamera Başlatılamadı: {str(e)}"
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
        if result_code != -1: 
            return
        
        if request_code == 1001: # Kameradan Dönüş
            if self.camera_uri is not None:
                try:
                    # Android 10+ yazma bittiği için dosya kilidini kaldırıyoruz
                    Build = autoclass('android.os.Build$VERSION')
                    if Build.SDK_INT >= 29:
                        ContentValues = autoclass('android.content.ContentValues')
                        Integer = autoclass('java.lang.Integer')
                        values = ContentValues()
                        values.put("is_pending", Integer(0))
                        PythonActivity.mActivity.getContentResolver().update(self.camera_uri, values, None, None)
                except Exception as e:
                    print(f"Pending kilit kaldırma hatası: {e}")
                
                self.lbl_status.text = "Kamera görüntüsü alınıyor..."
                threading.Thread(target=self.process_android_uri_query, args=(self.camera_uri,), daemon=True).start()

        elif request_code == 1002: # Galeriden Tekli Seçim
            if intent is not None:
                uri = intent.getData()
                if uri is not None:
                    self.lbl_status.text = "Görsel yükleniyor..."
                    threading.Thread(target=self.process_android_uri_query, args=(uri,), daemon=True).start()
                    
        elif request_code == 1003: # DB İçin Çoklu Seçim
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
                    self.lbl_status.text = f"{len(uris)} görsel aktarılıyor..."
                    threading.Thread(target=self.process_android_uris_bulk, args=(uris,), daemon=True).start()

    def copy_uri_to_local_file(self, uri, dest_path):
        try:
            context = PythonActivity.mActivity
            content_resolver = context.getContentResolver()
            input_stream = content_resolver.openInputStream(uri)
            
            FileOutputStream = autoclass('java.io.FileOutputStream')
            out_stream = FileOutputStream(dest_path)
            
            Build = autoclass('android.os.Build$VERSION')
            if Build.SDK_INT >= 29:
                FileUtils = autoclass('android.os.FileUtils')
                FileUtils.copy(input_stream, out_stream)
            else:
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
        self.lbl_status.text = "Varyasyonlar hesaplanıyor..."
        threading.Thread(target=self.find_best_match, daemon=True).start()

    # --- ANDROID YEREL EXIF ORYANTASYON DÜZELTİCİ MOTORU ---
    def load_image_with_orientation(self, img_path):
        """Telefonun dikey/yatay çekim bilgisini okur ve pikselleri doğru yöne döndürür"""
        img = cv2.imread(img_path)
        if img is None: 
            return None
            
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
            except Exception as e:
                print(f"EXIF Oryantasyon hatası: {e}")
                
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    def preprocess_to_edges(self, img_path):
        # cv2.imread yerine oryantasyon motorumuzu çağırıyoruz
        img = self.load_image_with_orientation(img_path)
        if img is None: return None

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)

        v = np.median(enhanced)
        sigma = 0.33
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        edges = cv2.Canny(enhanced, lower, upper)

        kernel_connect = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        edges_connected = cv2.dilate(edges, kernel_connect, iterations=1)

        contours, _ = cv2.findContours(edges_connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(largest_contour)
        if w_box < 15 or h_box < 15: return None

        cropped_edges = edges_connected[y:y+h_box, x:x+w_box]

        target_size = 400
        scale = target_size / max(w_box, h_box)
        new_w = int(w_box * scale)
        new_h = int(h_box * scale)

        resized_edges = cv2.resize(cropped_edges, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        canvas = np.zeros((target_size, target_size), dtype=np.uint8)

        pad_top = (target_size - new_h) // 2
        pad_left = (target_size - new_w) // 2
        canvas[pad_top:pad_top+new_h, pad_left:pad_left+new_w] = resized_edges

        kernel_thick = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        canvas_thick = cv2.dilate(canvas, kernel_thick, iterations=1)

        _, final_mask = cv2.threshold(canvas_thick, 127, 255, cv2.THRESH_BINARY)
        return final_mask

    def generate_query_variations(self, query_mask):
        variations = []
        h, w = query_mask.shape
        center = (w // 2, h // 2)

        for angle in range(0, 360, 5):
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(query_mask, M, (w, h), flags=cv2.INTER_NEAREST)
            variations.append(rotated)
            
            flipped = cv2.flip(rotated, 1)
            variations.append(flipped)
        return variations

    def calculate_similarity_fast(self, query_variations, db_mask):
        max_iou = 0
        db_sum = np.count_nonzero(db_mask)
        if db_sum == 0: return 0

        for q_mask in query_variations:
            intersection = cv2.bitwise_and(q_mask, db_mask)
            union = cv2.bitwise_or(q_mask, db_mask)

            i_sum = np.count_nonzero(intersection)
            u_sum = np.count_nonzero(union)

            if u_sum > 0:
                iou = i_sum / u_sum
                if iou > max_iou:
                    max_iou = iou
                if max_iou > 0.90:
                    break
        return max_iou

    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not db_files:
            self.update_status_from_thread("Hata: Veritabanında karşılaştırılacak conta yok.")
            return

        query_mask = self.preprocess_to_edges(self.query_image_path)
        if query_mask is None:
            self.update_status_from_thread("Hata: Aranan contanın kenarları tespit edilemedi.")
            return
            
        query_variations = self.generate_query_variations(query_mask)
        results = []
        total_files = len(db_files)
        
        for idx, f in enumerate(db_files):
            db_mask = self.preprocess_to_edges(os.path.join(self.db_folder, f))
            if db_mask is not None:
                score = self.calculate_similarity_fast(query_variations, db_mask)
                results.append((os.path.join(self.db_folder, f), score))
            
            if idx % 3 == 0 or idx == total_files - 1:
                progress = ((idx + 1) / total_files) * 100
                self.update_status_from_thread(f"Taranıyor... %{progress:.1f}")
                        
        results.sort(key=lambda x: x[1], reverse=True)
        filtered_results = [r for r in results if r[1] > 0.12]
        
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
        self.lbl_status.text = "Sistemde benzer conta bulunamadı."
        self.lbl_index.text = "Sonuç: 0 / 0"

    def update_result_display(self):
        if not self.match_results:
            return
            
        file_path, score = self.match_results[self.current_result_index]
        similarity_percentage = min(100, score * 150)
        
        self.img_match.source = file_path
        self.img_match.reload()
        
        code_name = os.path.basename(file_path)
        self.lbl_status.text = f"Sonuç {self.current_result_index + 1}: {code_name}\nEşleşme: %{similarity_percentage:.2f}"
        self.lbl_index.text = f"Sonuç: {self.current_result_index + 1} / {len(self.match_results)}"

    def show_prev_result(self, instance):
        if not self.match_results:
            return
        if self.current_result_index > 0:
            self.current_result_index -= 1
            self.update_result_display()

    def show_next_result(self, instance):
        if not self.match_results:
            return
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
