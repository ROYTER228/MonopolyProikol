from typing import List

def generate_variations(brand: str) -> List[str]:
    """Вспомогательная функция для генерации вариаций написания бренда"""
    variations = set()
    
    # Базовая очистка
    clean_brand = ''.join(c for c in brand if c.isalnum() or c.isspace() or c in '-_')
    words = clean_brand.split()
    
    # Добавляем вариации
    variations.add(clean_brand.lower())
    variations.add(clean_brand.upper())
    variations.add(clean_brand.title())
    variations.add(''.join(words).lower())
    variations.add(''.join(words).upper())
    variations.add(''.join(words).title())
    variations.add('_'.join(words).lower())
    variations.add('_'.join(words).upper())
    variations.add('-'.join(words).lower())
    variations.add('-'.join(words).upper())
    
    return list(variations) 