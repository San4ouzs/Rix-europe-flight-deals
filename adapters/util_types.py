from dataclasses import dataclass
from typing import Optional

@dataclass
class Offer:
    origin: str
    destination: str
    destination_city: Optional[str]
    country_code: Optional[str]
    date: str
    price: float
    currency: str
    provider: str