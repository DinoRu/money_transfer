"""
Script pour peupler la base de données avec des données de test
Usage: python -m app.scripts.seed_data [--force]
"""
import argparse
import asyncio
import sys
from pathlib import Path
import uuid
from datetime import datetime
from decimal import Decimal

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlmodel import select
from src.db.session import Session as AsyncSessionLocal
from src.db.models import (
    Currency, Country, Rate, ExchangeRates, Fee,
    PaymentType, ReceivingType
)


# === HELPER: Générer UUID stable à partir d'une clé (pour reproductibilité) ===
def stable_uuid(key: str) -> uuid.UUID:
    """Génère un UUID déterministe à partir d'une chaîne (pour les seeds)"""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"remittance.app.seed.{key}")


async def seed_currencies():
    """Créer les devises de base"""
    print("Création des devises...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Currency))
        existing = result.scalars().all()

        if existing:
            print(f"ℹ️  {len(existing)} devises existent déjà")
            return {c.code: c for c in existing}

        currencies = [
            Currency(
                id=stable_uuid("currency.RUB"),
                code="RUB",
                name="Rouble russe",
                symbol="₽"
            ),
            Currency(
                id=stable_uuid("currency.BYN"),
                code="BYN",
                name="Rouble biélorusse",
                symbol="Br"
            ),
            Currency(
                id=stable_uuid("currency.XOF"),
                code="XOF",
                name="Franc CFA (BCEAO)",
                symbol="CFA"
            ),
            Currency(
                id=stable_uuid("currency.XAF"),
                code="XAF",
                name="Franc CFA (BEAC)",
                symbol="FCFA"
            ),
            Currency(
                id=stable_uuid("currency.GNF"),
                code="GNF",
                name="Franc guinéen",
                symbol="FG"
            ),
        ]

        for currency in currencies:
            session.add(currency)

        await session.commit()
        print(f"✅ {len(currencies)} devises créées")
        return {c.code: c for c in currencies}


async def seed_countries(currencies_dict):
    """Créer les pays de base"""
    print("Création des pays...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Country))
        existing = result.scalars().all()

        if existing:
            print(f"ℹ️  {len(existing)} pays existent déjà")
            return {c.code_iso: c for c in existing}

        countries = [
            # === Europe de l'Est ===
            Country(
                id=stable_uuid("country.RU"),
                name="Russie",
                code_iso="RU",
                currency_id=currencies_dict["RUB"].id,
                dial_code="+7",
                phone_pattern=r"^\d{10}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.BY"),
                name="Biélorussie",
                code_iso="BY",
                currency_id=currencies_dict["BYN"].id,
                dial_code="+375",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            
            # === Guinée ===
            Country(
                id=stable_uuid("country.GN"),
                name="Guinée",
                code_iso="GN",
                currency_id=currencies_dict["GNF"].id,
                dial_code="+224",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            
            # === Zone FCFA - XOF (Afrique de l'Ouest) ===
            Country(
                id=stable_uuid("country.BJ"),
                name="Bénin",
                code_iso="BJ",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+229",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.BF"),
                name="Burkina Faso",
                code_iso="BF",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+226",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.CI"),
                name="Côte d'Ivoire",
                code_iso="CI",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+225",
                phone_pattern=r"^\d{10}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.GW"),
                name="Guinée-Bissau",
                code_iso="GW",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+245",
                phone_pattern=r"^\d{7}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.ML"),
                name="Mali",
                code_iso="ML",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+223",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.NE"),
                name="Niger",
                code_iso="NE",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+227",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.SN"),
                name="Sénégal",
                code_iso="SN",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+221",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.TG"),
                name="Togo",
                code_iso="TG",
                currency_id=currencies_dict["XOF"].id,
                dial_code="+228",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            
            # === Zone FCFA - XAF (Afrique Centrale) ===
            Country(
                id=stable_uuid("country.CM"),
                name="Cameroun",
                code_iso="CM",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+237",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.CF"),
                name="République centrafricaine",
                code_iso="CF",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+236",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.TD"),
                name="Tchad",
                code_iso="TD",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+235",
                phone_pattern=r"^\d{8}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.CG"),
                name="République du Congo",
                code_iso="CG",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+242",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.GQ"),
                name="Guinée équatoriale",
                code_iso="GQ",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+240",
                phone_pattern=r"^\d{9}$",
                can_send=True
            ),
            Country(
                id=stable_uuid("country.GA"),
                name="Gabon",
                code_iso="GA",
                currency_id=currencies_dict["XAF"].id,
                dial_code="+241",
                phone_pattern=r"^\d{7}$",
                can_send=True
            ),
        ]

        for country in countries:
            session.add(country)

        await session.commit()
        print(f"✅ {len(countries)} pays créés")
        return {c.code_iso: c for c in countries}


async def seed_exchange_rates(currencies_dict):
    """Créer les taux de change entre devises"""
    print("Création des taux de change...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExchangeRates))
        existing = result.scalars().all()

        if existing:
            print(f"ℹ️  {len(existing)} taux de change existent déjà")
            return

        rates_data = [
            # RUB vers autres monnaies
            ("RUB", "XOF", Decimal("7.30")),
            ("RUB", "XAF", Decimal("7.20")),
            ("RUB", "GNF", Decimal("95.00")),
            ("RUB", "BYN", Decimal("0.033")),
            
            # BYN vers autres monnaies
            ("BYN", "RUB", Decimal("30.50")),
            ("BYN", "XOF", Decimal("220.00")),
            ("BYN", "XAF", Decimal("218.00")),
            ("BYN", "GNF", Decimal("2850.00")),
            
            # XOF vers autres monnaies
            ("XOF", "RUB", Decimal("0.137")),
            ("XOF", "BYN", Decimal("0.0045")),
            ("XOF", "XAF", Decimal("1.00")),
            ("XOF", "GNF", Decimal("13.00")),
            
            # XAF vers autres monnaies
            ("XAF", "RUB", Decimal("0.139")),
            ("XAF", "BYN", Decimal("0.0046")),
            ("XAF", "XOF", Decimal("1.00")),
            ("XAF", "GNF", Decimal("13.20")),
            
            # GNF vers autres monnaies
            ("GNF", "RUB", Decimal("0.0105")),
            ("GNF", "BYN", Decimal("0.00035")),
            ("GNF", "XOF", Decimal("0.077")),
            ("GNF", "XAF", Decimal("0.076")),
        ]

        exchange_rates = []
        for from_code, to_code, rate in rates_data:
            exchange_rate = ExchangeRates(
                id=stable_uuid(f"exchange_rate.{from_code}_to_{to_code}"),
                from_currency_id=currencies_dict[from_code].id,
                to_currency_id=currencies_dict[to_code].id,
                rate=rate
            )
            exchange_rates.append(exchange_rate)
            session.add(exchange_rate)

        await session.commit()
        print(f"✅ {len(exchange_rates)} taux de change créés")


async def seed_rates(currencies_dict):
    """Créer les taux (table Rate - si utilisée différemment)"""
    print("Création des taux (table Rate)...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Rate))
        existing = result.scalars().all()

        if existing:
            print(f"ℹ️  {len(existing)} taux existent déjà")
            return

        # Taux de référence pour chaque devise
        rates_data = [
            ("RUB", Decimal("7.30")),
            ("BYN", Decimal("220.00")),
            ("XOF", Decimal("1.00")),
            ("XAF", Decimal("1.00")),
            ("GNF", Decimal("0.077")),
        ]

        rates = []
        for currency_code, rate in rates_data:
            rate_obj = Rate(
                id=stable_uuid(f"rate.{currency_code}"),
                currency=currency_code,
                rate=rate
            )
            rates.append(rate_obj)
            session.add(rate_obj)

        await session.commit()
        print(f"✅ {len(rates)} taux créés")


async def seed_fees(countries_dict):
    """Créer les frais de transaction entre pays"""
    print("Création des frais de transaction...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Fee))
        existing = result.scalars().all()

        if existing:
            print(f"ℹ️  {len(existing)} frais existent déjà")
            return

        fees = []
        fcfa_countries = ["BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG", "CM", "CF", "TD", "CG", "GQ", "GA"]
        
        # Créer les frais pour chaque paire de pays
        for from_code, from_country in countries_dict.items():
            for to_code, to_country in countries_dict.items():
                if from_code == to_code:
                    continue
                
                # Déterminer le taux de frais
                if from_code in fcfa_countries and to_code in fcfa_countries:
                    # Transferts intra-FCFA : frais réduits
                    fee_percentage = Decimal("1.00")
                elif from_code in ["RU", "BY", "GN"]:
                    # Depuis Russie, Biélorussie ou Guinée
                    fee_percentage = Decimal("2.50")
                elif from_code in fcfa_countries and to_code not in fcfa_countries:
                    # Depuis FCFA vers non-FCFA
                    fee_percentage = Decimal("3.00")
                else:
                    # Par défaut
                    fee_percentage = Decimal("2.50")
                
                fee = Fee(
                    id=stable_uuid(f"fee.{from_code}_to_{to_code}"),
                    from_country_id=from_country.id,
                    to_country_id=to_country.id,
                    fee=fee_percentage
                )
                fees.append(fee)
                session.add(fee)

        await session.commit()
        print(f"✅ {len(fees)} frais créés")


async def seed_payment_types(countries_dict):
    print("Création des méthodes de paiement (entrée)...")

    async with AsyncSessionLocal() as session:
        if (await session.execute(select(PaymentType))).scalars().first():
            print("ℹ️  Méthodes de paiement déjà existantes")
            return

        created = []

        for country_code, methods in PAYMENT_METHODS_BY_COUNTRY.items():
            country = countries_dict.get(country_code)
            if not country:
                continue

            for method in methods:
                pt = PaymentType(
                    id=stable_uuid(f"payment.{country_code}.{method['type']}"),
                    type=method["type"],
                    owner_full_name=method["owner"],
                    phone_number=method["phone"],
                    account_number=method["account"],
                    country_id=country.id,
                )
                session.add(pt)
                created.append(pt)

        await session.commit()
        print(f"✅ {len(created)} méthodes de paiement créées")

async def seed_receiving_types(countries_dict):
    print("Création des méthodes de réception (sortie)...")

    async with AsyncSessionLocal() as session:
        if (await session.execute(select(ReceivingType))).scalars().first():
            print("ℹ️  Méthodes de réception déjà existantes")
            return

        created = []

        for country_code, methods in RECEIVING_METHODS_BY_COUNTRY.items():
            country = countries_dict.get(country_code)
            if not country:
                continue

            for method in methods:
                rt = ReceivingType(
                    id=stable_uuid(f"receiving.{country_code}.{method}"),
                    type=method,
                    country_id=country.id,
                )
                session.add(rt)
                created.append(rt)

        await session.commit()
        print(f"✅ {len(created)} méthodes de réception créées")


PAYMENT_METHODS_BY_COUNTRY = {
    # =========================
    # 🇷🇺 RUSSIE
    # =========================
    "RU": [
        {"type": "Sberbank", "owner": "ChapMoney RU", "phone": None, "account": "408178100000000001"},
        {"type": "Tinkoff",  "owner": "ChapMoney RU", "phone": None, "account": "408178100000000002"},
        {"type": "VTB",      "owner": "ChapMoney RU", "phone": None, "account": "408178100000000003"},
    ],

    # =========================
    # 🇧🇾 BIÉLORUSSIE
    # =========================
    "BY": [
        {"type": "Belarusbank", "owner": "ChapMoney BY", "phone": None, "account": "301200000000000001"},
        {"type": "MTBank",      "owner": "ChapMoney BY", "phone": None, "account": "301200000000000002"},
    ],

    # =========================
    # 🇬🇳 GUINÉE
    # =========================
    "GN": [
        {"type": "Orange Money GN", "owner": "ChapMoney GN", "phone": "+224620000001", "account": None},
        {"type": "MTN MoMo GN",     "owner": "ChapMoney GN", "phone": "+224620000002", "account": None},
    ],

    # =========================
    # 🇨🇮 CÔTE D’IVOIRE
    # =========================
    "CI": [
        {"type": "Orange Money CI", "owner": "ChapMoney CI", "phone": "+225070000001", "account": None},
        {"type": "Wave CI",         "owner": "ChapMoney CI", "phone": "+225050000002", "account": None},
        {"type": "MTN MoMo CI",     "owner": "ChapMoney CI", "phone": "+225050000003", "account": None},
    ],

    # =========================
    # 🇸🇳 SÉNÉGAL
    # =========================
    "SN": [
        {"type": "Orange Money SN", "owner": "ChapMoney SN", "phone": "+221770000001", "account": None},
        {"type": "Wave SN",         "owner": "ChapMoney SN", "phone": "+221780000002", "account": None},
    ],

    # =========================
    # 🇹🇬 TOGO
    # =========================
    "TG": [
        {"type": "T-Money TG",  "owner": "ChapMoney TG", "phone": "+22890000001", "account": None},
        {"type": "Moov Money TG","owner": "ChapMoney TG", "phone": "+22891000002", "account": None},
    ],

    # =========================
    # 🇧🇯 BÉNIN
    # =========================
    "BJ": [
        {"type": "MTN MoMo BJ",  "owner": "ChapMoney BJ", "phone": "+22951000001", "account": None},
        {"type": "Moov Money BJ","owner": "ChapMoney BJ", "phone": "+22952000002", "account": None},
    ],

    # =========================
    # 🇧🇫 BURKINA FASO
    # =========================
    "BF": [
        {"type": "Orange Money BF","owner": "ChapMoney BF", "phone": "+22670000001", "account": None},
        {"type": "Moov Money BF",  "owner": "ChapMoney BF", "phone": "+22671000002", "account": None},
    ],

    # =========================
    # 🇲🇱 MALI
    # =========================
    "ML": [
        {"type": "Orange Money ML","owner": "ChapMoney ML", "phone": "+22370000001", "account": None},
        {"type": "Moov Money ML",  "owner": "ChapMoney ML", "phone": "+22371000002", "account": None},
    ],

    # =========================
    # 🇳🇪 NIGER
    # =========================
    "NE": [
        {"type": "Orange Money NE","owner": "ChapMoney NE", "phone": "+22790000001", "account": None},
        {"type": "Moov Money NE",  "owner": "ChapMoney NE", "phone": "+22791000002", "account": None},
    ],

    # =========================
    # 🇬🇼 GUINÉE-BISSAU
    # =========================
    "GW": [
        {"type": "Orange Money GW","owner": "ChapMoney GW", "phone": "+2459000001", "account": None},
    ],

    # =========================
    # 🇨🇲 CAMEROUN
    # =========================
    "CM": [
        {"type": "MTN MoMo CM",    "owner": "ChapMoney CM", "phone": "+237650000001", "account": None},
        {"type": "Orange Money CM","owner": "ChapMoney CM", "phone": "+237690000002", "account": None},
    ],

    # =========================
    # 🇨🇫 RCA
    # =========================
    "CF": [
        {"type": "Orange Money CF","owner": "ChapMoney CF", "phone": "+23670000001", "account": None},
    ],

    # =========================
    # 🇹🇩 TCHAD
    # =========================
    "TD": [
        {"type": "Tigo Cash TD","owner": "ChapMoney TD", "phone": "+23566000001", "account": None},
    ],

    # =========================
    # 🇨🇬 CONGO
    # =========================
    "CG": [
        {"type": "MTN MoMo CG","owner": "ChapMoney CG", "phone": "+24206000001", "account": None},
    ],

    # =========================
    # 🇬🇶 GUINÉE ÉQUATORIALE
    # =========================
    "GQ": [
        {"type": "Orange Money GQ","owner": "ChapMoney GQ", "phone": "+24070000001", "account": None},
    ],

    # =========================
    # 🇬🇦 GABON
    # =========================
    "GA": [
        {"type": "Airtel Money GA","owner": "ChapMoney GA", "phone": "+24106000001", "account": None},
    ],
}

RECEIVING_METHODS_BY_COUNTRY = {
    "CI": ["Orange Money CI", "Wave CI", "MTN MoMo CI"],
    "SN": ["Orange Money SN", "Wave SN"],
    "TG": ["T-Money TG", "Moov Money TG"],
    "BJ": ["MTN MoMo BJ", "Moov Money BJ"],
    "BF": ["Orange Money BF", "Moov Money BF"],
    "ML": ["Orange Money ML", "Moov Money ML"],
    "NE": ["Orange Money NE", "Moov Money NE"],
    "GW": ["Orange Money GW"],
    "GN": ["Orange Money GN", "MTN MoMo GN"],

    "CM": ["MTN MoMo CM", "Orange Money CM"],
    "CF": ["Orange Money CF"],
    "TD": ["Tigo Cash TD"],
    "CG": ["MTN MoMo CG"],
    "GQ": ["Orange Money GQ"],
    "GA": ["Airtel Money GA"],

    "RU": ["Sberbank", "Tinkoff", "VTB"],
    "BY": ["Belarusbank", "MTBank"],
}



async def clean_database():
    """Nettoyer toutes les données"""
    print("🗑️  Nettoyage de la base de données...")
    
    async with AsyncSessionLocal() as session:
        # Supprimer dans l'ordre inverse des dépendances
        tables = [
            ReceivingType,
            PaymentType,
            Fee,
            ExchangeRates,
            Rate,
            Country,
            Currency
        ]
        
        for table in tables:
            await session.execute(table.__table__.delete())
        
        await session.commit()
    
    print("✅ Base de données nettoyée")


async def seed_all():
    """Exécuter tous les seeds avec option --force pour nettoyer"""
    parser = argparse.ArgumentParser(description="Seed la base de données")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Supprime toutes les données existantes avant de créer"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌱 DÉMARRAGE DU PEUPLEMENT DE LA BASE DE DONNÉES")
    print("=" * 60)
    print()

    try:
        # Nettoyage si demandé
        if args.force:
            await clean_database()
            print()

        # Création des données
        currencies = await seed_currencies()
        countries = await seed_countries(currencies)
        await seed_exchange_rates(currencies)
        await seed_rates(currencies)
        await seed_fees(countries)
        await seed_payment_types(countries)
        await seed_receiving_types(countries)

        print()
        print("=" * 60)
        print("✅ BASE DE DONNÉES PEUPLÉE AVEC SUCCÈS!")
        print("=" * 60)
        
        # Résumé final
        async with AsyncSessionLocal() as session:
            counts = {}
            for name, model in [
                ("Devises", Currency),
                ("Pays", Country),
                ("Taux de change", ExchangeRates),
                ("Taux", Rate),
                ("Frais", Fee),
                ("Types de paiement", PaymentType),
                ("Types de réception", ReceivingType)
            ]:
                result = await session.execute(select(model))
                counts[name] = len(result.scalars().all())
        
        print()
        print("📊 RÉSUMÉ:")
        for name, count in counts.items():
            print(f"   • {name}: {count}")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERREUR: {e}")
        print("=" * 60)
        print()
        print("💡 Astuce: Utilisez --force pour nettoyer la base avant")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(seed_all())