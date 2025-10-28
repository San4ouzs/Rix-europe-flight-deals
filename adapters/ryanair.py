# Заглушка. При желании подключите публичные/партнёрские эндпоинты Ryanair
# и сконвертируйте их ответы в Offer из util_types.
# Затем импортируйте и добавьте в список провайдеров в main.py.

class RyanairAdapter:
    def __init__(self, *args, **kwargs):
        pass

    def search_offers(self, *args, **kwargs):
        return []