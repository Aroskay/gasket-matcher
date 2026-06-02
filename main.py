import os
import shutil
import threading
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

# Android yerel mimari entegrasyonu (Güncel ve Güvenli Bağlantı)
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from jnius import autoclass, cast
    
    # Gerekli Android Java Sınıfları
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    MediaStore = autoclass('android.provider.MediaStore')
    MediaStoreImagesMedia = autoclass('android.provider.MediaStore$Images$Media')
    Uri = autoclass('android.net.Uri')
    Environment = autoclass('android.os.Environment')
    Settings = autoclass('android.provider.Settings')
    File = autoclass('java.io.File')
    StrictMode = autoclass('android.os.StrictMode')

Window.clearcolor = (0.1, 0.1, 0.1, 1)

class GasketMatcherMobile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
        # --- VERİTABANI HAZIRLIĞI ---
        self.db_folder = os.path.join(App.get_running_app().user_data_dir, "GasketDB")
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        self.query_image_path = None
        self.match_results = []
        self.current_result_index = 0

        # --- GÜNCEL ANDROID ETKİNLİK BAĞLANTISI (Aktivite Dinleyici Fix) ---
        if platform == 'android':
            try:
                # FileUriExposedException hatasını kökten çözen katı politika esnetmesi
                VmPolicy = autoclass('android.os.StrictMode$VmPolicy$Builder')
                StrictMode.setVmPolicy(VmPolicy().build())
            except Exception as e:
                print(f"StrictMode Hatası: {e}")
            
            # Eski .bind yerine modern jnius ActivityResultListener entegrasyonu
            try:
                from android.activity import bind as android_bind
                android_bind(on_activity_result=self.modern_activity_result)
            except Exception:
                # Eğer üstteki de başarısız olursa PythonActivity üzerinden manuel callback yönetimi
                try:
                    PythonActivity.mActivity.registerActivityResultListener(self)
                except Exception as e:
                    print(f"Aktivite dinleyici kaydedilemedi: {e}")
                    
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
            text=f"Sistem Hazır. Veritabanında {len(os.listdir(self.db_folder))} conta var.",
            size_hint=(1, 0.15),
            halign="center",
            valign="middle",
            color=(0.2, 0.8, 0.5, 1)
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        self.add_widget(self.lbl_status)

        btn_grid = GridLayout(cols=2, size_hint=(1, 0.25), spacing=10)
        
        btn_camera = Button(text="📷 Kameradan Tara", background_color=(0.17, 0.78, 0.52, 1))
        btn_camera.bind(on_press=self.open_camera_native)
        btn_grid.add_widget(btn_camera)
        
        btn_gallery = Button(text="🖼️ Galeriden Seç", background_color=(0.12, 0.41, 0.64, 1))
        btn_gallery.bind(on_press=self.open_gallery_native)
        btn_grid.add_widget(btn_gallery)
        
        btn_bulk_import = Button(text="📂 Klasörden DB'ye Aktar", background_color=(0.7, 0.4, 0.1, 1))
        btn_bulk_import.bind(on_press=self.bulk_import_native)
        btn_grid.add_widget(btn_bulk_import)
        
        btn_db_manage = Button(text="🗑️ Veritabanını Temizle", background_color=(0.8, 0.2, 0.2, 1))
        btn_db_manage.bind(on_press=self.show_clear_db_popup)
        btn_grid.add_widget(btn_db_manage)
        
        self.add_widget(btn_grid)

        nav_panel = BoxLayout(size_hint=(1, 0.15), spacing=10)
        btn_prev = Button(text="◀ Önceki Sonuç")
        btn_prev.bind(on_press=self.show_prev_result)
        nav_panel.add_widget(btn_prev)
        
        self.lbl_index = Label(text="Sonuç: 0 / 0", bold=True)
        nav_panel.add_widget(self.lbl_index)
        
        btn_next = Button(text="Sonraki Sonuç ▶")
        btn_next.bind(on_press=self.show_next_result)
        nav_panel.add_widget(btn_next)
        
        self.add_widget(nav_panel)

    def request_android_permissions(self, dt):
        try:
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            request_permissions(permissions)

            if not Environment.isExternalStorageManager():
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                activity = PythonActivity.mActivity
                uri = Uri.fromParts("package", activity.getPackageName(), None)
                intent.setData(uri)
                activity.startActivity(intent)
        except Exception as e:
            print(f"İzin operates hatası: {e}")

    # ==========================================
    # ANDROID MODERN INTERACTION METHODS
    # ==========================================
    def open_camera_native(self, instance):
        if platform != 'android': return
        try:
            self.query_image_path = os.path.join(App.get_running_app().user_data_dir, "temp_query.jpg")
            if os.path.exists(self.query_image_path):
                os.remove(self.query_image_path)

            activity = PythonActivity.mActivity
            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            
            image_file = File(self.query_image_path)
            # StrictMode kapatıldığı için fromFile artık hata vermez
            file_uri = Uri.fromFile(image_file)
            intent.putExtra(MediaStore.EXTRA_OUTPUT, cast('android.os.Parcelable', file_uri))
            
            activity.startActivityForResult(intent, 101)
        except Exception as e:
            self.lbl_status.text = f"Kamera başlatılamadı: {e}"

    def open_gallery_native(self, instance):
        if platform != 'android': return
        try:
            activity = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_PICK, MediaStoreImagesMedia.EXTERNAL_CONTENT_URI)
            activity.startActivityForResult(intent, 102)
        except Exception as e:
            self.lbl_status.text = f"Galeri başlatılamadı: {e}"

    def bulk_import_native(self, instance):
        if platform != 'android': return
        try:
            activity = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            activity.startActivityForResult(intent, 103)
        except Exception as e:
            self.lbl_status.text = f"Klasör seçici açılamadı: {e}"

    # Yeni p4a motoru için evrensel activity result yakalayıcısı
    def modern_activity_result(self, request_code, result_code, intent):
        # Java'dan gelen ham çağrıları Python mimarisine yönlendirir
        Clock.schedule_once(lambda dt: self.direct_process_result(request_code, result_code, intent), 0)

    def direct_process_result(self, request_code, result_code, intent):
        if request_code == 101:
            if os.path.exists(self.query_image_path) and os.path.getsize(self.query_image_path) > 0:
                self.process_new_query(self.query_image_path)
            else:
                self.lbl_status.text = "Fotoğraf çekimi iptal edildi."

        elif request_code == 102 and intent is not None:
            try:
                uri = intent.getData()
                selected_path = self.get_path_from_uri(uri)
                if selected_path and os.path.exists(selected_path):
                    self.process_new_query(selected_path)
            except Exception as e:
                self.lbl_status.text = f"Resim yüklenemedi: {e}"

        elif request_code == 103 and intent is not None:
            try:
                uri = intent.getData()
                self.lbl_status.text = "Klasör doğrulandı. İşleniyor..."
                threading.Thread(target=self.run_bulk_import_saf, args=(uri,), daemon=True).start()
            except Exception as e:
                self.lbl_status.text = f"Klasör okuma hatası: {e}"

    def get_path_from_uri(self, uri):
        try:
            activity = PythonActivity.mActivity
            DocumentsContract = autoclass('android.provider.DocumentsContract')
            
            if DocumentsContract.isDocumentUri(activity, uri):
                docId = DocumentsContract.getDocumentId(uri)
                if ":" in docId:
                    type_str, id_str = docId.split(":", 1)
                    if "primary" == type_str.lower():
                        return os.path.join(Environment.getExternalStorageDirectory().getPath(), id_str)
            
            context = activity.getApplicationContext()
            cursor = context.getContentResolver().query(uri, None, None, None, None)
            if cursor is not None:
                if cursor.moveToFirst():
                    idx = cursor.getColumnIndexOrThrow(MediaStoreImagesMedia.InterfaceConsts.DATA)
                    path = cursor.getString(idx)
                    cursor.close()
                    return path
        except Exception as e:
            print(f"URI Dönüştürme Hatası: {e}")
        return None

    def process_new_query(self, path):
        self.query_image_path = path
        self.img_query.source = path
        self.img_query.reload()
        self.start_matching_thread()

    def run_bulk_import_saf(self, tree_uri):
        try:
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            content_resolver = context.getContentResolver()
            
            try:
                takeFlags = Intent.FLAG_GRANT_READ_URI_PERMISSION
                content_resolver.takePersistableUriPermission(tree_uri, takeFlags)
            except Exception as p_err:
                print(f"Kalıcı izin esneme hatası: {p_err}")

            try:
                DocumentFile = autoclass('androidx.documentfile.provider.DocumentFile')
            except Exception:
                self.update_status_from_thread("Hata: buildozer.spec dosyasına 'androidx.documentfile' eklenmemiş!")
                return
                
            from_tree = DocumentFile.fromTreeUri(context, tree_uri)
            all_files = from_tree.listFiles()
            
            valid_files = []
            for doc in all_files:
                if doc.isFile():
                    name = doc.getName()
                    if name and name.lower().endswith(('.png', '.jpg', '.jpeg')):
                        valid_files.append(doc)
            
            total_images = len(valid_files)
            if total_images == 0:
                self.update_status_from_thread("Seçilen alt klasörde geçerli resim (.jpg, .png) bulunamadı.")
                return

            copied_count = 0
            for idx, doc in enumerate(valid_files):
                file_name = doc.getName()
                file_uri = doc.getUri()
                
                input_stream = content_resolver.openInputStream(file_uri)
                dst_path = os.path.join(self.db_folder, file_name)
                
                with open(dst_path, 'wb') as output_file:
                    buffer_size = 4096
                    while True:
                        chunk = input_stream.read(buffer_size)
                        if chunk == -1 or len(chunk) == 0:
                            break
                        output_file.write(bytes(chunk))
                
                input_stream.close()
                copied_count += 1
                
                progress = (copied_count / total_images) * 100
                self.update_status_from_thread(
                    f"Redmi aktarımı: %{progress:.1f} ({copied_count} / {total_images})"
                )

            self.update_status_from_thread(
                f"Başarılı! {copied_count} adet yeni conta eklendi.\nToplam kayıt: {len(os.listdir(self.db_folder))}"
            )
        except Exception as e:
            self.update_status_from_thread(f"Aktarım esnasında hata: {e}")

    def show_clear_db_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text="Veritabanındaki TÜM contalar silinecek.\nBu işlem geri alınamaz!\nEmin misiniz?", halign='center'))
        
        btn_layout = BoxLayout(size_hint=(1, 0.4), spacing=10)
        btn_yes = Button(text="Evet, Hepsini Sil", background_color=(0.8, 0.2, 0.2, 1))
        btn_no = Button(text="İptal", background_color=(0.4, 0.4, 0.4, 1))
        
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        
        popup = Popup(title="⚠️ Veritabanını Temizleme Onayı", content=content, size_hint=(0.85, 0.4), auto_dismiss=False)
        
        btn_yes.bind(on_release=lambda x: self.confirm_clear_database(popup))
        btn_no.bind(on_release=popup.dismiss)
        popup.open()

    def confirm_clear_database(self, popup):
        popup.dismiss()
        for f in os.listdir(self.db_folder):
            os.remove(os.path.join(self.db_folder, f))
        self.lbl_status.text = "Veritabanı tamamen temizlendi! Toplam kayıt: 0"
        self.img_match.source = ''

    # ==========================================
    # GÖRÜNTÜ İŞLEME ALGORİTMALARI
    # ==========================================
    def preprocess_to_edges(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
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
        new_w, new_h = int(w_box * scale), int(h_box * scale)
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
            variations.append(cv2.flip(rotated, 1))
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
                if iou > max_iou: max_iou = iou
                if max_iou > 0.90: break
        return max_iou

    def start_matching_thread(self):
        self.lbl_status.text = "Analiz ediliyor, lütfen bekleyin..."
        self.lbl_status.color = (1, 0.8, 0.2, 1)
        threading.Thread(target=self.find_best_match, daemon=True).start()

    def update_status_from_thread(self, text):
        Clock.schedule_once(lambda dt: self.set_status(text), 0)

    def set_status(self, text):
        self.lbl_status.text = text

    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not db_files:
            self.update_status_from_thread("Hata: Veritabanında kayıtlı conta yok!")
            return

        query_mask = self.preprocess_to_edges(self.query_image_path)
        if query_mask is None:
            self.update_status_from_thread("Hata: Görselden conta sınırları algılanamadı.")
            return

        self.update_status_from_thread("Varyasyonlar üretiliyor...")
        query_variations = self.generate_query_variations(query_mask)
        
        results = []
        total_files = len(db_files)

        for idx, file_name in enumerate(db_files):
            file_path = os.path.join(self.db_folder, file_name)
            db_mask = self.preprocess_to_edges(file_path)
            
            if db_mask is not None:
                score = self.calculate_similarity_fast(query_variations, db_mask)
                results.append((file_path, score))
            
            if idx % 5 == 0 or idx == total_files - 1:
                progress = ((idx + 1) / total_files) * 100
                self.update_status_from_thread(f"Taranıyor... %{progress:.1f}")

        results.sort(key=lambda x: x[1], reverse=True)
        filtered_results = [r for r in results if r[1] > 0.12]

        Clock.schedule_once(lambda dt: self.finalize_matching(filtered_results), 0)

    def finalize_matching(self, filtered_results):
        if filtered_results:
            self.match_results = filtered_results
            self.current_result_index = 0
            self.update_result_display()
        else:
            self.match_results = []
            self.img_match.source = ''
            self.lbl_status.text = "Sistemde benzer conta bulunamadı."
            self.lbl_status.color = (1, 0.2, 0.2, 1)
            self.lbl_index.text = "Sonuç: 0 / 0"

    def update_result_display(self):
        if not self.match_results: return
        file_path, score = self.match_results[self.current_result_index]
        similarity_percentage = min(100, score * 150)
        
        self.img_match.source = file_path
        self.img_match.reload()
        
        code_name = os.path.basename(file_path)
        self.lbl_status.text = f"Eşleşme: {code_name}\nBenzerlik: %{similarity_percentage:.2f}"
        self.lbl_status.color = (0.2, 0.8, 0.5, 1) if similarity_percentage > 50 else (1, 0.8, 0.2, 1)
        self.lbl_index.text = f"Sonuç: {self.current_result_index + 1} / {len(self.match_results)}"

    def show_prev_result(self, instance):
        if self.match_results and self.current_result_index > 0:
            self.current_result_index -= 1
            self.update_result_display()

    def show_next_result(self, instance):
        if self.match_results and self.current_result_index < len(self.match_results) - 1:
            self.current_result_index += 1
            self.update_result_display()

class GasketApp(App):
    def build(self):
        self.title = 'Pro Gasket Matcher Mobile'
        return GasketMatcherMobile()

if __name__ == "__main__":
    GasketApp().run()
