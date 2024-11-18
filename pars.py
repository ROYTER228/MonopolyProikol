import requests
import concurrent.futures
import os
from typing import List, Set
from itertools import product
from brands_list import BRANDS

class BrandParser:
    def __init__(self, base_output_dir: str = "downloaded_svg"):
        self.base_output_dir = base_output_dir
        self.create_base_dir()
        
    def create_base_dir(self):
        """Создает базовую директорию и поддиректории от 0 до 9"""
        if not os.path.exists(self.base_output_dir):
            os.makedirs(self.base_output_dir)
        
        # Создаем поддиректории от 0 до 9
        for i in range(10):
            folder_path = os.path.join(self.base_output_dir, str(i))
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

    def generate_brand_variations(self, brand: str) -> List[str]:
        """Генерирует различные варианты написания бренда"""
        # Убираем специальные символы
        clean_brand = ''.join(c for c in brand if c.isalnum() or c.isspace())
        words = clean_brand.split()
        
        variations = set()
        
        # Добавляем вариации с разными разделителями
        separators = ['', '_', '-']
        cases = [str.lower, str.upper, str.title]
        
        for sep, case in product(separators, cases):
            # Вариант с разделителем
            variations.add(case(sep.join(words)))
            
            # Вариант без пробелов
            variations.add(case(''.join(words)))
            
        return list(variations)

    def check_url(self, folder: int, brand_variation: str) -> str:
        """Проверяет существование URL для конкретного варианта бренда"""
        url = f"https://m1.dogecdn.wtf/fields/brands/{folder}/{brand_variation}.svg"
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                return url
        except requests.RequestException:
            pass
        return ""

    def download_svg(self, url: str):
        """Скачивает SVG файл, сохраняя структуру папок"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Извлекаем номер папки и имя файла из URL
                parts = url.split('/')
                folder_num = parts[-2]  # Номер папки (0-9)
                filename = parts[-1]    # Имя файла
                
                # Создаем путь для сохранения
                folder_path = os.path.join(self.base_output_dir, folder_num)
                filepath = os.path.join(folder_path, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"Скачан файл: {folder_num}/{filename}")
                return True
        except requests.RequestException as e:
            print(f"Ошибка при скачивании {url}: {e}")
        return False

    def process_brand(self, brand: str, max_folders: int = 10) -> Set[str]:
        """Обрабатывает один бренд и все его вариации"""
        valid_urls = set()
        variations = self.generate_brand_variations(brand)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for variation in variations:
                for folder in range(max_folders):
                    futures.append(
                        executor.submit(self.check_url, folder, variation)
                    )
            
            for future in concurrent.futures.as_completed(futures):
                url = future.result()
                if url:
                    valid_urls.add(url)
                    print(f"Найден URL: {url}")
                    # Сразу скачиваем найденный файл
                    self.download_svg(url)
        
        return valid_urls

    def run(self, max_folders: int = 10):
        """Запускает процесс парсинга для всех брендов"""
        all_urls = set()
        
        for brand in BRANDS:
            print(f"\nОбработка бренда: {brand}")
            urls = self.process_brand(brand, max_folders)
            all_urls.update(urls)
            
        # Сохраняем все найденные URLs в файл
        self.save_urls(all_urls)
        print(f"\nВсего найдено и скачано: {len(all_urls)} SVG файлов")

    def save_urls(self, urls: Set[str], filename: str = "found_urls.txt"):
        """Сохраняет найденные URLs в файл"""
        with open(filename, "w", encoding="utf-8") as f:
            for url in sorted(urls):
                f.write(f"{url}\n")

def main():
    parser = BrandParser()
    parser.run()

if __name__ == "__main__":
    main()
