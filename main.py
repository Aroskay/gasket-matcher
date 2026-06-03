import sys
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
from plyer import filechooser

# =============================================================================
# ANDROID YEREL MİMARİ ENTEGRASYONU
# =============================================================================
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from jnius import autoclass, cast
    
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    MediaStore = autoclass('android.provider.MediaStore')
    MediaStoreImagesMedia = autoclass('android.provider.MediaStore$Images$Media')
    Uri = autoclass('android.net.Uri')
    Environment = autoclass('android.os.Environment')
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

        # --- ANDROID AKTİVİTE BAĞLANTISI ---
        if platform == 'android':
            try:
                VmPolicy = autoclass('android.os.StrictMode$VmPolicy$Builder')
                StrictMode.setVmPolicy(VmPolicy().build())
            except Exception as e:
                print(f"StrictMode Hatası: {e}")
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
            size_hint=(1, 0.15), halign="center", valign="middle", color=(0.2, 0.8, 0.5, 1)
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
            from android.permissions import request_permissions, Permission
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            request_permissions(permissions)
        except Exception as e:
            print(f"İzin hatası: {e}")

    def open_camera_native(self, instance):
        if platform != 'android': return
        self.query_image_path = os.path.join(App.get_running_app().user_data_dir, "temp_query.jpg")
        activity = PythonActivity.mActivity
        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        file_uri = Uri.fromFile(File(self.query_image_path))
        intent.putExtra(MediaStore.EXTRA_OUTPUT, cast('android.os.Parcelable', file_uri))
        activity.startActivityForResult(intent, 101)

    def open_gallery_native(self, instance):
        filechooser.open_file(on_selection=self.on_gallery_selected)

    def on_gallery_selected(self, selection):
        if selection: self.process_new_query(selection[0])

    # --- GÜNCELLENEN BÖLÜM: androidx hatasını önlemek için ---
    def bulk_import_native(self, instance):
        filechooser.choose_dir(on_selection=self.on_folder_selected)

    def on_folder_selected(self, selection):
        if selection:
            self.lbl_status.text = "Aktarılıyor..."
            threading.Thread(target=self.run_bulk_import_plyer, args=(selection[0],), daemon=True).start()

    def run_bulk_import_plyer(self, folder_path):
        try:
            copied_count = 0
            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    src = os.path.join(folder_path, file_name)
                    dst = os.path.join(self.db_folder, file_name)
                    shutil.copyfile(src, dst)
                    copied_count += 1
            self.update_status_from_thread(f"Başarılı! {copied_count} kayıt eklendi.")
        except Exception as e:
            self.update_status_from_thread(f"Aktarım hatası: {e}")
    # ---------------------------------------------------------

    def process_new_query(self, path):
        self.query_image_path = path
        self.img_query.source = path
        self.img_query.reload()
        self.start_matching_thread()

    def update_status_from_thread(self, text):
        Clock.schedule_once(lambda dt: setattr(self.lbl_status, 'text', text), 0)

    # --- DİĞER FONKSİYONLARINIZ AYNEN DEVAM EDİYOR ---
    def show_clear_db_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text="Tüm contalar silinecek. Emin misiniz?"))
        btn_layout = BoxLayout(size_hint=(1, 0.4), spacing=10)
        btn_yes = Button(text="Evet, Sil", background_color=(0.8, 0.2, 0.2, 1))
        btn_no = Button(text="İptal")
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup = Popup(title="Onay", content=content, size_hint=(0.85, 0.4))
        btn_yes.bind(on_release=lambda x: self.confirm_clear_database(popup))
        btn_no.bind(on_release=popup.dismiss)
        popup.open()

    def confirm_clear_database(self, popup):
        popup.dismiss()
        for f in os.listdir(self.db_folder):
            os.remove(os.path.join(self.db_folder, f))
        self.lbl_status.text = "Veritabanı temizlendi."

    def preprocess_to_edges(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)
        v = np.median(enhanced)
        lower, upper = int(max(0, (1.0 - 0.33) * v)), int(min(255, (1.0 + 0.33) * v))
        edges = cv2.Canny(enhanced, lower, upper)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        cropped = edges[y:y+h, x:x+w]
        resized = cv2.resize(cropped, (400, 400), interpolation=cv2.INTER_NEAREST)
        return resized

    def generate_query_variations(self, mask):
        variations = []
        for angle in range(0, 360, 10):
            M = cv2.getRotationMatrix2D((200, 200), angle, 1.0)
            variations.append(cv2.warpAffine(mask, M, (400, 400)))
        return variations

    def calculate_similarity_fast(self, query_variations, db_mask):
        max_iou = 0
        for q in query_variations:
            iou = np.count_nonzero(cv2.bitwise_and(q, db_mask)) / np.count_nonzero(cv2.bitwise_or(q, db_mask) + 1e-6)
            max_iou = max(max_iou, iou)
        return max_iou

    def start_matching_thread(self):
        threading.Thread(target=self.find_best_match, daemon=True).start()

    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        q_mask = self.preprocess_to_edges(self.query_image_path)
        if q_mask is None: return
        vars = self.generate_query_variations(q_mask)
        best_score = 0
        best_file = ""
        for f in db_files:
            db_mask = self.preprocess_to_edges(os.path.join(self.db_folder, f))
            if db_mask is not None:
                score = self.calculate_similarity_fast(vars, db_mask)
                if score > best_score:
                    best_score, best_file = score, f
        Clock.schedule_once(lambda dt: self.finalize_matching([(os.path.join(self.db_folder, best_file), best_score)]), 0)

    def finalize_matching(self, results):
        if results:
            self.match_results = results
            self.update_result_display()

    def update_result_display(self):
        path, score = self.match_results[0]
        self.img_match.source = path
        self.img_match.reload()
        self.lbl_status.text = f"Eşleşme: {os.path.basename(path)} (%{score*100:.1f})"

    def show_prev_result(self, instance): pass
    def show_next_result(self, instance): pass

class GasketApp(App):
    def build(self):
        return GasketMatcherMobile()

if __name__ == "__main__":
    GasketApp().run()
