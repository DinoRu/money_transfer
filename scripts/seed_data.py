"""
Script asynchrone pour remplir la base de données avec des données de test
- Devises: RUB, XOF, XAF, GNF, EUR, USD
- Pays: Russie, Zone CFA, Guinée, France
- Taux de change entre toutes les devises
- Partenaires de paiement
- Comptes de paiement
- Frais pour tous les corridors
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

from src.db.session import AsyncSessionLocal

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import PaymentPartnerType, FeeType
from src.services import (
    currency_service,
    country_service,
    exchange_rate_service,
    payment_partner_service,
    payment_account_service,
    fee_service
)
from src.schemas.currency import CurrencyCreate
from src.schemas.country import CountryCreate
from src.schemas.exchange_rate import ExchangeRateCreate
from src.schemas.payment_partner import PaymentPartnerCreate
from src.schemas.payment_account import PaymentAccountCreate
from src.schemas.fees import FeeCreate


async def create_currencies(db: AsyncSession) -> dict:
    """
    Crée les devises principales
    
    Returns:
        Dictionnaire {code: currency_object}
    """
    print("\n💱 Création des devises...")
    
    currencies_data = [
        {"code": "RUB", "name": "Rouble russe", "symbol": "₽"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "USD", "name": "Dollar américain", "symbol": "$"},
        {"code": "XOF", "name": "Franc CFA (BCEAO)", "symbol": "CFA"},
        {"code": "XAF", "name": "Franc CFA (BEAC)", "symbol": "FCFA"},
        {"code": "GNF", "name": "Franc guinéen", "symbol": "FG"},
    ]
    
    currencies = {}
    created_count = 0
    existed_count = 0
    
    for curr_data in currencies_data:
        try:
            existing = await currency_service.get_by_code(db, curr_data["code"])
            if existing:
                currencies[curr_data["code"]] = existing
                existed_count += 1
                continue
            
            currency = await currency_service.create(db, CurrencyCreate(
                **curr_data,
                is_active=True
            ))
            currencies[curr_data["code"]] = currency
            created_count += 1
            print(f"   ✓ {curr_data['code']} - {curr_data['name']}")
        
        except Exception as e:
            print(f"   ❌ Erreur {curr_data['code']}: {e}")
    
    await db.commit()
    print(f"   📊 Total: {created_count} créées, {existed_count} existantes")
    
    return currencies


async def create_countries(db: AsyncSession, currencies: dict) -> dict:
    """
    Crée les pays avec leurs devises
    
    Args:
        currencies: Dictionnaire des devises créées
        
    Returns:
        Dictionnaire {name: country_object}
    """
    print("\n🌍 Création des pays...")
    
    countries_data = [
        # Pays expéditeurs
        {
        "name": "Russie",
        "code": "RU",
        "currency": "RUB",
        "dial_code": "+7",
        "flag": "🇷🇺",
        "phone_number_length": 10,
        "phone_format_example": "+7 9XX XXX XX XX",
        "can_send_from": True,
        "can_send_to": False,
        },

        {
        "name": "France",
        "code": "FR",
        "currency": "EUR",
        "dial_code": "+33",
        "flag": "🇫🇷",
        "phone_number_length": 9,
        "phone_format_example": "+33 6 XX XX XX XX",
        "can_send_from": True,
        "can_send_to": False,
        },

        
        # Zone UEMOA (XOF) - Destinataires
        {
        "name": "Côte d'Ivoire",
        "code": "CI",
        "currency": "XOF",
        "dial_code": "+225",
        "flag": "🇨🇮",
        "phone_number_length": 10,
        "phone_format_example": "+225 07 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Sénégal",
        "code": "SN",
        "currency": "XOF",
        "dial_code": "+221",
        "flag": "🇸🇳",
        "phone_number_length": 9,
        "phone_format_example": "+221 77 XXX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Mali",
        "code": "ML",
        "currency": "XOF",
        "dial_code": "+223",
        "flag": "🇲🇱",
        "phone_number_length": 8,
        "phone_format_example": "+223 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Bénin",
        "code": "BJ",
        "currency": "XOF",
        "dial_code": "+229",
        "flag": "🇧🇯",
        "phone_number_length": 8,
        "phone_format_example": "+229 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Burkina Faso",
        "code": "BF",
        "currency": "XOF",
        "dial_code": "+226",
        "flag": "🇧🇫",
        "phone_number_length": 8,
        "phone_format_example": "+226 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Niger",
        "code": "NE",
        "currency": "XOF",
        "dial_code": "+227",
        "flag": "🇳🇪",
        "phone_number_length": 8,
        "phone_format_example": "+227 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Togo",
        "code": "TG",
        "currency": "XOF",
        "dial_code": "+228",
        "flag": "🇹🇬",
        "phone_number_length": 8,
        "phone_format_example": "+228 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Guinée-Bissau",
        "code": "GW",
        "currency": "XOF",
        "dial_code": "+245",
        "flag": "🇬🇼",
        "phone_number_length": 7,
        "phone_format_example": "+245 XXX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        # Zone CEMAC (XAF) - Destinataires
        {
        "name": "Cameroun",
        "code": "CM",
        "currency": "XAF",
        "dial_code": "+237",
        "flag": "🇨🇲",
        "phone_number_length": 9,
        "phone_format_example": "+237 6 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Gabon",
        "code": "GA",
        "currency": "XAF",
        "dial_code": "+241",
        "flag": "🇬🇦",
        "phone_number_length": 7,
        "phone_format_example": "+241 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Congo",
        "code": "CG",
        "currency": "XAF",
        "dial_code": "+242",
        "flag": "🇨🇬",
        "phone_number_length": 9,
        "phone_format_example": "+242 06 XXX XXXX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Tchad",
        "code": "TD",
        "currency": "XAF",
        "dial_code": "+235",
        "flag": "🇹🇩",
        "phone_number_length": 8,
        "phone_format_example": "+235 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "République Centrafricaine",
        "code": "CF",
        "currency": "XAF",
        "dial_code": "+236",
        "flag": "🇨🇫",
        "phone_number_length": 8,
        "phone_format_example": "+236 XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

        {
        "name": "Guinée Équatoriale",
        "code": "GQ",
        "currency": "XAF",
        "dial_code": "+240",
        "flag": "🇬🇶",
        "phone_number_length": 9,
        "phone_format_example": "+240 XXX XXX XXX",
        "can_send_from": False,
        "can_send_to": True,
        },

        # Guinée (GNF) - Destinataire
        {
        "name": "Guinée",
        "code": "GN",
        "currency": "GNF",
        "dial_code": "+224",
        "flag": "🇬🇳",
        "phone_number_length": 9,
        "phone_format_example": "+224 6XX XX XX XX",
        "can_send_from": False,
        "can_send_to": True,
        },

    ]
    
    countries = {}
    created_count = 0
    existed_count = 0
    
    for country_data in countries_data:
        try:
            currency_code = country_data.pop("currency")
            currency = currencies.get(currency_code)
            
            if not currency:
                print(f"   ❌ Devise {currency_code} non trouvée pour {country_data['name']}")
                continue
            
            existing = await country_service.get_by_name(db, country_data["name"])
            if existing:
                countries[country_data["name"]] = existing
                existed_count += 1
                continue
            
            country = await country_service.create(db, CountryCreate(
                currency_id=currency.id,
                **country_data
            ))
            countries[country_data["name"]] = country
            created_count += 1
            print(f"   ✓ {country_data['name']} ({country_data['code']}) - {currency_code}")
        
        except Exception as e:
            print(f"   ❌ Erreur {country_data['name']}: {e}")
    
    await db.commit()
    print(f"   📊 Total: {created_count} créés, {existed_count} existants")
    
    return countries


async def create_exchange_rates(db: AsyncSession, currencies: dict) -> list:
    """
    Crée les taux de change entre toutes les devises
    
    Taux approximatifs (décembre 2024):
    - 1 EUR = 105 RUB, 655 XOF/XAF, 11500 GNF, 1.05 USD
    - 1 RUB = 6.5 XOF/XAF, 87 GNF, 0.01 USD, 0.0095 EUR
    - 1 USD = 95 RUB, 590 XOF/XAF, 8800 GNF, 0.95 EUR
    - 1 XOF = 1 XAF, 13.4 GNF, 0.0017 USD, 0.0015 EUR, 0.154 RUB
    """
    print("\n💱 Création des taux de change...")
    
    rates_data = [
        # RUB vers autres
        {"from": "RUB", "to": "EUR", "rate": Decimal("0.0095")},
        {"from": "RUB", "to": "USD", "rate": Decimal("0.010")},
        {"from": "RUB", "to": "XOF", "rate": Decimal("6.5")},
        {"from": "RUB", "to": "XAF", "rate": Decimal("6.5")},
        {"from": "RUB", "to": "GNF", "rate": Decimal("87.0")},
        
        # EUR vers autres
        {"from": "EUR", "to": "RUB", "rate": Decimal("105.0")},
        {"from": "EUR", "to": "USD", "rate": Decimal("1.05")},
        {"from": "EUR", "to": "XOF", "rate": Decimal("655.0")},
        {"from": "EUR", "to": "XAF", "rate": Decimal("655.0")},
        {"from": "EUR", "to": "GNF", "rate": Decimal("11500.0")},
        
        # USD vers autres
        {"from": "USD", "to": "RUB", "rate": Decimal("95.0")},
        {"from": "USD", "to": "EUR", "rate": Decimal("0.95")},
        {"from": "USD", "to": "XOF", "rate": Decimal("590.0")},
        {"from": "USD", "to": "XAF", "rate": Decimal("590.0")},
        {"from": "USD", "to": "GNF", "rate": Decimal("8800.0")},
        
        # XOF vers autres
        {"from": "XOF", "to": "RUB", "rate": Decimal("0.154")},
        {"from": "XOF", "to": "EUR", "rate": Decimal("0.0015")},
        {"from": "XOF", "to": "USD", "rate": Decimal("0.0017")},
        {"from": "XOF", "to": "XAF", "rate": Decimal("1.0")},
        {"from": "XOF", "to": "GNF", "rate": Decimal("13.4")},
        
        # XAF vers autres
        {"from": "XAF", "to": "RUB", "rate": Decimal("0.154")},
        {"from": "XAF", "to": "EUR", "rate": Decimal("0.0015")},
        {"from": "XAF", "to": "USD", "rate": Decimal("0.0017")},
        {"from": "XAF", "to": "XOF", "rate": Decimal("1.0")},
        {"from": "XAF", "to": "GNF", "rate": Decimal("13.4")},
        
        # GNF vers autres
        {"from": "GNF", "to": "RUB", "rate": Decimal("0.0115")},
        {"from": "GNF", "to": "EUR", "rate": Decimal("0.000087")},
        {"from": "GNF", "to": "USD", "rate": Decimal("0.000114")},
        {"from": "GNF", "to": "XOF", "rate": Decimal("0.075")},
        {"from": "GNF", "to": "XAF", "rate": Decimal("0.075")},
    ]
    
    rates = []
    created_count = 0
    existed_count = 0
    
    for rate_data in rates_data:
        try:
            from_curr = currencies.get(rate_data["from"])
            to_curr = currencies.get(rate_data["to"])
            
            if not from_curr or not to_curr:
                continue
            
            existing = await exchange_rate_service.get_by_currencies(
                db, from_curr.id, to_curr.id
            )
            if existing:
                rates.append(existing)
                existed_count += 1
                continue
            
            rate = await exchange_rate_service.create(db, ExchangeRateCreate(
                from_currency_id=from_curr.id,
                to_currency_id=to_curr.id,
                rate=rate_data["rate"],
                is_active=True
            ))
            rates.append(rate)
            created_count += 1
            
            if created_count <= 5:  # Afficher seulement les 5 premiers
                print(f"   ✓ {rate_data['from']} → {rate_data['to']}: {rate_data['rate']}")
        
        except Exception as e:
            print(f"   ❌ Erreur {rate_data['from']} → {rate_data['to']}: {e}")
    
    await db.commit()
    print(f"   📊 Total: {created_count} créés, {existed_count} existants")
    
    return rates


async def create_payment_partners(db: AsyncSession, countries: dict) -> dict:
    """
    Crée les partenaires de paiement pour chaque pays
    """
    print("\n💳 Création des partenaires de paiement...")
    
    partners = {}
    created_count = 0
    
    # Partenaires pour pays expéditeurs (Russie, France)
    sender_countries = ["Russie", "France"]
    for country_name in sender_countries:
        country = countries.get(country_name)
        if not country:
            continue
        
        partners_data = [
            {
                "name": f"Carte Bancaire {country_name}",
                "type": PaymentPartnerType.CARD,
                "description": f"Cartes Visa/Mastercard en {country_name}",
                "can_send": True,
                "can_receive": False
            },
            {
                "name": f"Virement Bancaire {country_name}",
                "type": PaymentPartnerType.BANK_TRANSFER,
                "description": f"Virement bancaire classique en {country_name}",
                "can_send": True,
                "can_receive": False
            }
        ]
        
        for partner_data in partners_data:
            try:
                partner = await payment_partner_service.create(db, PaymentPartnerCreate(
                    country_id=country.id,
                    **partner_data,
                    is_active=True
                ))
                partners[partner_data["name"]] = partner
                created_count += 1
            except Exception as e:
                print(f"   ❌ Erreur {partner_data['name']}: {e}")
    
    # Partenaires Mobile Money pour pays africains
    african_countries = [
        "Côte d'Ivoire", "Sénégal", "Mali", "Bénin",
        "Burkina Faso", "Niger", "Togo", "Guinée-Bissau",
        "Cameroun", "Gabon", "Congo", "Guinée"
    ]
    
    for country_name in african_countries:
        country = countries.get(country_name)
        if not country:
            continue
        
        mobile_partners = [
            {
                "name": f"Orange Money {country_name}",
                "type": PaymentPartnerType.MOBILE_MONEY,
                "description": f"Service Orange Money en {country_name}",
                "can_send": False,
                "can_receive": True
            },
            {
                "name": f"MTN Mobile Money {country_name}",
                "type": PaymentPartnerType.MOBILE_MONEY,
                "description": f"Service MTN Money en {country_name}",
                "can_send": False,
                "can_receive": True
            }
        ]
        
        for partner_data in mobile_partners:
            try:
                partner = await payment_partner_service.create(db, PaymentPartnerCreate(
                    country_id=country.id,
                    **partner_data,
                    is_active=True
                ))
                partners[partner_data["name"]] = partner
                created_count += 1
            except Exception as e:
                pass  # Silent pour ne pas surcharger l'affichage
    
    await db.commit()
    print(f"   ✓ {created_count} partenaires créés")
    print(f"   📊 Russie/France: envoi | Pays africains: réception")
    
    return partners


async def create_payment_accounts(db: AsyncSession, partners: dict) -> list:
    """
    Crée 2 comptes de paiement pour chaque partenaire
    """
    print("\n🏦 Création des comptes de paiement...")
    
    accounts = []
    account_number = 10000000
    created_count = 0
    
    for partner_name, partner in partners.items():
        for i in range(1, 3):
            try:
                account = await payment_account_service.create(db, PaymentAccountCreate(
                    payment_partner_id=partner.id,
                    account_name=f"Compte {i}",
                    account_number=f"{account_number:08d}",
                    is_active=True
                ))
                accounts.append(account)
                account_number += 1
                created_count += 1
            except Exception as e:
                pass  # Silent
    
    await db.commit()
    print(f"   ✓ {created_count} comptes créés (2 par partenaire)")
    
    return accounts


async def create_fees(db: AsyncSession, countries: dict) -> list:
    """
    Crée les frais pour tous les corridors possibles
    """
    print("\n💰 Création des frais...")
    
    fees = []
    created_count = 0
    
    # Pays expéditeurs
    sender_countries = ["Russie", "France"]
    
    # Pays destinataires
    receiver_countries = [
        "Côte d'Ivoire", "Sénégal", "Mali", "Bénin",
        "Burkina Faso", "Niger", "Togo", "Guinée-Bissau",
        "Cameroun", "Gabon", "Congo", "République Centrafricaine",
        "Guinée Équatoriale", "Tchad", "Guinée"
    ]
    
    for sender_name in sender_countries:
        sender = countries.get(sender_name)
        if not sender:
            continue
        
        for receiver_name in receiver_countries:
            receiver = countries.get(receiver_name)
            if not receiver:
                continue
            
            # 3 tranches de frais par corridor
            fee_ranges = [
                # Petits montants: frais fixe
                {
                    "fee_type": FeeType.FIXED,
                    "fee_value": Decimal("150.00") if sender_name == "Russie" else Decimal("2.00"),
                    "min_amount": Decimal("0"),
                    "max_amount": Decimal("5000") if sender_name == "Russie" else Decimal("100")
                },
                # Montants moyens: pourcentage
                {
                    "fee_type": FeeType.PERCENTAGE,
                    "fee_value": Decimal("3.5"),
                    "min_amount": Decimal("5000") if sender_name == "Russie" else Decimal("100"),
                    "max_amount": Decimal("50000") if sender_name == "Russie" else Decimal("1000")
                },
                # Gros montants: pourcentage réduit
                {
                    "fee_type": FeeType.PERCENTAGE,
                    "fee_value": Decimal("2.5"),
                    "min_amount": Decimal("50000") if sender_name == "Russie" else Decimal("1000"),
                    "max_amount": None
                }
            ]
            
            for fee_data in fee_ranges:
                try:
                    fee = await fee_service.create(db, FeeCreate(
                        from_country_id=sender.id,
                        to_country_id=receiver.id,
                        **fee_data,
                        is_active=True
                    ))
                    fees.append(fee)
                    created_count += 1
                except Exception as e:
                    pass  # Silent
    
    await db.commit()
    print(f"   ✓ {created_count} structures de frais créées")
    print(f"   📊 {len(sender_countries)} pays expéditeurs × {len(receiver_countries)} destinataires × 3 tranches")
    
    return fees


async def main():
    """Fonction principale asynchrone"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "SEED DATA - BASE DE DONNÉES" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Initialiser la base de données
    print("\n🔧 Initialisation de la base de données...")
    # await init_db()
    print("✓ Base de données prête")
    
    # Créer une session asynchrone
    async with AsyncSessionLocal() as db:
        try:
            # 1. Devises
            currencies = await create_currencies(db)
            
            # 2. Pays
            countries = await create_countries(db, currencies)
            
            # 3. Taux de change
            rates = await create_exchange_rates(db, currencies)
            
            # 4. Partenaires de paiement
            partners = await create_payment_partners(db, countries)
            
            # 5. Comptes de paiement
            accounts = await create_payment_accounts(db, partners)
            
            # 6. Frais
            fees = await create_fees(db, countries)
            
            # Résumé final
            print("\n" + "=" * 80)
            print("📊 RÉSUMÉ FINAL")
            print("=" * 80)
            
            print(f"\n✅ Devises: {len(currencies)}")
            print(f"   • RUB, EUR, USD, XOF, XAF, GNF")
            
            print(f"\n✅ Pays: {len(countries)}")
            print(f"   • Russie, France (expéditeurs)")
            print(f"   • Zone UEMOA (XOF): 8 pays")
            print(f"   • Zone CEMAC (XAF): 6 pays")
            print(f"   • Guinée (GNF)")
            
            print(f"\n✅ Taux de change: {len(rates)}")
            print(f"   • Conversions entre toutes les devises")
            
            print(f"\n✅ Partenaires de paiement: {len(partners)}")
            print(f"   • Cartes et virements (expéditeurs)")
            print(f"   • Mobile Money (destinataires)")
            
            print(f"\n✅ Comptes de paiement: {len(accounts)}")
            print(f"   • 2 comptes par partenaire")
            
            print(f"\n✅ Frais: {len(fees)}")
            print(f"   • 3 tranches par corridor")
            print(f"   • 2 expéditeurs × 15 destinataires = 30 corridors")
            
            print("\n" + "=" * 80)
            print("🎉 SEED DATA TERMINÉ AVEC SUCCÈS!")
            print("=" * 80)
            
            # Exemples de requêtes
            print("\n" + "=" * 80)
            print("🧪 EXEMPLES DE REQUÊTES")
            print("=" * 80)
            
            print("\n# Lister les devises:")
            print("curl http://localhost:8000/api/v1/currencies")
            
            print("\n# Lister les pays:")
            print("curl http://localhost:8000/api/v1/countries")
            
            print("\n# Convertir 100 EUR en XOF:")
            print('curl -X POST http://localhost:8000/api/v1/exchange-rates/convert \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"from_currency_id": "eur_id", "to_currency_id": "xof_id", "amount": 100}\'')
            
            print("\n# Calculer frais Russie → Côte d'Ivoire (10000 RUB):")
            print('curl -X POST http://localhost:8000/api/v1/fees/calculate \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"from_country_id": "ru_id", "to_country_id": "ci_id", "amount": 10000}\'')
            
            print()
            
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())