import aiohttp
import asyncio
import os
from typing import List, Set
from itertools import product
from brands_list import BRANDS
import aiofiles
from tqdm import tqdm

class AsyncBrandParser:
    def __init__(self, base_output_dir: str = "downloaded_svg"):
        self.base_output_dir = base_output_dir
        self.session = None
        self.pbar = None
        self.semaphore = asyncio.Semaphore(5)
        self.create_base_dir()
        
    def create_base_dir(self):
        """Создает структуру директорий"""
        if not os.path.exists(self.base_output_dir):
            os.makedirs(self.base_output_dir)
        for i in range(10):
            folder_path = os.path.join(self.base_output_dir, str(i))
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

    def generate_brand_variations(self, brand: str) -> List[str]:
        """Генерирует варианты написания бренда"""
        clean_brand = ''.join(c for c in brand if c.isalnum() or c.isspace())
        words = clean_brand.split()
        variations = set()
        separators = ['', '_', '-']
        cases = [str.lower, str.upper, str.title]
        
        for sep, case in product(separators, cases):
            variations.add(case(sep.join(words)))
            variations.add(case(''.join(words)))
        return list(variations)

    async def check_url(self, folder: int, brand_variation: str) -> str:
        """Проверяет существование URL"""
        async with self.semaphore:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            url = f"https://m1.dogecdn.wtf/fields/brands/{folder}/{brand_variation}.svg"
            try:
                await asyncio.sleep(0.01)
                async with self.session.head(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return url
            except Exception as e:
                print(f"Ошибка при проверке {url}: {e}")
            return ""

    async def download_svg(self, url: str):
        """Скачивает SVG файл"""
        async with self.semaphore:
            try:
                await asyncio.sleep(0.01)
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        parts = url.split('/')
                        folder_num = parts[-2]
                        filename = parts[-1]
                        folder_path = os.path.join(self.base_output_dir, folder_num)
                        filepath = os.path.join(folder_path, filename)
                        
                        content = await response.read()
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(content)
                        self.pbar.update(1)
                        print(f"Скачан файл: {filename}")
                        return True
            except Exception as e:
                print(f"Ошибка при скачивании {url}: {e}")
            return False

    async def process_brand(self, brand: str, max_folders: int = 10) -> Set[str]:
        """Обрабатывает бренд и его вариации"""
        valid_urls = set()
        variations = self.generate_brand_variations(brand)
        
        for variation in variations:
            for folder in range(max_folders):
                url = await self.check_url(folder, variation)
                if url:
                    valid_urls.add(url)
                    await self.download_svg(url)
        
        return valid_urls

    async def save_urls(self, urls: Set[str], filename: str = "found_urls.txt"):
        """Сохраняет URLs в файл"""
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            for url in sorted(urls):
                await f.write(f"{url}\n")

    async def run(self, max_folders: int = 10):
        """Запускает процесс парсинга"""
        connector = aiohttp.TCPConnector(limit=5)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            all_urls = set()
            
            self.pbar = tqdm(total=len(BRANDS), desc="Обработка брендов")
            
            chunk_size = 5
            for i in range(0, len(BRANDS), chunk_size):
                chunk = BRANDS[i:i+chunk_size]
                tasks = [self.process_brand(brand, max_folders) for brand in chunk]
                results = await asyncio.gather(*tasks)
                
                for urls in results:
                    all_urls.update(urls)
                
            await self.save_urls(all_urls)
            self.pbar.close()
            print(f"\nВсего найдено и скачано: {len(all_urls)} SVG файлов")

async def main():
    parser = AsyncBrandParser()
    await parser.run()

if __name__ == "__main__":
    # Установка лимита на количество открытых файлов для Unix систем
    import platform
    if platform.system() != 'Windows':
        import resource
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
    
    # Запуск асинхронного парсера
    asyncio.run(main()) 