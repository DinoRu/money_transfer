"""
╔══════════════════════════════════════════════════════════════════╗
║  SEED — Agents + Comptes Ledger + Soldes initiaux               ║
║  Usage: python -m app.scripts.seed_agents [--force]             ║
║                                                                  ║
║  ⚠️ Pré-requis: exécuter seed_data.py et seed_users.py AVANT    ║
║     (les devises, pays et méthodes de paiement doivent exister)  ║
╚══════════════════════════════════════════════════════════════════╝

Crée:
  👤 6 agents + 1 compte système Chapmoney
  💳 14 comptes agents (AgentAccount) liés aux méthodes de paiement existantes
  📒 Écritures TOPUP initiales dans le ledger

Agents:
  🇷🇺 Dmitry Ivanov       — Sberbank (500K RUB), Tinkoff (300K RUB)
  🇧🇾 Aliaksandr Kazlov   — Belarusbank (15K BYN)
  🇨🇮 Koné Ibrahim        — Wave CI (2M XOF), Orange Money CI (1.5M XOF)
  🇸🇳 Ousmane Diop        — Wave SN (1M XOF), Orange Money SN (800K XOF)
  🇨🇲 Jean-Pierre Mbarga  — MTN MoMo CM (1.5M XAF)
  🇬🇳 Alpha Barry         — Orange Money GN (50M GNF)
  💰 Chapmoney System     — Comptes frais (solde 0)
"""

import argparse
import asyncio
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import Session as AsyncSessionLocal
from src.db.models import (
    LedgerTx, User, UserRole, Currency, Country, PaymentType, AgentAccount, LedgerEntry, LedgerEntryType, LedgerCategory
)

from src.auth.auth import hash_password


# =============================================================================
# HELPER — UUID stable (même pattern que seed_data.py)
# =============================================================================

def stable_uuid(key: str) -> uuid.UUID:
    """Génère un UUID déterministe (namespace propre aux agents)"""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"chapmoney.seed.agents.{key}")


# =============================================================================
# DONNÉES — AGENTS
# =============================================================================

AGENTS = [
    {
        "key": "agent_ru",
        "full_name": "Dmitry Ivanov",
        "email": "agent.ru@chapmoney.dev",
        "phone": "+79001234567",
        "country": "RU",
    },
    {
        "key": "agent_by",
        "full_name": "Aliaksandr Kazlov",
        "email": "agent.by@chapmoney.dev",
        "phone": "+375291234567",
        "country": "BY",
    },
    {
        "key": "agent_ci",
        "full_name": "Koné Ibrahim",
        "email": "agent.ci@chapmoney.dev",
        "phone": "+2250701234567",
        "country": "CI",
    },
    {
        "key": "agent_sn",
        "full_name": "Ousmane Diop",
        "email": "agent.sn@chapmoney.dev",
        "phone": "+221771234567",
        "country": "SN",
    },
    {
        "key": "agent_cm",
        "full_name": "Jean-Pierre Mbarga",
        "email": "agent.cm@chapmoney.dev",
        "phone": "+237651234567",
        "country": "CM",
    },
    {
        "key": "agent_gn",
        "full_name": "Alpha Barry",
        "email": "agent.gn@chapmoney.dev",
        "phone": "+224621234567",
        "country": "GN",
    },
    {
        "key": "chapmoney_system",
        "full_name": "Chapmoney System",
        "email": "system@chapmoney.dev",
        "phone": "+0000000000",
        "country": "CI",
    },
]

# =============================================================================
# DONNÉES — COMPTES AGENTS
#
# Format: (agent_key, payment_type_name, currency_code, initial_balance, min_balance)
#
# ⚠️ payment_type_name correspond EXACTEMENT au champ `type`
#    dans PAYMENT_METHODS_BY_COUNTRY de seed_data.py
# =============================================================================

AGENT_ACCOUNTS = [
    # ── 🇷🇺 Russie ──────────────────────────────────────────────────────────
    ("agent_ru",  "Sberbank",          "RUB",  Decimal("500000"),    Decimal("-1000000")),
    ("agent_ru",  "Tinkoff",           "RUB",  Decimal("300000"),    Decimal("-500000")),

    # ── 🇧🇾 Biélorussie ─────────────────────────────────────────────────────
    ("agent_by",  "Belarusbank",       "BYN",  Decimal("15000"),     Decimal("-50000")),

    # ── 🇨🇮 Côte d'Ivoire ───────────────────────────────────────────────────
    ("agent_ci",  "Wave CI",           "XOF",  Decimal("2000000"),   Decimal("-5000000")),
    ("agent_ci",  "Orange Money CI",   "XOF",  Decimal("1500000"),   Decimal("-3000000")),

    # ── 🇸🇳 Sénégal ─────────────────────────────────────────────────────────
    ("agent_sn",  "Wave SN",           "XOF",  Decimal("1000000"),   Decimal("-2000000")),
    ("agent_sn",  "Orange Money SN",   "XOF",  Decimal("800000"),    Decimal("-1500000")),

    # ── 🇨🇲 Cameroun ────────────────────────────────────────────────────────
    ("agent_cm",  "MTN MoMo CM",       "XAF",  Decimal("1500000"),   Decimal("-3000000")),

    # ── 🇬🇳 Guinée ──────────────────────────────────────────────────────────
    ("agent_gn",  "Orange Money GN",   "GNF",  Decimal("50000000"),  Decimal("-100000000")),

    # ── 💰 Chapmoney — Comptes frais (1 par devise) ─────────────────────────
    ("chapmoney_system",  "Wave CI",           "XOF",  Decimal("0"),  Decimal("0")),
    ("chapmoney_system",  "Sberbank",          "RUB",  Decimal("0"),  Decimal("0")),
    ("chapmoney_system",  "MTN MoMo CM",       "XAF",  Decimal("0"),  Decimal("0")),
    ("chapmoney_system",  "Orange Money GN",   "GNF",  Decimal("0"),  Decimal("0")),
    ("chapmoney_system",  "Belarusbank",       "BYN",  Decimal("0"),  Decimal("0")),
]


# =============================================================================
# SEED — Utilisateurs agents
# =============================================================================

async def seed_agent_users(session: AsyncSession) -> dict:
    """Créer les utilisateurs agents. Retourne {key: User}."""
    print("\n👤 Création des agents...")
    agents_map = {}

    for agent_data in AGENTS:
        agent_id = stable_uuid(agent_data["key"])

        # Vérifier par ID
        existing = await session.get(User, agent_id)
        if existing:
            print(f"   ℹ️  {agent_data['full_name']} existe déjà")
            agents_map[agent_data["key"]] = existing
            continue

        # Vérifier par email
        result = await session.execute(
            select(User).where(User.email == agent_data["email"])
        )
        existing_by_email = result.scalar_one_or_none()
        if existing_by_email:
            print(f"   ℹ️  {agent_data['full_name']} (email) existe déjà")
            agents_map[agent_data["key"]] = existing_by_email
            continue

        user = User(
            id=agent_id,
            full_name=agent_data["full_name"],
            email=agent_data["email"],
            phone=agent_data["phone"],
            country=agent_data["country"],
            hash_password=hash_password("Agent@123"),
            role=UserRole.AGENT,  # ⚠️ Si AGENT n'existe pas dans UserRole, voir note ci-dessous
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(user)
        agents_map[agent_data["key"]] = user
        print(f"   ✅ {agent_data['full_name']} ({agent_data['country']})")

    await session.flush()
    print(f"   → {len(agents_map)} agents prêts")
    return agents_map


# =============================================================================
# SEED — Comptes agents + écritures TOPUP
# =============================================================================

async def seed_agent_accounts(session: AsyncSession, agents_map: dict) -> dict:
    """Créer les AgentAccount et les LedgerEntry TOPUP initiales."""
    print("\n💳 Création des comptes agents + soldes initiaux...")

    # ── Charger les lookups depuis la DB ──
    currencies = {
        c.code: c
        for c in (await session.execute(select(Currency))).scalars().all()
    }
    payment_types = {
        pt.type: pt
        for pt in (await session.execute(select(PaymentType))).scalars().all()
    }

    if not currencies:
        print("   ❌ Aucune devise trouvée ! Exécutez seed_data.py d'abord.")
        return {}
    if not payment_types:
        print("   ❌ Aucune méthode de paiement trouvée ! Exécutez seed_data.py d'abord.")
        return {}

    print(f"   📦 {len(currencies)} devises, {len(payment_types)} méthodes chargées")

    accounts_map = {}
    created_count = 0
    topup_count = 0

    for agent_key, pm_type, currency_code, initial_balance, min_bal in AGENT_ACCOUNTS:

        # ── Vérifications ──
        agent = agents_map.get(agent_key)
        if not agent:
            print(f"   ⚠️  Agent '{agent_key}' introuvable → skip")
            continue

        currency = currencies.get(currency_code)
        if not currency:
            print(f"   ⚠️  Devise '{currency_code}' introuvable → skip")
            continue

        pm = payment_types.get(pm_type)
        if not pm:
            print(f"   ⚠️  Méthode '{pm_type}' introuvable → skip")
            continue

        # ── UUID stable pour le compte ──
        account_key = f"{agent_key}.{pm_type}"
        account_id = stable_uuid(f"account.{account_key}")

        # ── Doublon ? ──
        existing = await session.get(AgentAccount, account_id)
        if existing:
            print(
                f"   ℹ️  {existing.label or account_key} existe déjà "
                f"(solde: {existing.balance:,.0f} {currency_code})"
            )
            accounts_map[account_key] = existing
            continue

        # ── Label ──
        if agent_key == "chapmoney_system":
            label = f"Chapmoney Fees - {currency_code}"
        else:
            label = f"{agent.full_name} - {pm_type} ({currency_code})"

        # ── Créer le compte ──
        account = AgentAccount(
            id=account_id,
            agent_id=agent.id,
            currency_id=currency.id,
            currency_code=currency.code,
            payment_method_id=pm.id,
            payment_method_name=pm.type,
            balance=initial_balance,
            min_balance=min_bal,
            is_active=True,
        )
        session.add(account)
        accounts_map[account_key] = account
        created_count += 1

        # ── Écriture TOPUP initiale (si balance > 0) ──
        if initial_balance > 0:
            ledger_ref = f"SEED-{agent_key.upper()}-{currency_code}"

            # Vérifier si le ledger_tx existe déjà
            existing_ledger_tx = (
                await session.execute(
                    select(LedgerTx).where(LedgerTx.reference == ledger_ref)
                )
            ).scalar_one_or_none()

            if existing_ledger_tx:
                ledger_tx = existing_ledger_tx
            else:
                ledger_tx = LedgerTx(
                    id=stable_uuid(f"ledger.{account_key}"),
                    reference=ledger_ref,
                    category=LedgerCategory.TOP_UP,
                    description=f"Solde initial — {agent.full_name}",
                    initiated_by_id=agent.id,
                )
                session.add(ledger_tx)
                await session.flush()
            
            entry = LedgerEntry(
                id=stable_uuid(f"entry.{account_key}"),
                ledger_tx_id=ledger_tx.id,
                wallet_id=account.id,
                entry_type=LedgerEntryType.DEBIT,  # ✅ augmente le solde
                amount=initial_balance,
                currency_code=currency_code,
                balance_after=initial_balance,
                note="Solde initial seed",
            )
            session.add(entry)

            topup_count += 1

        print(
            f"   ✅ {label:<45} "
            f"{initial_balance:>15,.0f} {currency_code}  "
            f"(min: {min_bal:>12,.0f})"
        )

    await session.flush()
    print(f"\n   → {created_count} comptes créés, {topup_count} écritures TOPUP")
    return accounts_map


# =============================================================================
# RÉSUMÉ
# =============================================================================

async def print_summary(session: AsyncSession):
    """Afficher le résumé complet."""
    print("\n" + "=" * 72)
    print("📊 RÉSUMÉ DES COMPTES AGENTS")
    print("=" * 72)

    accounts = (await session.execute(
        select(AgentAccount)
        .where(AgentAccount.is_active == True)
        .order_by(AgentAccount.agent_id)
    )).scalars().all()

    if not accounts:
        print("   Aucun compte agent trouvé.")
        return

    # Grouper par agent
    by_agent = defaultdict(list)
    for acc in accounts:
        agent = await session.get(User, acc.agent_id)
        currency = await session.get(Currency, acc.currency_id)
        pm = await session.get(PaymentType, acc.payment_method_id)
        by_agent[agent.full_name if agent else "?"].append({
            "balance": float(acc.balance),
            "min_balance": float(acc.min_balance),
            "currency": currency.code if currency else "?",
            "method": pm.type if pm else "?",
        })

    for agent_name, accs in by_agent.items():
        print(f"\n   👤 {agent_name}")
        for a in accs:
            bar = "█" * min(int(abs(a["balance"]) / 100000), 25)
            sign = "+" if a["balance"] >= 0 else ""
            print(
                f"      {a['method']:<22} "
                f"{sign}{a['balance']:>15,.0f} {a['currency']}  "
                f"│ min: {a['min_balance']:>12,.0f}  "
                f"│ {bar}"
            )

    # Totaux par devise
    totals = defaultdict(float)
    for acc in accounts:
        cur = await session.get(Currency, acc.currency_id)
        totals[cur.code if cur else "?"] += float(acc.balance)

    print(f"\n   {'─' * 60}")
    print("   💰 TOTAUX PAR DEVISE:")
    for code, total in sorted(totals.items()):
        print(f"      {code}: {total:>18,.0f}")

    # Écritures ledger
    entries = (await session.execute(select(LedgerEntry))).scalars().all()
    print(f"\n   📒 {len(entries)} écritures dans le ledger")

    print("\n" + "=" * 72)
    print("✅ PRÊT POUR LES SIMULATIONS!")
    print("=" * 72)
    print("""
   Mot de passe agents: Agent@123

   Scénarios de test:

   1️⃣  Client CI → Russie (100 000 XOF)
       collection_account  = Agent CI → Wave CI
       disbursement_account = Agent RU → Sberbank
       → CREDIT +100 000 XOF │ DEBIT -13 700 RUB

   2️⃣  Client RU → Sénégal (50 000 RUB)
       collection_account  = Agent RU → Sberbank
       disbursement_account = Agent SN → Wave SN
       → CREDIT +50 000 RUB │ DEBIT -365 000 XOF

   3️⃣  Client CI → Cameroun (200 000 XOF)
       collection_account  = Agent CI → Orange Money CI
       disbursement_account = Agent CM → MTN MoMo CM
       → CREDIT +200 000 XOF │ DEBIT -200 000 XAF

   4️⃣  Compensation mensuelle
       POST /api/v1/admin/ledger/settlements
       Agent CI (excédent XOF) → Agent RU (déficit RUB)
""")


# =============================================================================
# NETTOYAGE
# =============================================================================

async def clean_agent_data(session: AsyncSession):
    """Supprimer les données agents (ordre des dépendances FK)."""
    print("\n🗑️  Nettoyage des données agents...")
    from src.db.models import Settlement

    for model, name in [
        (LedgerEntry, "écritures ledger"),
        (Settlement, "settlements"),
        (AgentAccount, "comptes agents"),
    ]:
        try:
            count = len((await session.execute(select(model))).scalars().all())
            if count > 0:
                await session.execute(model.__table__.delete())
                print(f"   🗑️  {count} {name} supprimé(e)s")
        except Exception as e:
            print(f"   ⚠️  Erreur sur {name}: {e}")

    # Supprimer les agents créés par ce seed
    for agent_data in AGENTS:
        agent_id = stable_uuid(agent_data["key"])
        agent = await session.get(User, agent_id)
        if agent:
            await session.delete(agent)
            print(f"   🗑️  Agent {agent.full_name} supprimé")

    await session.flush()
    print("   ✅ Nettoyage terminé")


# =============================================================================
# MAIN
# =============================================================================

async def seed_all():
    parser = argparse.ArgumentParser(description="Seed agents + comptes ledger")
    parser.add_argument("--force", action="store_true", help="Nettoyer et recréer")
    args = parser.parse_args()

    print("=" * 72)
    print("🌱 SEED — AGENTS & COMPTES LEDGER CHAPMONEY")
    print("=" * 72)

    try:
        async with AsyncSessionLocal() as session:
            if args.force:
                await clean_agent_data(session)

            agents_map = await seed_agent_users(session)
            await seed_agent_accounts(session, agents_map)

            # Commit atomique
            await session.commit()

            await print_summary(session)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        print("\n💡 Vérifiez que seed_data.py a été exécuté avant.")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(seed_all())
