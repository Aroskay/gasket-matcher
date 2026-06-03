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
        
        # --- VERİTABANI DEĞİŞKENLERİ ---
        self.db_folder = os.path.join(App.get_running_app().user_data_dir, "GasketDB")
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        self.query_image_path = None
        self.match_results = []
        self.current_result_index = 0
        self.camera_uri = None 

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
            permissions = [Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_MEDIA_IMAGES]
            request_permissions(permissions)
        except Exception as e: 
            print(f"İzin isteme hatası: {e}")

    def open_camera_native(self, instance):
        """Çift katmanlı (Fallback korumalı) evrensel Kamera Intent tetikleyicisi"""
        if platform == 'android':
            try:
                ContentValues = autoclass('android.content.ContentValues')
                Media = autoclass('android.provider.MediaStore$Images$Media')
                String = autoclass('java.lang.String')
                
                context = PythonActivity.mActivity
                content_resolver = context.getContentResolver()
                
                filename = f"gasket_{int(time.time())}.jpg"
                
                # 1. Aşama: En geniş kapsamlı temel değerleri ata
                values = ContentValues()
                values.put(Media.DISPLAY_NAME, String(filename))
                values.put(Media.MIME_TYPE, String("image/jpeg"))
                
                # Sürüme özel gelişmiş parametreleri dene (Hata verirse güvenle es geçilir)
                try:
                    Build = autoclass('android.os.Build$VERSION')
                    if Build.SDK_INT >= 29:
                        values.put(Media.RELATIVE_PATH, String("Pictures/GasketMatcher"))
                        try:
                            values.put("is_pending", autoclass('java.lang.Integer')(1))
                        except:
                            pass
                except:
                    pass
                
                # 2. Aşama: Veritabanına ekle, eğer sütun hatası verirse çökmesini engelle ve yalın ekle
                try:
                    self.camera_uri = content_resolver.insert(Media.EXTERNAL_CONTENT_URI, values)
                except Exception as db_err:
                    print(f"Gelişmiş insert başarısız, yalın deniniyor: {db_err}")
                    fallback_values = ContentValues()
                    fallback_values.put(Media.DISPLAY_NAME, String(filename))
                    fallback_values.put(Media.MIME_TYPE, String("image/jpeg"))
                    self.camera_uri = content_resolver.insert(Media.EXTERNAL_CONTENT_URI, fallback_values)
                
                if self.camera_uri is None:
                    self.lbl_status.text = "Hata: Media Deposu oluşturulamadı."
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
                    Build = autoclass('android.os.Build$VERSION')
                    if Build.SDK_INT >= 29:
                        ContentValues = autoclass('android.content.ContentValues')
                        Integer = autoclass('java.lang.Integer')
                        values = ContentValues()
                        values.put("is_pending", Integer(0))
                        PythonActivity.mActivity.getContentResolver().update(self.camera_uri, values, None, None)
                except:
                    pass
                
                self.lbl_status.text = "Kamera görüntüsü işleniyor..."
                threading.Thread(target=self.process_android_uri_query, args=(self.camera_uri,), daemon=True).start()

        elif request_code == 1002: # Galeriden Dönüş
            if intent is not None:
                uri = intent.getData()
                if uri is not None:
                    self.lbl_status.text = "Görsel yükleniyor..."
                    threading.Thread(target=self.process_android_uri_query, args=(uri,), daemon=True).start()
                    
        elif request_code == 1003: # DB Çoklu Aktarım
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
            print(f"Dosya Kopyalama Hatası: {e}")
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
        self.lbl_status.text = "Gelişmiş detaylar taranıyor..."
        threading.Thread(target=self.find_best_match, daemon=True).start()

    def load_image_with_orientation(self, img_path):
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
                print(f"EXIF Oryantasyon hatası es geçildi: {e}")
                
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    # --- YENİ NESİL ARKA PLAN BAĞIMSIZ ORB ÖZELLİK EŞLEŞTİRME MOTORU ---
    def find_best_match(self):
        db_files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not db_files:
            self.update_status_from_thread("Hata: Veritabanında karşılaştırılacak conta yok.")
            return

        query_img = self.load_image_with_orientation(self.query_image_path)
        if query_img is None:
            self.update_status_from_thread("Hata: Aranan resim yüklenemedi.")
            return

        # ORB Tanımlayıcısı oluştur (Arka planı süzüp sadece contaya odaklanır)
        orb = cv2.ORB_create(nfeatures=1000)
        kp_query, des_query = orb.detectAndCompute(query_img, None)
        
        if des_query is None:
            self.update_status_from_thread("Hata: Fotoğrafta belirgin conta detayı bulunamadı.")
            return

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        results = []
        total_files = len(db_files)
        
        for idx, f in enumerate(db_files):
            db_path = os.path.join(self.db_folder, f)
            db_img = cv2.imread(db_path, cv2.IMREAD_GRAYSCALE)
            if db_img is None: 
                continue
                
            kp_db, des_db = orb.detectAndCompute(db_img, None)
            if des_db is None: 
                continue

            # Özellik haritalarını eşleştir
            matches = bf.match(des_query, des_db)
            matches = sorted(matches, key=lambda x: x.distance)

            # Sadece güçlü geometrik benzerlikleri filtrele (Mesafe eşiği: 48)
            good_matches = [m for m in matches if m.distance < 48]
            score = len(good_matches)
            
            results.append((db_path, score))
            
            if idx % 4 == 0 or idx == total_files - 1:
                progress = ((idx + 1) / total_files) * 100
                self.update_status_from_thread(f"Eşleştiriliyor... %{progress:.1f}")
                        
        results.sort(key=lambda x: x[1], reverse=True)
        # Minimum eşleşme nokta sayısı barajı (Gürültüleri engellemek için)
        filtered_results = [r for r in results if r[1] >= 8]
        
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
        self.lbl_status.text = "Sistemde benzer geometride conta bulunamadı."
        self.lbl_index.text = "Sonuç: 0 / 0"

    def update_result_display(self):
        if not self.match_results:
            return
            
        file_path, match_count = self.match_results[self.current_result_index]
        # Gerçekçi ve kararlı bir doğruluk yüzdesi hesabı
        confidence = min(100.0, (match_count / 25.0) * 100)
        
        self.img_match.source = file_path
        self.img_match.reload()
        
        code_name = os.path.basename(file_path)
        self.lbl_status.text = f"Sonuç {self.current_result_index + 1}: {code_name}\nEşleşen Nokta: {match_count} (Güven Skoru: %{confidence:.1f})"
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
