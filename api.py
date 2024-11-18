import aiohttp
import asyncio
import re
from urllib.parse import urlparse
from datetime import datetime
import random
import os
import aiofiles
from typing import Set
import json

class BrandParser:
    def __init__(self):
        self.all_urls: Set[str] = set()
        self.all_brands: Set[str] = set()
        self.failed_downloads: Set[str] = set()
        self.base_save_path = 'savess'
        self.ensure_base_directory()
        self.loop = None
        self.semaphore = None

    def ensure_base_directory(self):
        if not os.path.exists(self.base_save_path):
            os.makedirs(self.base_save_path)

    def extract_urls_from_json(self) -> Set[str]:
        try:
            with open('inpars.json', 'r', encoding='utf-8') as f:
                content = f.read()
            
            urls = set(re.findall(r'https://m1\.dogecdn\.wtf/fields/brands/[^"\s\']+', content))
            print(f"Найдено {len(urls)} URL'ов в inpars.json")
            
            valid_urls = {url for url in urls if url.lower().endswith(('.svg', '.png', '.jpg', '.jpeg'))}
            print(f"Из них {len(valid_urls)} URL'ов изображений")
            
            with open('linkeess.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'total_urls': len(valid_urls),
                    'urls': sorted(list(valid_urls))
                }, f, indent=2, ensure_ascii=False)
            
            return valid_urls
            
        except FileNotFoundError:
            print("Файл inpars.json не найден!")
            return set()
        except Exception as e:
            print(f"Ошибка при чтении inpars.json: {e}")
            return set()

    async def save_svg(self, url: str, content: bytes) -> bool:
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            relative_path = '/'.join(path_parts[3:-1])
            save_dir = os.path.join(self.base_save_path, relative_path)
            
            os.makedirs(save_dir, exist_ok=True)
            
            filename = path_parts[-1]
            file_path = os.path.join(save_dir, filename)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            print(f"✓ Сохранен: {relative_path}/{filename}")
            return True
        except Exception as e:
            print(f"✗ Ошибка сохранения {url}: {e}")
            return False

    async def download_svg(self, url: str) -> bool:
        async with self.semaphore:
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            success = await self.save_svg(url, content)
                            await asyncio.sleep(0.01)
                            return success
                        else:
                            print(f"✗ Ошибка загрузки {url}: статус {response.status}")
                            self.failed_downloads.add(url)
                            return False
            except Exception as e:
                print(f"✗ Ошибка при загрузке {url}: {e}")
                self.failed_downloads.add(url)
                return False

    async def process_urls(self, urls: Set[str]):
        tasks = []
        for url in urls:
            self.all_urls.add(url)
            filename = urlparse(url).path.split('/')[-1]
            if filename.endswith(('.svg', '.png', '.jpg', '.jpeg')):
                brand_name = os.path.splitext(filename)[0]
                self.all_brands.add(brand_name)
            tasks.append(self.download_svg(url))
        
        await asyncio.gather(*tasks)

    async def save_results(self):
        stats = {
            'total_urls': len(self.all_urls),
            'total_brands': len(self.all_brands),
            'failed_downloads': len(self.failed_downloads),
            'timestamp': datetime.now().isoformat(),
            'brands': sorted(list(self.all_brands)),
            'failed_urls': sorted(list(self.failed_downloads))
        }
        
        async with aiofiles.open('parsing_stats.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(stats, indent=2, ensure_ascii=False))

    async def main(self):
        try:
            # Инициализируем семафор
            self.loop = asyncio.get_event_loop()
            self.semaphore = asyncio.Semaphore(10)
            
            print("Извлекаем URL'ы из inpars.json...")
            urls = self.extract_urls_from_json()
            
            if not urls:
                print("URL'ы не найдены!")
                return
            
            print(f"Начинаем загрузку {len(urls)} файлов...")
            await self.process_urls(urls)
            
            print("\nСохраняем результаты...")
            await self.save_results()
            
            print(f"\nГотово!")
            print(f"Обработано URL'ов: {len(self.all_urls)}")
            print(f"Найдено брендов: {len(self.all_brands)}")
            print(f"Ошибок загрузки: {len(self.failed_downloads)}")
            
        except KeyboardInterrupt:
            print("\nПрерывание работы...")
            await self.save_results()
            print("Результаты сохранены")

if __name__ == "__main__":
    parser = BrandParser()
    try:
        asyncio.run(parser.main())
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем")