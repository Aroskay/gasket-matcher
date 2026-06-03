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
    
    StrictMode = autoclass('android.os.StrictMode')
    StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().permitAll().build())
else:
    from plyer import filechooser

Window.clearcolor = (0.1, 0.1, 0.1, 1)

class GasketMatcherMobile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
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

        # --- ARAYÜZ ---
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

    def robust_imread(self, path, is_gray=False):
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
            nparr = np.frombuffer(file_bytes, np.uint8)
            flag = cv2.IMREAD_GRAYSCALE if is_gray else cv2.IMREAD_COLOR
            return cv2.imdecode(nparr, flag)
        except Exception as e:
            print(f"Resim okuma hatası bypass edildi: {e}")
            return None

    def get_uri_filename(self, uri):
        """Orijinal dosya ismini galeriden çeker"""
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
            except:
                pass
        return f"gasket_{int(time.time())}.jpg"

    def open_camera_native(self, instance):
        if platform == 'android':
            try:
                context = PythonActivity.mActivity
                ext_dir = context.getExternalFilesDir(None).getAbsolutePath()
                self.camera_file_path = os.path.join(ext_dir, "camera_query.jpg")
                
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
        self.lbl_status.text = f"Başarılı! {count} kayıt eklendi."

    def handle_activity_result(self, request_code, result_code, intent):
        if result_code != -1: 
            return
        
        if request_code == 1001: 
            if self.camera_file_path and os.path.exists(self.camera_file_path):
                self.process_new_query(self.camera_file_path)
            else:
                self.lbl_status.text = "Hata: Kamera resmi hafızaya yazamadı."

        elif request_code == 1002: 
            if intent is not None and intent.getData() is not None:
                self.lbl_status.text = "Görsel yükleniyor..."
                threading.Thread(target=self.process_android_uri_query, args=(intent.getData(),), daemon=True).start()
                    
        elif request_code == 1003: 
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
                if bytes_read == -1: break
                out_stream.write(buffer, 0, bytes_read)
            out_stream.flush(); out_stream.close(); input_stream.close()
            return True
        except Exception as e:
            return False

    def process_android_uri_query(self, uri):
        local_path = os.path.join(App.get_running_app().user_data_dir, "temp_query.jpg")
        if self.copy_uri_to_local_file(uri, local_path):
            Clock.schedule_once(lambda dt: self.process_new_query(local_path), 0)
        else:
            self.update_status_from_thread("Hata: Görsel kopyalanamadı.")

    def process_android_uris_bulk(self, uris_with_names):
        try:
            total = len(uris_with_names)
            count = 0
            temp_path = os.path.join(App.get_running_app().user_data_dir, "temp_import.jpg")
            
            last_prog = -1
            for idx, (uri, orig_name) in enumerate(uris_with_names):
                if self.copy_uri_to_local_file(uri, temp_path):
                    # PC'de fotolar olduğu gibi kalıyordu ancak telefonda RAM aşımı olmaması için
                    # görsel kalitesini düşürmeden en fazla 1000px olarak DB'ye atıyoruz.
                    img = self.robust_imread(temp_path)
                    if img is not None:
                        max_dim = 1000
                        h, w = img.shape[:2]
                        if max(h, w) > max_dim:
                            scale = max_dim / max(h, w)
                            img = cv2.resize(img, (int(w * scale), int(h * scale)))
                        dest_path = os.path.join(self.db_folder, orig_name)
                        cv2.imwrite(dest_path, img)
                        count += 1
                
                progress = int(((idx + 1) / total) * 100)
                if progress % 5 == 0 and progress != last_prog:
                    self.update_status_from_thread(f"Veritabanı oluşturuluyor: {idx+1}/{total} (%{progress})")
                    last_prog = progress
                time.sleep(0.005)
                
            if os.path.exists(temp_path): os.remove(temp_path)
            self.update_status_from_thread(f"Başarılı! {count} orijinal isimli conta yüklendi.")
        except Exception as e:
            self.update_status_from_thread(f"Aktarım hatası: {str(e)}")

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
        for f in os.listdir(self.db_folder): 
            os.remove(os.path.join(self.db_folder, f))
        self.update_status_from_thread("Veritabanı temizlendi.")

    def process_new_query(self, path):
        self.query_image_path = path
        self.lbl_status.text = "Analiz ediliyor..."
        threading.Thread(target=self.find_best_match_worker, daemon=True).start()

    def get_orientation_fixed_image(self, img_path):
        """Kameradan gelen yan veya ters dönmüş resmi düzeltir"""
        img = self.robust_imread(img_path, is_gray=True)
        if img is None: return None
        if platform == 'android':
            try:
                ExifInterface = autoclass('android.media.ExifInterface')
                exif = ExifInterface(img_path)
                orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
                if orientation == ExifInterface.ORIENTATION_ROTATE_90: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif orientation == ExifInterface.ORIENTATION_ROTATE_180: img = cv2.rotate(img, cv2.ROTATE_180)
                elif orientation == ExifInterface.ORIENTATION_ROTATE_270: img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            except: pass
        return img

    # --- PC'DEKİ MÜKEMMEL KENAR KESME VE MASKE ÇIKARTMA MOTORU ---
    def preprocess_to_edges(self, img_gray):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img_gray)

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

        # Sadece contayı kırpıp alıyoruz, masayı atıyoruz
        cropped_edges = edges_connected[y:y+h_box, x:x+w_box]

        # Her contayı 400x400 standart bir kanvasa eşitliyoruz
        target_size = 400
        scale = target_size / max(w_box, h_box)
        new_w = int(w_box * scale)
        new_h = int(h_box * scale)

        resized_edges = cv2.resize(cropped_edges, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        canvas = np.zeros((target_size, target_size), dtype=np.uint8)

        pad_top = (target_size - new_h) // 2
        pad_left = (target_size - new_w) // 2
        canvas[pad_top:pad_top+new_h, pad_left:pad_left+new_w] = resized_edges

        # PC'deki kalınlaştırma mantığı (kaymaları affetmesi için)
        kernel_thick = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        canvas_thick = cv2.dilate(canvas, kernel_thick, iterations=1)
        _, final_mask = cv2.threshold(canvas_thick, 127, 255, cv2.THRESH_BINARY)
        
        return final_mask

    # --- PC'DEKİ 144 VARYASYON ÜRETİCİSİ ---
    def generate_query_variations(self, query_mask):
        """Aranan contayı her 5 derecede bir çevirip ayna görüntülerini hesaplar"""
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

    # --- HIZLI IoU HESAPLAYICISI (BİREBİR PC MANTIĞI) ---
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
                # Eğer çok yüksek eşleşme bulduysa hızlanmak için döngüyü kır
                if max_iou > 0.90:
                    break
        return max_iou

    def find_best_match_worker(self):
        try:
            db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not db_files:
                self.update_status_from_thread("Hata: Veritabanında şablon yok.")
                return

            self.update_status_from_thread("[Adım 1/3] Aranan resim hazırlanıyor...")
            img_gray = self.get_orientation_fixed_image(self.query_image_path)
            if img_gray is None:
                self.update_status_from_thread("Hata: Resim okunamadı.")
                return

            # Arayüze donmaması için 500px küçük bir versiyon kaydedip gönderiyoruz
            display_path = os.path.join(App.get_running_app().user_data_dir, "display_query.jpg")
            max_dim = 500
            h, w = img_gray.shape[:2]
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                img_display = cv2.resize(img_gray, (int(w * scale), int(h * scale)))
            else:
                img_display = img_gray
            cv2.imwrite(display_path, img_display)
            Clock.schedule_once(lambda dt: self.update_query_ui(display_path), 0)

            # PC'deki gibi Maske Çıkarma
            query_mask = self.preprocess_to_edges(img_gray)
            if query_mask is None:
                self.update_status_from_thread("Hata: Fotoğrafta net bir conta şekli bulunamadı.")
                return

            self.update_status_from_thread("[Adım 2/3] 360 Derece Açı Varyasyonları Çıkarılıyor...")
            query_variations = self.generate_query_variations(query_mask)

            results = []
            total_files = len(db_files)
            last_progress = -1

            self.update_status_from_thread("[Adım 3/3] Veritabanı Maske Eşleştirmesi Başlıyor...")
            for idx, f in enumerate(db_files):
                progress = int(((idx + 1) / total_files) * 100)
                if progress % 5 == 0 and progress != last_progress:
                    self.update_status_from_thread(f"Eşleştiriliyor: %{progress} ({idx+1}/{total_files})")
                    last_progress = progress
                    time.sleep(0.01)

                db_path = os.path.join(self.db_folder, f)
                db_img = self.robust_imread(db_path, is_gray=True)
                if db_img is None: continue

                db_mask = self.preprocess_to_edges(db_img)
                if db_mask is None: continue

                score = self.calculate_similarity_fast(query_variations, db_mask)
                results.append((db_path, score))

            # Sonuçları en yüksek orana göre sırala
            results.sort(key=lambda x: x[1], reverse=True)
            
            # PC'deki baraj (0.12)
            filtered_results = [r for r in results if r[1] > 0.12]

            if filtered_results:
                self.match_results = filtered_results
                self.current_result_index = 0
                Clock.schedule_once(lambda dt: self.update_result_display(), 0)
            else:
                self.match_results = []
                Clock.schedule_once(lambda dt: self.set_no_match_ui(), 0)

        except Exception as e:
            self.update_status_from_thread(f"Kritik Hata: {str(e)}")

    def update_query_ui(self, display_path):
        self.img_query.source = display_path
        self.img_query.reload()

    def set_no_match_ui(self):
        self.img_match.source = ''
        self.img_match.reload()
        self.lbl_status.text = "Sistemde benzer conta bulunamadı."
        self.lbl_index.text = "Sonuç: 0 / 0"

    def update_result_display(self):
        if not self.match_results: return
        file_path, score = self.match_results[self.current_result_index]
        
        # PC'deki katsayı (x 150)
        similarity_percentage = min(100.0, score * 150)
        
        self.img_match.source = file_path
        self.img_match.reload()
        
        code_name = os.path.basename(file_path)
        self.lbl_status.text = f"Sonuç {self.current_result_index + 1}: {code_name}\nEşleşme Oranı: %{similarity_percentage:.2f}"
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
